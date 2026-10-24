"""Skema PostgreSQL. Dua kelompok tabel:
1. Master/konfigurasi (dapat diubah di menu Admin, tidak ada yang di-hardcode di kode).
2. Data operasional hasil sinkron API / impor.
Waktu disimpan sebagai TIMESTAMP tanpa zona = jam lokal (WIB), sama seperti ekspor sumber."""
from datetime import datetime, date
from sqlalchemy import (String, Integer, SmallInteger, Float, Boolean, Text, DateTime, Date, BigInteger,
                        ForeignKey, Index, UniqueConstraint, func)
from sqlalchemy.dialects.postgresql import JSONB, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .db import Base


# ---------------- master / konfigurasi ----------------
class Parameter(Base):
    """Parameter bisnis bertipe bebas (angka, daftar, objek). Contoh: net.target, soc.watch_apps."""
    __tablename__ = "app_parameter"
    key: Mapped[str] = mapped_column(String(80), primary_key=True)
    value: Mapped[dict] = mapped_column(JSONB)
    label: Mapped[str] = mapped_column(String(160))
    group: Mapped[str] = mapped_column(String(40), default="umum")
    editor: Mapped[str] = mapped_column(String(20), default="json")  # number|percent|text|json|list|date
    ui: Mapped[dict] = mapped_column(JSONB, default=dict)               # min, max, step, unit
    description: Mapped[str | None] = mapped_column(Text)
    sort: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    updated_by: Mapped[str | None] = mapped_column(String(60))


class Module(Base):
    """Menu/halaman dashboard. Urutan, label, filter yang berlaku, catatan, dan badge diatur di sini."""
    __tablename__ = "module"
    key: Mapped[str] = mapped_column(String(40), primary_key=True)
    label: Mapped[str] = mapped_column(String(80))
    sort: Mapped[int] = mapped_column(Integer, default=0)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    filters: Mapped[dict] = mapped_column(JSONB, default=dict)   # {p,s,l,c} periode/shift/lokasi/bandingkan
    note: Mapped[str | None] = mapped_column(Text)
    why: Mapped[str | None] = mapped_column(Text)
    parent: Mapped[str | None] = mapped_column(String(40))       # menu induk: menu ini tampil sebagai sub-menu induknya (mis. Handover di Report)
    icon: Mapped[str | None] = mapped_column(String(30))         # nama ikon menu (dashboard, ticket, activity, shield, users, handover, database, sliders)
    badge: Mapped[dict | None] = mapped_column(JSONB)            # {text, tip}
    notice: Mapped[dict | None] = mapped_column(JSONB)           # {title, body}


class Role(Base):
    __tablename__ = "role"
    key: Mapped[str] = mapped_column(String(40), primary_key=True)
    label: Mapped[str] = mapped_column(String(80))
    description: Mapped[str | None] = mapped_column(String(300))               # siapa yang memakai role ini, tampil di Admin
    modules: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)  # ["*"] = semua
    can_write: Mapped[bool] = mapped_column(Boolean, default=True)           # serah terima, unggah
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    uploads: Mapped[list[str]] = mapped_column(ARRAY(String), default=list, server_default="{}")
    admin_view: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")  # boleh membuka menu Admin, hanya baca
    scope: Mapped[str] = mapped_column(String(10), default="all", server_default="all")      # all | ho (kantor pusat) | own (lokasi di akun)  # sumber RAW yang boleh diunggah: soc | tickets | prtg | *
    sort: Mapped[int] = mapped_column(Integer, default=0)


class User(Base):
    __tablename__ = "app_user"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(60), unique=True)
    full_name: Mapped[str] = mapped_column(String(120))
    role_key: Mapped[str] = mapped_column(ForeignKey("role.key"))
    password_hash: Mapped[str] = mapped_column(String(120))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    must_change_pw: Mapped[bool] = mapped_column(Boolean, default=True)
    last_login: Mapped[datetime | None] = mapped_column(DateTime)
    site: Mapped[str | None] = mapped_column(String(120))  # untuk role EOS: batasi ke branch sendiri
    profile: Mapped[str] = mapped_column(String(40), default="default", server_default="default")   # chosen dashboard profile
    role: Mapped[Role] = relationship(lazy="joined")


