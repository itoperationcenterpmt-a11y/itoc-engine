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


class Layout(Base):
    """Tata letak halaman dashboard (Overview, Service Desk, NOC, SOC): urutan, ukuran, judul, tampil/sembunyi tiap blok. Diatur lewat tombol Customize."""
    __tablename__ = "layout"
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
    "isp": (Isp, "ISP"), "sla_target": (SlaTarget, "Target SLA"), "prtg_sensor": (PrtgSensor, "Sensor & kapasitas"),
    "module": (Module, "Modul / menu"), "widget": (Widget, "Widget grafik"), "role": (Role, "Role & akses"), "formula": (Formula, "Definisi rumus"),
    "data_source": (DataSource, "Sumber data"),
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


MASTER["zbx_loc"] = (ZbxLocMap, "Zabbix: kode ke lokasi")

class DevCode(Base):
    """Kamus kode perangkat pada nama host (mis. CFIX = CCTV Fixed). Kode baru terdaftar otomatis saat sinkron; Admin mengisi labelnya."""
    __tablename__ = "dev_code"
    code: Mapped[str] = mapped_column(String(20), primary_key=True)
    label: Mapped[str | None] = mapped_column(String(80))
    note: Mapped[str | None] = mapped_column(String(200))


MASTER["dev_code"] = (DevCode, "Zabbix: kode perangkat")
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
