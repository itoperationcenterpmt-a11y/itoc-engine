"""Enterprise Single Sign-On (OIDC / OAuth2 Authorization Code + PKCE).
Supports Microsoft Entra ID (Azure AD), Keycloak, Google Workspace, Okta, and any standard OIDC provider.
Configuration and encrypted client_secret are stored in the vault ('sso')."""
import base64
import hashlib
import logging
import secrets
from urllib.parse import urlencode
import httpx
import jwt
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from .. import vault
from ..config import settings
from ..db import get_db
from ..models import Role, User
from ..security import hash_pw, is_https, make_token, random_pw, require_admin, require_admin_area, set_session
from ..store import audit, bump_config, load_config

log = logging.getLogger("itoc.sso")
router = APIRouter(prefix="/api/auth/sso", tags=["sso"])
admin = APIRouter(prefix="/api/admin/sso", tags=["admin-sso"], dependencies=[Depends(require_admin_area)])

SSO_COOKIE = "itoc_sso_state"
DEFAULTS = {
    "enabled": False,
    "provider_name": "Corporate SSO",
    "issuer_url": "",
    "auth_url": "",
    "token_url": "",
    "userinfo_url": "",
    "client_id": "",
    "scopes": "openid email profile",
    "auto_provision": False,
    "default_role": "management",
    "allowed_domains": "",
    "username_claim": "preferred_username",
    "name_claim": "name",
    "verify_tls": True,
}


def _cfg(db: Session) -> dict:
    raw = vault.get_json(db, "sso") or {}
    return {**DEFAULTS, **raw}


def _discover(c: dict) -> dict:
    """Resolve authorization/token/userinfo endpoints from issuer_url (.well-known/openid-configuration) or explicit URLs."""
    auth_u, tok_u, info_u = (c.get("auth_url") or "").strip(), (c.get("token_url") or "").strip(), (c.get("userinfo_url") or "").strip()
    if auth_u and tok_u:
        return {"authorization_endpoint": auth_u, "token_endpoint": tok_u, "userinfo_endpoint": info_u}
    iss = (c.get("issuer_url") or "").strip().rstrip("/")
    if not iss:
        raise HTTPException(400, "SSO Issuer URL or Authorization/Token URLs are not configured.")
    disc_url = iss if iss.endswith("/openid-configuration") else f"{iss}/.well-known/openid-configuration"
    try:
        r = httpx.get(disc_url, timeout=8, verify=bool(c.get("verify_tls", True)))
        r.raise_for_status()
        d = r.json()
    except Exception as e:
        raise HTTPException(502, f"OIDC discovery failed: {e}")
    return {
        "authorization_endpoint": auth_u or d.get("authorization_endpoint", ""),
        "token_endpoint": tok_u or d.get("token_endpoint", ""),
        "userinfo_endpoint": info_u or d.get("userinfo_endpoint", ""),
    }


def _redirect_uri(request: Request, db: Session) -> str:
    pub = (load_config(db).p("ui.public_url", "") or "").strip().rstrip("/")
    if pub:
        return f"{pub}/api/auth/sso/callback"
    scheme = "https" if is_https(request) else request.url.scheme
    host = request.headers.get("x-forwarded-host") or request.headers.get("host") or request.url.netloc
    return f"{scheme}://{host}/api/auth/sso/callback"


def public_info(db: Session) -> dict:
    c = _cfg(db)
    ready = bool(c.get("enabled") and c.get("client_id") and (c.get("issuer_url") or (c.get("auth_url") and c.get("token_url"))))
    return {"sso_enabled": ready, "sso_label": (c.get("provider_name") or "Corporate SSO").strip()}


@router.get("/login")
def sso_login(request: Request, db: Session = Depends(get_db)):
    c = _cfg(db)
    if not c.get("enabled") or not c.get("client_id"):
        raise HTTPException(400, "SSO is not enabled.")
    ep = _discover(c)
    if not ep.get("authorization_endpoint"):
        raise HTTPException(502, "OIDC authorization_endpoint missing.")
    state = secrets.token_urlsafe(24)
    verifier = secrets.token_urlsafe(48)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    redirect_uri = _redirect_uri(request, db)
    params = {
        "client_id": c["client_id"].strip(),
        "response_type": "code",
        "scope": (c.get("scopes") or "openid email profile").strip(),
        "redirect_uri": redirect_uri,
        "state": state,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    }
    signed = jwt.encode({"s": state, "v": verifier, "r": redirect_uri}, settings().jwt_secret, algorithm="HS256")
    resp = RedirectResponse(ep["authorization_endpoint"] + ("&" if "?" in ep["authorization_endpoint"] else "?") + urlencode(params), status_code=302)
    resp.set_cookie(SSO_COOKIE, signed, max_age=600, httponly=True, samesite="lax", secure=is_https(request), path="/")
    return resp