class Site(Base):
    __tablename__ = "site"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)   # = Group di ManageEngine = Device di PRTG
    kind: Mapped[str] = mapped_column(String(20), default="branch")
    aliases: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    sort: Mapped[int] = mapped_column(Integer, default=0)
    lat: Mapped[float | None] = mapped_column(Float)    # koordinat untuk peta Devices (opsional)
    lon: Mapped[float | None] = mapped_column(Float)


class Shift(Base):
    __tablename__ = "shift"
    no: Mapped[int] = mapped_column(SmallInteger, primary_key=True)  # 1..n, urutan dalam sehari
    code: Mapped[str] = mapped_column(String(4), unique=True)       # P / S / M
    name: Mapped[str] = mapped_column(String(40))
    start_hour: Mapped[int] = mapped_column(SmallInteger)


class Team(Base):
    __tablename__ = "team"
    code: Mapped[str] = mapped_column(String(10), primary_key=True)
    label: Mapped[str] = mapped_column(String(60))
    rotation_offset: Mapped[int] = mapped_column(SmallInteger, default=0)  # geser hari dalam pola rotasi
    sort: Mapped[int] = mapped_column(Integer, default=0)


class Person(Base):
    __tablename__ = "person"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    sys_name: Mapped[str | None] = mapped_column(String(120))  # nama teknisi di ManageEngine bila beda
    unit: Mapped[str] = mapped_column(String(40))              # ITOC | EOS | Akun bersama
    job: Mapped[str] = mapped_column(String(80))
    team_code: Mapped[str | None] = mapped_column(ForeignKey("team.code"))
    branch: Mapped[str | None] = mapped_column(String(120))
    phone: Mapped[str | None] = mapped_column(String(40))
    is_coordinator: Mapped[bool] = mapped_column(Boolean, default=False)
    is_shared: Mapped[bool] = mapped_column(Boolean, default=False)
    exclude_rank: Mapped[bool] = mapped_column(Boolean, default=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Isp(Base):
    __tablename__ = "isp"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    keyword: Mapped[str] = mapped_column(String(40))   # dicocokkan ke nama sensor (lowercase contains)
    name: Mapped[str] = mapped_column(String(60))
    target: Mapped[float | None] = mapped_column(Float)  # null = pakai net.target
    sort: Mapped[int] = mapped_column(Integer, default=0)


class SlaTarget(Base):
    __tablename__ = "sla_target"
    name: Mapped[str] = mapped_column(String(60), primary_key=True)  # = SLA Name di ManageEngine
    hours: Mapped[float] = mapped_column(Float)


class Formula(Base):
    __tablename__ = "formula"
    key: Mapped[str] = mapped_column(String(40), primary_key=True)
    label: Mapped[str] = mapped_column(String(80))
    text: Mapped[str] = mapped_column(Text)
    source: Mapped[str | None] = mapped_column(String(160))
    sort: Mapped[int] = mapped_column(Integer, default=0)


class Widget(Base):
    """Widget grafik laporan. Isi data disediakan kode (kunci = key); judul, jenis, jumlah baris, urutan, preset, dan aktif/tidaknya diatur di Admin."""
    __tablename__ = "widget"
    key: Mapped[str] = mapped_column(String(40), primary_key=True)
    section: Mapped[str] = mapped_column(String(20))               # servicedesk | noc | soc
    title: Mapped[str] = mapped_column(String(120))
    kind: Mapped[str] = mapped_column(String(10), default="bar")   # bar | stack | hbar | donut | line
    top_n: Mapped[int] = mapped_column(SmallInteger, default=10)    # batas baris untuk grafik peringkat (hbar)
    hero: Mapped[bool] = mapped_column(Boolean, default=False)      # grafik utama bidang ini (dipakai di Summary)
    presets: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)  # ringkas | standar | lengkap
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    sort: Mapped[int] = mapped_column(Integer, default=0)


class LayoutProfile(Base):
    """Dashboard profile: a named set of page layouts (for example NOC wall, Management). Each user picks one; Super Admin edits them with Customize."""
    __tablename__ = "layout_profile"
    key: Mapped[str] = mapped_column(String(40), primary_key=True)
    name: Mapped[str] = mapped_column(String(80))
    description: Mapped[str | None] = mapped_column(String(200))
    builtin: Mapped[bool] = mapped_column(Boolean, default=False)
    sort: Mapped[int] = mapped_column(Integer, default=0)


