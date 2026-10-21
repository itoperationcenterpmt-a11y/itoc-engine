"""Panorama (PAN-OS XML API): uji koneksi dan pengambilan custom report. Tahap ini hanya untuk Test; sinkron otomatis menyusul setelah bentuk hasil report terkonfirmasi.
Login memakai akun API khusus (Admin -> Integrations, terenkripsi): key dibuat lewat keygen setiap kali dipakai, tidak disimpan."""
import re
import time
import xml.etree.ElementTree as ET
import httpx


def api_url(base: str) -> str:
    b = (base or "").strip().rstrip("/")
    if not re.match(r"^https?://", b, re.I):
        b = "https://" + b
    return b + "/api/"


def _parse(r: httpx.Response) -> ET.Element:
    """PAN-OS menjawab kegagalan (kredensial salah, hak kurang) dengan HTTP 403 dan XML berisi alasan: alasan itu yang ditampilkan."""
    try:
        x = ET.fromstring(r.text)
    except ET.ParseError:
        r.raise_for_status()
        raise RuntimeError("Jawaban Panorama bukan XML (alamat salah atau bukan Panorama?)")
    if x.get("status") != "success":
        msg = " ".join((e.text or "").strip() for e in x.iter() if e.tag in ("line", "msg") and (e.text or "").strip()) or r.text[:160]
        raise RuntimeError(f"Panorama menolak (HTTP {r.status_code}, kode {x.get('code') or '-'}): {msg[:180]}")
    r.raise_for_status()
    return x

def keygen(cl: httpx.Client, base: str, user: str, pw: str) -> str:
    x = _parse(cl.post(api_url(base), data={"type": "keygen", "user": user, "password": pw}))
    key = x.findtext(".//key")
    if not key:
        raise RuntimeError("Panorama tidak mengembalikan key")
    return key


def run_report(cl: httpx.Client, base: str, key: str, name: str, wait_s: int = 90, extra: dict | None = None) -> tuple[list[str], list[dict]]:
    """Jalankan custom report secara asinkron lalu tunggu hasilnya. Mengembalikan (kolom, baris)."""
    h = {"X-PAN-KEY": key}
    x = _parse(cl.post(api_url(base), headers=h, data={"type": "report", "reporttype": "custom", "reportname": name, "async": "yes", **(extra or {})}))
    job = x.findtext(".//job")
    if not job:
        raise RuntimeError("Panorama tidak memberi job id untuk report " + name)
    t0 = time.time()
    while True:
        y = _parse(cl.post(api_url(base), headers=h, data={"type": "report", "action": "get", "job-id": job}))
        if (y.findtext(".//job/status") or "FIN").upper() == "FIN":
            break
        if time.time() - t0 > wait_s:
            raise RuntimeError("Report belum selesai dalam %d detik" % wait_s)
        time.sleep(2)
    rows = [{c.tag: (c.text or "").strip() for c in e} for e in y.iter("entry") if len(e)]
    cols = list(rows[0].keys()) if rows else []
    return cols, rows

def run_log(cl: httpx.Client, base: str, key: str, log_type: str = "threat", nlogs: int = 5, query: str = "", wait_s: int = 60) -> tuple[list[str], list[dict]]:
    """Ambil beberapa baris log (traffic, threat, url, ...) lewat job asinkron. Untuk uji hak Log dan melihat nama kolom."""
    h = {"X-PAN-KEY": key}
    data = {"type": "log", "log-type": log_type, "nlogs": str(nlogs), "async": "yes"}
    if query:
        data["query"] = query
    x = _parse(cl.post(api_url(base), headers=h, data=data))
    job = x.findtext(".//job")
    if not job:
        raise RuntimeError("Panorama tidak memberi job id untuk log " + log_type)
    t0 = time.time()
    while True:
        y = _parse(cl.post(api_url(base), headers=h, data={"type": "log", "action": "get", "job-id": job}))
        if (y.findtext(".//job/status") or "FIN").upper() == "FIN":
            break
        if time.time() - t0 > wait_s:
            raise RuntimeError("Log belum selesai dalam %d detik" % wait_s)
        time.sleep(1)
    rows = [{c.tag: (c.text or "").strip() for c in e} for e in y.iter("entry") if len(e)]
    return (list(rows[0].keys()) if rows else []), rows

def _names(x: ET.Element, path: str) -> list[str]:
    n = x.find(path)
    return [e.get("name") for e in (n if n is not None else []) if e.tag == "entry" and e.get("name")]


def find_report(cl: httpx.Client, base: str, key: str, name: str) -> tuple[list[str], list[str]]:
    """Cari di config Panorama di mana report itu didefinisikan (shared atau device group). Butuh hak XML API Configuration minimal Read Only.
    Mengembalikan (lokasi, daftar device group)."""
    h = {"X-PAN-KEY": key}
    get = lambda xp: _parse(cl.post(api_url(base), headers=h, data={"type": "config", "action": "get", "xpath": xp}))
    found = []
    if name in _names(get("/config/shared/reports"), ".//reports"):
        found.append("shared")
    dgp = "/config/devices/entry[@name='localhost.localdomain']/device-group"
    dgs = _names(get(dgp), ".//device-group")
    for dg in dgs:
        try:
            if name in _names(get(f"{dgp}/entry[@name='{dg}']/reports"), ".//reports"):
                found.append("device-group " + dg)
        except RuntimeError:
            continue
    return found, dgs