@router.get("/callback")
def sso_callback(request: Request, code: str = "", state: str = "", error: str = "", db: Session = Depends(get_db)):
    if error:
        return RedirectResponse(f"/?sso_err={error[:80]}", status_code=302)
    raw_cookie = request.cookies.get(SSO_COOKIE, "")
    try:
        st = jwt.decode(raw_cookie, settings().jwt_secret, algorithms=["HS256"])
    except Exception:
        return RedirectResponse("/?sso_err=expired_state", status_code=302)
    if not code or not state or not secrets.compare_digest(state, str(st.get("s", ""))):
        return RedirectResponse("/?sso_err=invalid_state", status_code=302)

    c = _cfg(db)
    if not c.get("enabled"):
        return RedirectResponse("/?sso_err=disabled", status_code=302)
    ep = _discover(c)
    form = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": st.get("r") or _redirect_uri(request, db),
        "client_id": c["client_id"].strip(),
        "code_verifier": st.get("v", ""),
    }
    if c.get("client_secret"):
        form["client_secret"] = c["client_secret"]
    try:
        tr = httpx.post(ep["token_endpoint"], data=form, timeout=12, verify=bool(c.get("verify_tls", True)))
        tr.raise_for_status()
        tok = tr.json()
    except Exception as e:
        log.warning("SSO token exchange failed: %s", e)
        return RedirectResponse("/?sso_err=token_failed", status_code=302)

    claims = {}
    if tok.get("id_token"):
        try:
            claims = jwt.decode(tok["id_token"], options={"verify_signature": False})
        except Exception:
            claims = {}
    if ep.get("userinfo_endpoint") and tok.get("access_token"):
        try:
            ur = httpx.get(ep["userinfo_endpoint"], headers={"Authorization": f"Bearer {tok['access_token']}"}, timeout=8, verify=bool(c.get("verify_tls", True)))
            if ur.is_success:
                claims.update(ur.json())
        except Exception as e:
            log.warning("SSO userinfo fetch failed: %s", e)

    u_claim = (c.get("username_claim") or "preferred_username").strip()
    n_claim = (c.get("name_claim") or "name").strip()
    raw_id = str(claims.get(u_claim) or claims.get("email") or claims.get("upn") or claims.get("sub") or "").strip().lower()
    email = str(claims.get("email") or (raw_id if "@" in raw_id else "")).strip().lower()
    full_name = str(claims.get(n_claim) or claims.get("given_name") or raw_id.split("@")[0] or "SSO User").strip()[:120]
    if not raw_id:
        return RedirectResponse("/?sso_err=no_identity", status_code=302)

    # Check allowed domains if configured
    allowed = [d.strip().lower().lstrip("@") for d in str(c.get("allowed_domains") or "").split(",") if d.strip()]
    if allowed:
        dom = email.split("@")[-1] if "@" in email else (raw_id.split("@")[-1] if "@" in raw_id else "")
        if dom not in allowed:
            return RedirectResponse("/?sso_err=domain_denied", status_code=302)

    # Match existing user by full email/upn OR local part before @
    short = raw_id.split("@")[0]
    u = db.query(User).filter(User.username.in_([raw_id[:60], short[:60]])).first()
    cfg = load_config(db)
    ip = request.client.host if request.client else "?"
    if not u:
        if not c.get("auto_provision"):
            audit(db, raw_id[:60], "SSO login denied (not provisioned)", {"ip": ip}, cfg.p("tz_offset_hours", 7))
            db.commit()
            return RedirectResponse("/?sso_err=not_registered", status_code=302)
        rk = c.get("default_role") or "management"
        if not db.get(Role, rk):
            rk = "management"
        uname = short[:60] if not db.query(User).filter_by(username=short[:60]).first() else raw_id[:60]
        u = User(username=uname, full_name=full_name, role_key=rk, active=True, password_hash=hash_pw(random_pw() + secrets.token_hex(8)), must_change_pw=False)
        db.add(u)
        audit(db, uname, f"SSO auto-provisioned account ({rk})", {"ip": ip, "email": email}, cfg.p("tz_offset_hours", 7))

    if not u.active:
        return RedirectResponse("/?sso_err=inactive", status_code=302)
    u.last_login = cfg.now()
    audit(db, u.username, "SSO Login", {"ip": ip, "provider": c.get("provider_name")}, cfg.p("tz_offset_hours", 7))
    db.commit()
    resp = RedirectResponse("/", status_code=302)
    resp.delete_cookie(SSO_COOKIE, path="/")
    set_session(resp, request, make_token(u))
    return resp


class SsoIn(BaseModel):
    enabled: bool = False
    provider_name: str = "Corporate SSO"
    issuer_url: str = ""
    auth_url: str = ""
    token_url: str = ""
    userinfo_url: str = ""
    client_id: str = ""
    client_secret: str = ""       # blank = keep existing
    clear_secret: bool = False
    scopes: str = "openid email profile"
    auto_provision: bool = False
    default_role: str = "management"
    allowed_domains: str = ""
    username_claim: str = "preferred_username"
    name_claim: str = "name"
    verify_tls: bool = True


@admin.get("")
def sso_get(request: Request, db: Session = Depends(get_db)):
    c = _cfg(db)
    out = {k: c.get(k) for k in DEFAULTS}
    out["secret_set"] = bool(c.get("client_secret"))
    out["callback_url"] = _redirect_uri(request, db)
    return out


@admin.put("")
def sso_set(body: SsoIn, db: Session = Depends(get_db), user: User = Depends(require_admin)):
    cur = _cfg(db)
    data = body.model_dump(exclude={"client_secret", "clear_secret"})
    if body.clear_secret:
        data["client_secret"] = ""
    elif body.client_secret.strip():
        data["client_secret"] = body.client_secret.strip()
    else:
        data["client_secret"] = cur.get("client_secret", "")
    vault.put_json(db, "sso", data)
    audit(db, user.username, f"Updated SSO configuration ({'enabled' if data['enabled'] else 'disabled'})", {"provider": data["provider_name"]})
    db.commit()
    bump_config()
    return {"ok": True}


@admin.post("/test")
def sso_test(db: Session = Depends(get_db), user: User = Depends(require_admin)):
    c = _cfg(db)
    ep = _discover(c)
    return {"ok": True, "authorization_endpoint": ep.get("authorization_endpoint"), "token_endpoint": ep.get("token_endpoint"), "userinfo_endpoint": ep.get("userinfo_endpoint")}