class Layout(Base):
    """Page layout (Overview, Ticketing, ...) inside one profile: order, size, title, and show/hide of each block. Edited with the Customize button."""
    __tablename__ = "layout"
    profile: Mapped[str] = mapped_column(String(40), primary_key=True, default="default")
    page: Mapped[str] = mapped_column(String(40), primary_key=True)
    role: Mapped[str] = mapped_column(String(40), primary_key=True, default="")   # "" = berlaku untuk semua role
    key: Mapped[str] = mapped_column(String(80), primary_key=True)                 # kunci blok (dari judul bawaan)
    title: Mapped[str] = mapped_column(String(120), default="")                    # kosong = judul bawaan
    size: Mapped[str] = mapped_column(String(4), default="")                       # c3 | c4 | c6 | c8 | c12; kosong = ukuran bawaan
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    sort: Mapped[int] = mapped_column(Integer, default=0)


class DataSource(Base):
    """Konektor: ManageEngine, PRTG, Panorama. Mode api/impor, interval, dan kredensial (nama env) diatur di sini."""
    __tablename__ = "data_source"
    key: Mapped[str] = mapped_column(String(40), primary_key=True)
    label: Mapped[str] = mapped_column(String(80))
    mode: Mapped[str] = mapped_column(String(10), default="api")   # api | import
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    interval_min: Mapped[int] = mapped_column(Integer, default=60)
    config: Mapped[dict] = mapped_column(JSONB, default=dict)
    tip: Mapped[str | None] = mapped_column(String(200))
    last_ok_at: Mapped[datetime | None] = mapped_column(DateTime)
    last_error: Mapped[str | None] = mapped_column(Text)
    cursor: Mapped[dict] = mapped_column(JSONB, default=dict)      # posisi sinkron inkremental


# ---------------- data operasional ----------------
class Ticket(Base):
    __tablename__ = "ticket"
    id: Mapped[str] = mapped_column(String(30), primary_key=True)
    mode: Mapped[str] = mapped_column(String(40), default="")
    requester: Mapped[str] = mapped_column(String(160), default="")
    site: Mapped[str] = mapped_column(String(120), default="")
    category: Mapped[str] = mapped_column(String(80), default="")
    subcategory: Mapped[str] = mapped_column(String(80), default="")
    subject: Mapped[str] = mapped_column(String(200), default="")
    technician: Mapped[str] = mapped_column(String(120), default="")
    sla_name: Mapped[str] = mapped_column(String(60), default="")
    impact: Mapped[str] = mapped_column(String(40), default="")
    priority: Mapped[str] = mapped_column(String(40), default="")
    urgency: Mapped[str] = mapped_column(String(40), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime)
    onhold_h: Mapped[float] = mapped_column(Float, default=0)
    status: Mapped[str] = mapped_column(String(40), default="")
    desc_empty: Mapped[bool] = mapped_column(Boolean, default=False)
    source: Mapped[str] = mapped_column(String(20), default="api")
    synced_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    __table_args__ = (Index("ix_ticket_site_created", "site", "created_at"),)


class PrtgSensor(Base):
    __tablename__ = "prtg_sensor"
    id: Mapped[str] = mapped_column(String(20), primary_key=True)
    name: Mapped[str] = mapped_column(String(160))
    device: Mapped[str] = mapped_column(String(120))   # nama lokasi
    capacity_mbps: Mapped[float | None] = mapped_column(Float)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class PrtgHourly(Base):
    __tablename__ = "prtg_hourly"
    sensor_id: Mapped[str] = mapped_column(ForeignKey("prtg_sensor.id", ondelete="CASCADE"), primary_key=True)
    ts: Mapped[datetime] = mapped_column(DateTime, primary_key=True)  # awal jam
    in_mbps: Mapped[float | None] = mapped_column(Float)
    out_mbps: Mapped[float | None] = mapped_column(Float)
    down_s: Mapped[float] = mapped_column(Float, default=0)
    seen: Mapped[bool] = mapped_column(Boolean, default=True)
    __table_args__ = (Index("ix_prtg_hourly_ts", "ts"),)


