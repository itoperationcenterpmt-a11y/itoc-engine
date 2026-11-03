"""Penjaga alamat keluar (SSRF): URL yang diisi admin (webhook, konektor) tidak boleh mengarah ke loopback, link-local (termasuk metadata cloud 169.254.169.254),
multicast, atau alamat tak terdefinisi. Alamat jaringan internal (RFC 1918) tetap boleh karena sumber data memang ada di jaringan internal."""
import ipaddress
import re
import socket
from urllib.parse import urlsplit


def check_url(url: str, what: str = "Alamat") -> str:
    u = (url or "").strip()
    if not re.match(r"^https?://", u, re.I):
        u = "https://" + u
    p = urlsplit(u)
    host = p.hostname
    if not host or p.scheme not in ("http", "https") or p.username or p.password:
        raise ValueError(f"{what} is not valid (use http:// or https://, without user:password@)")
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror:
        raise ValueError(f"{what}: host name not found")
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_unspecified or ip.is_reserved:
            raise ValueError(f"{what}: address {ip} is not allowed (loopback, link-local, or invalid)")
    return u