class PrtgDaily(Base):
    """Ringkasan PRTG per sensor per hari dari unggahan RAW (PDF laporan harian). Dipakai NOC untuk hari yang tidak punya data per jam dari API."""
    __tablename__ = "prtg_daily"
    sensor_id: Mapped[str] = mapped_column(ForeignKey("prtg_sensor.id", ondelete="CASCADE"), primary_key=True)
    day: Mapped[date] = mapped_column(Date, primary_key=True)
    up_s: Mapped[float] = mapped_column(Float, default=0)
    down_s: Mapped[float] = mapped_column(Float, default=0)
    req_good: Mapped[float | None] = mapped_column(Float)
    req_fail: Mapped[float | None] = mapped_column(Float)
    avg_total: Mapped[float | None] = mapped_column(Float)   # Mbit/s
    avg_in: Mapped[float | None] = mapped_column(Float)
    avg_out: Mapped[float | None] = mapped_column(Float)
    vol_total_mb: Mapped[float | None] = mapped_column(Float)
    max_mbps: Mapped[float | None] = mapped_column(Float)
    min_mbps: Mapped[float | None] = mapped_column(Float)
    source_file: Mapped[str | None] = mapped_column(String(200))
    created_pdf: Mapped[datetime | None] = mapped_column(DateTime)  # waktu laporan dibuat di PRTG (untuk memilih yang terbaru)
    __table_args__ = (Index("ix_prtg_daily_day", "day"),)


class PrtgEvent(Base):
    __tablename__ = "prtg_event"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    sensor_id: Mapped[str] = mapped_column(ForeignKey("prtg_sensor.id", ondelete="CASCADE"), index=True)
    start_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    end_at: Mapped[datetime] = mapped_column(DateTime)
    __table_args__ = (UniqueConstraint("sensor_id", "start_at"),)


class SocBatch(Base):
    __tablename__ = "soc_batch"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    file_name: Mapped[str] = mapped_column(String(200))
    uploaded_by: Mapped[str] = mapped_column(String(60))
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    date_from: Mapped[date] = mapped_column(Date)
    date_to: Mapped[date] = mapped_column(Date)
    rows_read: Mapped[int] = mapped_column(Integer, default=0)
    rows_skipped: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(10), default="valid")   # valid | warn | failed
    issues: Mapped[list] = mapped_column(JSONB, default=list)          # [{k: warn|crit, t}]
    tables: Mapped[list] = mapped_column(JSONB, default=list)          # tabel laporan Top
    kpi: Mapped[dict | None] = mapped_column(JSONB)
    days: Mapped[list["SocDay"]] = relationship(back_populates="batch", cascade="all, delete-orphan")


class SocDay(Base):
    __tablename__ = "soc_day"
    batch_id: Mapped[int] = mapped_column(ForeignKey("soc_batch.id", ondelete="CASCADE"), primary_key=True)
    day: Mapped[date] = mapped_column(Date, primary_key=True, index=True)
    threats: Mapped[dict] = mapped_column(JSONB, default=dict)  # 'sev|type|cat|action|internal' -> count
    urls: Mapped[dict] = mapped_column(JSONB, default=dict)     # 'cat|blocked' -> count
    bytes: Mapped[int] = mapped_column(BigInteger, default=0)
    sessions: Mapped[int] = mapped_column(BigInteger, default=0)
    batch: Mapped[SocBatch] = relationship(back_populates="days")


class Handover(Base):
    __tablename__ = "handover"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    shift_date: Mapped[date] = mapped_column(Date, index=True)
    shift_no: Mapped[int] = mapped_column(SmallInteger)
    category: Mapped[str] = mapped_column(String(40))
    priority: Mapped[str] = mapped_column(String(20))
    site: Mapped[str] = mapped_column(String(120))
    ticket_id: Mapped[str | None] = mapped_column(String(30))
    title: Mapped[str] = mapped_column(String(160))
    body: Mapped[str] = mapped_column(Text)
    next_action: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[str] = mapped_column(String(120))
    is_open: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    closed_by: Mapped[str | None] = mapped_column(String(120))
    closed_at: Mapped[datetime | None] = mapped_column(DateTime)
    close_note: Mapped[str | None] = mapped_column(Text)


class SyncLog(Base):
    __tablename__ = "sync_log"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    source: Mapped[str] = mapped_column(String(40), index=True)
    at: Mapped[datetime] = mapped_column(DateTime, index=True)
    ok: Mapped[bool] = mapped_column(Boolean)
    rows: Mapped[int] = mapped_column(Integer, default=0)
    ms: Mapped[int] = mapped_column(Integer, default=0)
    message: Mapped[str] = mapped_column(Text, default="")


class AuditLog(Base):
    __tablename__ = "audit_log"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    at: Mapped[datetime] = mapped_column(DateTime, index=True)
    username: Mapped[str] = mapped_column(String(60))
    action: Mapped[str] = mapped_column(Text)
    detail: Mapped[dict | None] = mapped_column(JSONB)


# tabel master yang boleh di-CRUD dari menu Admin (urutan = urutan tampil)
MASTER = {
    "site": (Site, "Lokasi"), "person": (Person, "Personel"), "team": (Team, "Tim"), "shift": (Shift, "Shift"),
    "isp": (Isp, "ISP"), "sla_target": (SlaTarget, "Target SLA"), "prtg_sensor": (PrtgSensor, "Sensor dan Kapasitas"),
    "module": (Module, "Menu"), "widget": (Widget, "Widget"), "role": (Role, "Role"), "formula": (Formula, "Rumus"),
    "data_source": (DataSource, "Sumber Data"),
}


# ---------------- integrasi ----------------
class Secret(Base):
    """Rahasia terenkripsi (Fernet): kredensial konektor, konfigurasi SMTP. Nilai tidak pernah dikirim kembali ke browser."""
    __tablename__ = "secret"
    name: Mapped[str] = mapped_column(String(80), primary_key=True)
    value: Mapped[str] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class ApiKey(Base):
    """Kunci API baca-saja untuk sistem lain. Hanya hash SHA-256 yang disimpan; kunci tampil sekali saat dibuat."""
    __tablename__ = "api_key"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(80))
    prefix: Mapped[str] = mapped_column(String(16))
    key_hash: Mapped[str] = mapped_column(String(64), unique=True)
    role_key: Mapped[str] = mapped_column(ForeignKey("role.key"))   # hak akses = role ini, hanya GET
    site: Mapped[str | None] = mapped_column(String(120))
    created_by: Mapped[str] = mapped_column(String(60))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    expires_at: Mapped[datetime | None] = mapped_column(DateTime)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime)


class Webhook(Base):
    """Tujuan notifikasi (Teams, Slack, Telegram, JSON umum). URL dienkripsi karena memuat token."""
    __tablename__ = "webhook"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(80))
    kind: Mapped[str] = mapped_column(String(20), default="generic")
    url_enc: Mapped[str] = mapped_column(Text)
    events: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    last_at: Mapped[datetime | None] = mapped_column(DateTime)
    last_status: Mapped[str | None] = mapped_column(String(200))

class ZbxHost(Base):
    """Perangkat dari Zabbix (host group CCTV-* dan OPERASIONAL-*): snapshot status terkini dari sinkron terakhir."""
    __tablename__ = "zbx_host"
    hostid: Mapped[str] = mapped_column(String(20), primary_key=True)
    host: Mapped[str] = mapped_column(String(255))
    name: Mapped[str] = mapped_column(String(255))
    kind: Mapped[str] = mapped_column(String(40), default="")          # CCTV | OPERASIONAL (dari prefix host group)
    code: Mapped[str] = mapped_column(String(40), default="")          # kode lokasi dari nama grup, mis. JNR
    group_name: Mapped[str] = mapped_column(String(255), default="")
    zone: Mapped[str] = mapped_column(String(40), default="")          # dari nama host: Entitas-Cabang-Zona-SubZona-KodePerangkat-Urut
    subzone: Mapped[str] = mapped_column(String(80), default="")
    dev_code: Mapped[str] = mapped_column(String(20), default="")
    ip: Mapped[str] = mapped_column(String(45), default="", server_default="", index=True)   # first interface address (used to match Milestone cameras)
    groups: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    status: Mapped[str] = mapped_column(String(20), default="up")      # up | down | maintenance | disabled
    down_since: Mapped[datetime | None] = mapped_column(DateTime)
    problem: Mapped[str | None] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

class ZbxLocMap(Base):
    """Pemetaan kode lokasi di nama host group Zabbix (mis. TJE, BLW) ke nama lokasi di master Lokasi. Kode baru terisi otomatis saat sinkron; Admin tinggal mengisi lokasinya."""
    __tablename__ = "zbx_loc_map"
    code: Mapped[str] = mapped_column(String(40), primary_key=True)
    site: Mapped[str | None] = mapped_column(String(120))
    note: Mapped[str | None] = mapped_column(String(200))


MASTER["zbx_loc"] = (ZbxLocMap, "Kode Lokasi Zabbix")

class DevCode(Base):
    """Kamus kode perangkat pada nama host (mis. CFIX = CCTV Fixed). Kode baru terdaftar otomatis saat sinkron; Admin mengisi labelnya."""
    __tablename__ = "dev_code"
    code: Mapped[str] = mapped_column(String(20), primary_key=True)
    label: Mapped[str | None] = mapped_column(String(80))
    note: Mapped[str | None] = mapped_column(String(200))


MASTER["dev_code"] = (DevCode, "Kode Perangkat")
class WifiClient(Base):
    """Client WiFi yang sedang terhubung menurut Ruckus SmartZone (vSZ): snapshot dari sinkron terakhir."""
    __tablename__ = "wifi_client"
    mac: Mapped[str] = mapped_column(String(20), primary_key=True)
    ip: Mapped[str | None] = mapped_column(String(64))
    username: Mapped[str | None] = mapped_column(String(160))
    hostname: Mapped[str | None] = mapped_column(String(160))
    ssid: Mapped[str | None] = mapped_column(String(120))
    ap_name: Mapped[str | None] = mapped_column(String(160))
    ap_mac: Mapped[str | None] = mapped_column(String(20))
    zone: Mapped[str | None] = mapped_column(String(120))
    os: Mapped[str | None] = mapped_column(String(120))
    rssi: Mapped[int | None] = mapped_column(Integer)
    vlan: Mapped[int | None] = mapped_column(Integer)
    started_at: Mapped[datetime | None] = mapped_column(DateTime)
    rx_bytes: Mapped[int | None] = mapped_column(BigInteger)
    tx_bytes: Mapped[int | None] = mapped_column(BigInteger)
    raw: Mapped[dict | None] = mapped_column(JSONB)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

class WifiAp(Base):
    """Access Point dari Ruckus vSZ: snapshot status terkini."""
    __tablename__ = "wifi_ap"
    mac: Mapped[str] = mapped_column(String(20), primary_key=True)
    name: Mapped[str | None] = mapped_column(String(160))
    zone: Mapped[str | None] = mapped_column(String(120))
    ap_group: Mapped[str | None] = mapped_column(String(120))
    status: Mapped[str | None] = mapped_column(String(40))
    model: Mapped[str | None] = mapped_column(String(60))
    ip: Mapped[str | None] = mapped_column(String(64))
    clients: Mapped[int | None] = mapped_column(Integer)
    firmware: Mapped[str | None] = mapped_column(String(60))
    location: Mapped[str | None] = mapped_column(String(200))
    last_seen: Mapped[datetime | None] = mapped_column(DateTime)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class WifiStat(Base):
    """Riwayat per sinkron untuk grafik tren client dan trafik WiFi."""
    __tablename__ = "wifi_stat"
    at: Mapped[datetime] = mapped_column(DateTime, primary_key=True)
    clients: Mapped[int] = mapped_column(Integer, default=0)
    users: Mapped[int] = mapped_column(Integer, default=0)
    rx_bytes: Mapped[int] = mapped_column(BigInteger, default=0)
    tx_bytes: Mapped[int] = mapped_column(BigInteger, default=0)
    ap_online: Mapped[int] = mapped_column(Integer, default=0)
    ap_total: Mapped[int] = mapped_column(Integer, default=0)

class WifiSession(Base):
    """Riwayat sesi client WiFi (satu baris per sesi): dasar laporan per zone, client, SSID, dan rentang waktu. Sesi aktif diperbarui tiap sinkron, sesi selesai dilengkapi dari riwayat vSZ."""
    __tablename__ = "wifi_session"
    mac: Mapped[str] = mapped_column(String(20), primary_key=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, primary_key=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime)
    last_seen: Mapped[datetime | None] = mapped_column(DateTime)
    ip: Mapped[str | None] = mapped_column(String(64))
    username: Mapped[str | None] = mapped_column(String(160))
    hostname: Mapped[str | None] = mapped_column(String(160))
    device: Mapped[str | None] = mapped_column(String(80))
    ssid: Mapped[str | None] = mapped_column(String(120))
    ap_mac: Mapped[str | None] = mapped_column(String(20))
    ap_name: Mapped[str | None] = mapped_column(String(160))
    zone: Mapped[str | None] = mapped_column(String(120))
    loc: Mapped[str | None] = mapped_column(String(120))
    auth: Mapped[str | None] = mapped_column(String(60))
    rx_bytes: Mapped[int | None] = mapped_column(BigInteger)
    tx_bytes: Mapped[int | None] = mapped_column(BigInteger)


class ZbxEvent(Base):
    """Riwayat kejadian down perangkat dari Zabbix (event problem yang cocok dengan pola down): dasar laporan downtime per lokasi, tipe, dan perangkat."""
    __tablename__ = "zbx_event"
    eventid: Mapped[str] = mapped_column(String(20), primary_key=True)
    hostid: Mapped[str] = mapped_column(String(20), index=True)
    host_name: Mapped[str | None] = mapped_column(String(255))
    kind: Mapped[str | None] = mapped_column(String(40))
    code: Mapped[str | None] = mapped_column(String(40))
    dev_code: Mapped[str | None] = mapped_column(String(20))
    name: Mapped[str | None] = mapped_column(String(255))
    start_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    end_at: Mapped[datetime | None] = mapped_column(DateTime)


class ZbxStat(Base):
    """Cuplikan per jam jumlah perangkat menurut kategori dan status (untuk tren availability)."""
    __tablename__ = "zbx_stat"
    hour: Mapped[datetime] = mapped_column(DateTime, primary_key=True)
    kind: Mapped[str] = mapped_column(String(40), primary_key=True)
    total: Mapped[int] = mapped_column(Integer, default=0)
    up: Mapped[int] = mapped_column(Integer, default=0)
    down: Mapped[int] = mapped_column(Integer, default=0)
    degraded: Mapped[int] = mapped_column(Integer, default=0)
    maintenance: Mapped[int] = mapped_column(Integer, default=0)

class XdrAlert(Base):
    """Alert Workbench dari Trend Micro Vision One (XDR): satu baris per alert, diperbarui saat statusnya berubah."""
    __tablename__ = "xdr_alert"
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    incident_id: Mapped[str | None] = mapped_column(String(80))
    model: Mapped[str | None] = mapped_column(String(300))
    model_type: Mapped[str | None] = mapped_column(String(40))
    severity: Mapped[str | None] = mapped_column(String(20), index=True)
    score: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str | None] = mapped_column(String(40))
    investigation_status: Mapped[str | None] = mapped_column(String(40))
    provider: Mapped[str | None] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime)
    owners: Mapped[list | None] = mapped_column(JSONB)
    impact: Mapped[dict | None] = mapped_column(JSONB)
    indicators: Mapped[list | None] = mapped_column(JSONB)
    link: Mapped[str | None] = mapped_column(String(600))
    description: Mapped[str | None] = mapped_column(Text)
    investigation_result: Mapped[str | None] = mapped_column(String(80))
    entities: Mapped[list | None] = mapped_column(JSONB)          # host/akun terdampak: [{type, name, ips}]
    techniques: Mapped[list | None] = mapped_column(JSONB)        # ID teknik MITRE ATT&CK
    rules: Mapped[list | None] = mapped_column(JSONB)             # nama aturan deteksi yang cocok
    fetched_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class CctvHardware(Base):
    """Hardware di Milestone XProtect (NVR/interconnect per lokasi): inventaris dari RESTful API, bukan status real-time."""
    __tablename__ = "cctv_hardware"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    server: Mapped[str] = mapped_column(String(80), default="HO")
    name: Mapped[str] = mapped_column(String(200))
    address: Mapped[str | None] = mapped_column(String(300))
    host: Mapped[str | None] = mapped_column(String(120))
    model: Mapped[str | None] = mapped_column(String(80))
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    recorder: Mapped[str | None] = mapped_column(String(120))
    cameras: Mapped[int] = mapped_column(Integer, default=0)
    cameras_enabled: Mapped[int] = mapped_column(Integer, default=0)
    modified_at: Mapped[datetime | None] = mapped_column(DateTime)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class CctvCamera(Base):
    """Kamera di Milestone XProtect: satu baris per kamera, lokasi dan IP diurai dari nama kamera."""
    __tablename__ = "cctv_camera"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    server: Mapped[str] = mapped_column(String(80), default="HO")
    name: Mapped[str] = mapped_column(String(300))
    location: Mapped[str | None] = mapped_column(String(160))
    ip: Mapped[str | None] = mapped_column(String(45), index=True)
    channel: Mapped[int | None] = mapped_column(Integer)
    hardware_id: Mapped[str | None] = mapped_column(String(40), index=True)
    hardware: Mapped[str | None] = mapped_column(String(200))
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    recording: Mapped[bool] = mapped_column(Boolean, default=False)
    fps: Mapped[str | None] = mapped_column(String(10))
    modified_at: Mapped[datetime | None] = mapped_column(DateTime)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Insight(Base):
    """Temuan analisis otomatis (anomali, tren, kejadian berulang). Kunci unik mencegah duplikat; temuan yang tidak muncul lagi berstatus 'selesai'."""
    __tablename__ = "insight"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key: Mapped[str] = mapped_column(String(160))
    kind: Mapped[str] = mapped_column(String(20))
    severity: Mapped[str] = mapped_column(String(10))            # info | warn | crit
    title: Mapped[str] = mapped_column(String(200))
    detail: Mapped[str] = mapped_column(Text)
    tab: Mapped[str | None] = mapped_column(String(30))          # halaman rujukan
    site: Mapped[str | None] = mapped_column(String(120))
    metric: Mapped[dict | None] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(String(10), default="new")    # new | read | dismissed | resolved
    first_seen: Mapped[datetime] = mapped_column(DateTime)
    last_seen: Mapped[datetime] = mapped_column(DateTime)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime)
    ack_by: Mapped[str | None] = mapped_column(String(60))
    ack_at: Mapped[datetime | None] = mapped_column(DateTime)
    notified: Mapped[bool] = mapped_column(Boolean, default=False)
    reason: Mapped[str | None] = mapped_column(String(200))             # why it was dismissed
    suppress_until: Mapped[datetime | None] = mapped_column(DateTime)   # a dismissed finding stays hidden until then
    handover_id: Mapped[int | None] = mapped_column(Integer)            # handover created from this finding
    __table_args__ = (Index("ix_insight_key_open", "key", "status"),)


class SocFwDay(Base):
    """Palo Alto events per day and firewall (Panorama device name): severity and action counts, traffic."""
    __tablename__ = "soc_fw_day"
    day: Mapped[date] = mapped_column(Date, primary_key=True, index=True)
    fw: Mapped[str] = mapped_column(String(120), primary_key=True)
    sev: Mapped[dict] = mapped_column(JSONB, default=dict)     # severity -> events
    act: Mapped[dict] = mapped_column(JSONB, default=dict)     # action -> events
    typ: Mapped[dict] = mapped_column(JSONB, default=dict)     # threat type -> events
    cat: Mapped[dict] = mapped_column(JSONB, default=dict)     # threat category -> events
    app: Mapped[dict] = mapped_column(JSONB, default=dict)     # application -> bytes (top 40)
    src: Mapped[dict] = mapped_column(JSONB, default=dict)     # source IP -> bytes (top 25)
    bytes: Mapped[int] = mapped_column(BigInteger, default=0)
    sessions: Mapped[int] = mapped_column(BigInteger, default=0)


class SocFwMap(Base):
    """Admin override: which location a firewall belongs to (the automatic name match is used when a firewall is not listed here)."""
    __tablename__ = "soc_fw_map"
    fw: Mapped[str] = mapped_column(String(120), primary_key=True)
    site: Mapped[str | None] = mapped_column(String(120))
