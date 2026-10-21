"""Membangun docs/Paparan-Dashboard-IT-Pelindo-Multi-Terminal.pptx (python-pptx). Jalankan: python build_paparan.py <folder keluaran>.
Angka di slide diambil dari kondisi aplikasi saat dokumen dibuat (Oktober 2026); perbarui sebelum dipakai ulang."""
import sys
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE, MSO_CONNECTOR
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.chart.data import CategoryChartData
from pptx.enum.chart import XL_CHART_TYPE, XL_LABEL_POSITION
from pptx.oxml.ns import qn
from lxml import etree

OUT = sys.argv[1] if len(sys.argv) > 1 else "."
NAVY, NAVY2, INK, MUTED = "0B1F3A", "16335C", "14243A", "5B6B82"
TEAL, TEAL_D, AMBER, RED, GREEN = "0FA3B1", "0B7C87", "F59E0B", "E5484D", "2FB67C"
BG, CARD, LINE, ICE = "F4F7FB", "FFFFFF", "DCE4EF", "CFE3F5"
FONT = "Calibri"
rgb = lambda h: RGBColor.from_string(h)

prs = Presentation()
prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
W, H, M = 13.333, 7.5, 0.6
BLANK = prs.slide_layouts[6]
state = {"n": 0}


def bg(slide, color):
    f = slide.background.fill
    f.solid()
    f.fore_color.rgb = rgb(color)


def shadow(shape, blur=10, dist=2, alpha=18):
    sp = shape._element.spPr
    for e in sp.findall(qn("a:effectLst")):
        sp.remove(e)
    eff = etree.SubElement(sp, qn("a:effectLst"))
    sh = etree.SubElement(eff, qn("a:outerShdw"), blurRad=str(int(blur * 12700)), dist=str(int(dist * 12700)), dir="5400000", algn="t", rotWithShape="0")
    clr = etree.SubElement(sh, qn("a:srgbClr"), val="0B1F3A")
    etree.SubElement(clr, qn("a:alpha"), val=str(alpha * 1000))


def box(slide, x, y, w, h, fill=CARD, line=None, radius=0.06, shape=MSO_SHAPE.ROUNDED_RECTANGLE, shade=True, name=None):
    s = slide.shapes.add_shape(shape, Inches(x), Inches(y), Inches(w), Inches(h))
    if shape == MSO_SHAPE.ROUNDED_RECTANGLE:
        s.adjustments[0] = radius
    if fill:
        s.fill.solid()
        s.fill.fore_color.rgb = rgb(fill)
    else:
        s.fill.background()
    if line:
        s.line.color.rgb = rgb(line)
        s.line.width = Pt(1)
    else:
        s.line.fill.background()
    if shade and fill:
        shadow(s)
    else:
        s.shadow.inherit = False
    if name:
        s.name = name
    return s


def text(slide, x, y, w, h, content, size=14, bold=False, color=INK, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP, italic=False, name=None, space=0):
    t = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = t.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    tf.vertical_anchor = anchor
    lines = content if isinstance(content, list) else [content]
    for i, ln in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        if space:
            p.space_after = Pt(space)
        runs = ln if isinstance(ln, list) else [(ln, {})]
        for r in runs:
            txt, o = (r if isinstance(r, tuple) else (r, {}))
            run = p.add_run()
            run.text = txt
            f = run.font
            f.name, f.size, f.bold, f.italic = FONT, Pt(o.get("size", size)), o.get("bold", bold), o.get("italic", italic)
            f.color.rgb = rgb(o.get("color", color))
    if name:
        t.name = name
    return t


def bullets(slide, x, y, w, h, items, size=14, color=INK, space=6, bullet_color=TEAL):
    t = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = t.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    for i, it in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.space_after = Pt(space)
        pPr = p._p.get_or_add_pPr()
        pPr.set("marL", str(int(0.2 * 914400)))
        pPr.set("indent", str(int(-0.2 * 914400)))
        bc = etree.SubElement(pPr, qn("a:buClr"))
        etree.SubElement(bc, qn("a:srgbClr"), val=bullet_color)
        etree.SubElement(pPr, qn("a:buFont"), typeface="Arial")
        etree.SubElement(pPr, qn("a:buChar"), char="•")
        runs = it if isinstance(it, list) else [(it, {})]
        for r in runs:
            txt, o = (r if isinstance(r, tuple) else (r, {}))
            run = p.add_run()
            run.text = txt
            f = run.font
            f.name, f.size, f.bold = FONT, Pt(o.get("size", size)), o.get("bold", False)
            f.color.rgb = rgb(o.get("color", color))
    return t


def new(title=None, dark=False, notes=""):
    s = prs.slides.add_slide(BLANK)
    state["n"] += 1
    bg(s, NAVY if dark else BG)
    if title:
        text(s, M, 0.42, W - 2 * M, 0.8, title, size=34, bold=True, color="FFFFFF" if dark else NAVY, anchor=MSO_ANCHOR.MIDDLE, name="Judul")
    if not dark:
        text(s, M, 7.08, 8, 0.25, "Dashboard IT Pelindo Multi Terminal · IT Operation Center", size=10, color=MUTED, name="Footer")
        text(s, W - M - 1, 7.08, 1, 0.25, str(state["n"]), size=10, color=MUTED, align=PP_ALIGN.RIGHT, name="Nomor")
    if notes:
        s.notes_slide.notes_text_frame.text = notes
    return s


def badge(s, x, y, label, color, d=0.5, size=13):
    c = box(s, x, y, d, d, fill=color, shape=MSO_SHAPE.OVAL, shade=False)
    tf = c.text_frame
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    r = p.add_run()
    r.text = label
    r.font.name, r.font.size, r.font.bold = FONT, Pt(size), True
    r.font.color.rgb = rgb("FFFFFF")


def card(s, x, y, w, h, title, lines, tag=None, tag_color=TEAL, size=16, title_size=20):
    box(s, x, y, w, h, name="Kartu " + title[:20])
    ty = y + 0.22
    if tag:
        badge(s, x + 0.25, ty, tag, tag_color)
        text(s, x + 0.9, ty, w - 1.1, 0.5, title, size=title_size, bold=True, color=NAVY, anchor=MSO_ANCHOR.MIDDLE)
        ty += 0.75
    else:
        text(s, x + 0.25, ty, w - 0.5, 0.4, title, size=title_size, bold=True, color=NAVY)
        ty += 0.5
    bullets(s, x + 0.25, ty, w - 0.5, h - (ty - y) - 0.15, lines, size=size)


def stat(s, x, y, w, big, label, color=TEAL_D, big_size=44):
    box(s, x, y, w, 1.55, name="Statistik " + big)
    text(s, x + 0.2, y + 0.15, w - 0.4, 0.8, big, size=big_size, bold=True, color=color, anchor=MSO_ANCHOR.MIDDLE)
    text(s, x + 0.2, y + 0.98, w - 0.4, 0.5, label, size=13, color=MUTED)


def arrow(s, x1, y1, x2, y2, color=TEAL_D, width=2):
    c = s.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(x1), Inches(y1), Inches(x2), Inches(y2))
    c.line.color.rgb = rgb(color)
    c.line.width = Pt(width)
    ln = c.line._get_or_add_ln()
    etree.SubElement(ln, qn("a:tailEnd"), type="triangle", w="med", len="med")
    return c


def label_box(s, x, y, w, h, title, sub=None, fill=CARD, tcolor=NAVY, scolor=MUTED, tsize=15, ssize=12):
    box(s, x, y, w, h, fill=fill, line=LINE if fill == CARD else None, shade=(fill == CARD))
    rows = [[(title, {"bold": True, "size": tsize, "color": tcolor})]]
    for ln in (sub.split("\n") if sub else []):
        rows.append([(ln, {"size": ssize, "color": scolor})])
    text(s, x + 0.1, y + 0.08, w - 0.2, h - 0.16, rows, anchor=MSO_ANCHOR.MIDDLE, align=PP_ALIGN.CENTER)


def table(s, x, y, w, col_w, header, rows, size=12, row_h=0.42, head_h=0.46):
    gs = s.shapes.add_table(len(rows) + 1, len(header), Inches(x), Inches(y), Inches(w), Inches(head_h + row_h * len(rows)))
    t = gs.table
    for i, cw_ in enumerate(col_w):
        t.columns[i].width = Inches(cw_)
    t.rows[0].height = Inches(head_h)
    for r in range(1, len(rows) + 1):
        t.rows[r].height = Inches(row_h)

    def cell(c, txt, bold=False, color=INK, fill=None):
        c.margin_left = c.margin_right = Inches(0.1)
        c.margin_top = c.margin_bottom = Inches(0.04)
        c.vertical_anchor = MSO_ANCHOR.MIDDLE
        tf = c.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        run = p.add_run()
        run.text = txt
        run.font.name, run.font.size, run.font.bold = FONT, Pt(size), bold
        run.font.color.rgb = rgb(color)
        if fill:
            c.fill.solid()
            c.fill.fore_color.rgb = rgb(fill)
    for j, h_ in enumerate(header):
        cell(t.cell(0, j), h_, True, "FFFFFF", NAVY)
    for i, row in enumerate(rows, 1):
        for j, v in enumerate(row):
            cell(t.cell(i, j), v, bold=(j == 0), fill=("FFFFFF" if i % 2 else "EEF3F9"))
    return t


# ---------------------------------------------------------------- 1. Judul
s = new(dark=True, notes="Pembuka: aplikasi ini adalah satu layar kerja untuk ITOC. Paparan menjelaskan fungsi, arsitektur, data, keamanan, dan langkah berikutnya.")
text(s, M, 1.55, 9, 0.5, "PAPARAN APLIKASI", size=16, bold=True, color="7FD6DF")
text(s, M, 2.1, 11.5, 2.0, ["Dashboard IT", "Pelindo Multi Terminal"], size=54, bold=True, color="FFFFFF", name="Judul")
text(s, M, 4.4, 11, 0.9, ["Satu layar untuk ticketing, jaringan, keamanan siber, perangkat, dan personel ITOC", "IT Operation Center · Oktober 2026"], size=18, color=ICE, space=6)
for i, (n, l) in enumerate([("6", "sumber data terintegrasi"), ("9", "menu dan sub-menu kerja"), ("7", "role akses")]):
    x = M + i * 3.2
    box(s, x, 5.7, 2.95, 1.05, fill=NAVY2, shade=False)
    text(s, x + 0.2, 5.75, 0.9, 0.95, n, size=40, bold=True, color="7FD6DF", anchor=MSO_ANCHOR.MIDDLE)
    text(s, x + 1.1, 5.75, 1.7, 0.95, l, size=14, color="FFFFFF", anchor=MSO_ANCHOR.MIDDLE)

# ---------------------------------------------------------------- 2. Ringkasan
s = new("Satu layar kerja untuk seluruh operasional TI terminal", notes="Pesan utama: konsolidasi data dari enam sistem ke satu aplikasi, tersimpan di database sendiri, dengan input manual tetap sebagai validasi.")
text(s, M, 1.45, 6.3, 1.5, "Aplikasi ini menarik data dari enam sistem yang sebelumnya dilihat terpisah, menyimpannya di database sendiri, dan menyajikannya sebagai satu dashboard untuk operator shift, koordinator, dan manajemen.", size=17, color=INK)
bullets(s, M, 3.3, 6.3, 3.4, [
    [("Informatif: ", {"bold": True}), ("ringkasan gabungan Network dan Cyber Security, plus rincian tiap sumber.", {})],
    [("Terkendali: ", {"bold": True}), ("role, audit log, dan aksi sensitif (putus sesi WiFi) dibatasi.", {})],
    [("Tahan banting: ", {"bold": True}), ("riwayat tersimpan; bila API gagal, impor manual tetap bisa dipakai.", {})],
    [("Siap diaudit: ", {"bold": True}), ("hardening keamanan dan pemeriksaan konfigurasi bawaan.", {})]], size=16, space=10)
stat(s, 7.4, 1.5, 2.6, "6", "sumber data terintegrasi")
stat(s, 10.2, 1.5, 2.55, "38", "tabel PostgreSQL dan 26 migrasi")
stat(s, 7.4, 3.3, 2.6, "0", "temuan critical/high pada security-check", color=GREEN)
stat(s, 10.2, 3.3, 2.55, "10", "jenis laporan Excel, PDF, PowerPoint")
box(s, 7.4, 5.1, 5.35, 1.55, fill=NAVY, shade=True)
text(s, 7.7, 5.2, 4.8, 1.35, [[("Prinsip: ", {"bold": True, "color": "7FD6DF"}), ("dashboard membaca dari database sendiri, bukan langsung dari sumber. Data tarikan dan data manual hidup berdampingan.", {"color": "FFFFFF"})]], size=15, anchor=MSO_ANCHOR.MIDDLE)

# ---------------------------------------------------------------- 3. Prinsip
s = new("Empat prinsip yang membentuk aplikasi ini", notes="Prinsip desain yang menjelaskan banyak keputusan teknis: data disimpan sendiri, manual tidak ditimpa, aksi dibatasi, dan konfigurasi bisa diubah dari menu Admin.")
cw = (W - 2 * M - 0.6) / 4
for i, (tag, ttl, ls) in enumerate([
    ("1", "Satu pandangan", ["Overview dan ringkasan gabungan", "Status hari ini per bidang", "Perhatian dikumpulkan di satu daftar"]),
    ("2", "Data milik sendiri", ["Semua tarikan API disimpan di PostgreSQL", "Riwayat WiFi, down Zabbix, alert XDR", "Laporan dan grafik dihitung dari database"]),
    ("3", "Manual tetap hidup", ["CSV, PDF, Excel tetap bisa diunggah", "Tidak tertimpa data API", "Selisih dengan API dicatat sebagai validasi"]),
    ("4", "Terkendali", ["Role dan lokasi membatasi data", "Aksi tulis dibatasi dan diaudit", "Parameter diatur dari menu Admin, bukan kode"])]):
    card(s, M + i * (cw + 0.2), 1.6, cw, 4.9, ttl, ls, tag=tag, size=14)

# ---------------------------------------------------------------- 4. Peta menu
s = new("Peta menu: sembilan area kerja dalam satu navigasi", notes="Menu Network dan Cyber Security memiliki ringkasan gabungan dan sub-menu per sumber. Report memuat Handover dan Data.")
tops = [("Overview", "status hari ini, perhatian, ringkasan semua bidang", None), ("Ticketing", "ManageEngine: tiket, SLA, teknisi", None),
        ("Network", "Summary gabungan", ["PRTG: link, trafik, SLA", "WiFi: Ruckus, client, AP"]), ("Cyber Security", "Summary gabungan", ["NDR: Palo Alto Panorama", "XDR: Trend Micro Vision One"]),
        ("Devices", "Zabbix: status, peta, riwayat down", None), ("Personnel", "jadwal shift dan on duty", None),
        ("Report", "Excel, PDF, PowerPoint", ["Handover: serah terima shift", "Data: kelengkapan dan unggah RAW"]), ("Admin", "pengguna, role, integrasi, parameter, audit", None)]
cw, chh = 2.85, 2.35
for i, (nm, sub, kids) in enumerate(tops):
    x, y = M + (i % 4) * (cw + 0.2), 1.5 + (i // 4) * (chh + 0.25)
    box(s, x, y, cw, chh, name="Menu " + nm)
    text(s, x + 0.2, y + 0.18, cw - 0.4, 0.4, nm, size=19, bold=True, color=NAVY)
    text(s, x + 0.2, y + 0.62, cw - 0.4, 0.62, sub, size=13, color=MUTED)
    for k, kd in enumerate(kids or []):
        box(s, x + 0.2, y + 1.3 + k * 0.46, cw - 0.4, 0.38, fill="E3F4F6", shade=False)
        text(s, x + 0.3, y + 1.3 + k * 0.46, cw - 0.6, 0.38, kd, size=12, color=TEAL_D, bold=True, anchor=MSO_ANCHOR.MIDDLE)

# ---------------------------------------------------------------- 5. Arsitektur
s = new("Arsitektur: sumber, penyimpan, penyaji", notes="Alur: konektor di worker menarik data terjadwal ke PostgreSQL; API FastAPI menghitung tampilan dari database; browser hanya menampilkan. Impor manual masuk ke database yang sama.")
srcs = [("ManageEngine", "tiket"), ("PRTG", "link dan trafik"), ("Zabbix", "perangkat"), ("Ruckus vSZ", "WiFi"), ("Palo Alto Panorama", "NDR"), ("Trend Micro Vision One", "XDR")]
for i, (a, b) in enumerate(srcs):
    label_box(s, M, 1.45 + i * 0.82, 2.7, 0.7, a, b)
    arrow(s, M + 2.7, 1.8 + i * 0.82, 4.2, 3.9, color="8FA3BD", width=1.25)
label_box(s, 4.2, 3.15, 2.2, 1.5, "Konektor + penjadwal", "worker (APScheduler)\nAPI, jam tetap, backfill", fill=TEAL, tcolor="FFFFFF", scolor="E6FAFC")
arrow(s, 6.4, 3.9, 7.1, 3.9)
label_box(s, 7.1, 2.95, 2.2, 1.9, "PostgreSQL 16", "38 tabel · riwayat\nrahasia terenkripsi", fill=NAVY, tcolor="FFFFFF", scolor=ICE)
arrow(s, 9.3, 3.9, 9.9, 3.9)
label_box(s, 9.9, 3.15, 1.45, 1.5, "FastAPI", "auth · hitung\nlaporan", fill=NAVY2, tcolor="FFFFFF", scolor=ICE)
arrow(s, 11.35, 3.9, 11.75, 3.9)
label_box(s, 11.75, 3.15, 0.98, 1.5, "UI", "browser", fill=CARD, tsize=15)
label_box(s, 4.2, 5.5, 2.2, 0.95, "Impor manual", "CSV · PDF · Excel", fill="E3F4F6", tcolor=TEAL_D, scolor=TEAL_D)
arrow(s, 5.3, 5.5, 7.6, 4.85, color=TEAL_D)
text(s, 7.1, 5.5, 5.6, 1.3, ["Backend: FastAPI + SQLAlchemy + Alembic", "Frontend: JavaScript murni, Leaflet untuk peta", "Rahasia konektor: Fernet di database; sesi: cookie HttpOnly"], size=14, color=MUTED, space=4)

# ---------------------------------------------------------------- 6. Integrasi
s = new("Enam integrasi, jadwal dan cara tarik masing-masing", notes="Setiap sumber punya kartu di Admin > Integrations dengan tombol Test dan Sync now. Panorama memakai jam tetap; yang lain interval.")
table(s, M, 1.5, W - 2 * M, [2.5, 3.1, 2.4, 4.13], ["Sumber", "Cara tarik", "Jadwal", "Isi yang disimpan"], [
    ["ManageEngine SDP", "REST API v3, inkremental", "tiap 15 menit", "Tiket, kategori, SLA, teknisi"],
    ["PRTG", "historicdata per sensor", "tiap jam", "Trafik, downtime, kejadian per link"],
    ["Zabbix 7", "JSON-RPC + event.get", "tiap 5 menit", "Perangkat, status, riwayat down 60 hari"],
    ["Ruckus vSZ", "Public REST API v11", "tiap 5 menit", "Client, AP, sesi, tren, usage"],
    ["Palo Alto Panorama", "XML API, dynamic report", "00.00 dan 12.00 WIB", "Ringkasan harian dan tabel Top (7, 30 hari, bulanan)"],
    ["Trend Micro Vision One", "REST API v3 (region Singapura)", "tiap 15 menit", "Alert Workbench: host, akun, MITRE, insiden"]], size=14, row_h=0.62)
text(s, M, 5.95, W - 2 * M, 0.9, [[("Tersedia juga impor manual ", {"bold": True, "color": NAVY}), ("untuk SOC (CSV Panorama), PRTG (PDF harian), dan tiket (Excel). Impor manual dipakai sebagai validasi dan tidak tertimpa data API.", {})]], size=15, color=INK)

# ---------------------------------------------------------------- 7. Data tersimpan
s = new("Yang tersimpan di database server ini", notes="Angka diambil dari database saat dokumen dibuat. Semua tampilan dan laporan dihitung dari tabel-tabel ini.")
cd = CategoryChartData()
data = [("Data trafik PRTG per jam", 35427), ("Sesi WiFi", 13496), ("Kejadian down Zabbix", 12946), ("Tiket", 2085), ("Perangkat Zabbix", 1772), ("Hari SOC (ringkasan)", 195), ("Access Point", 186), ("Alert XDR", 33)]
cd.categories = [d[0] for d in data]
cd.add_series("Jumlah baris", [d[1] for d in data])
gf = s.shapes.add_chart(XL_CHART_TYPE.BAR_CLUSTERED, Inches(M), Inches(1.5), Inches(7.6), Inches(5.3), cd)
gf.name = "Grafik data tersimpan"
ch = gf.chart
ch.has_legend = False
ch.has_title = False
pl = ch.plots[0]
pl.gap_width = 45
pl.has_data_labels = True
dl = pl.data_labels
dl.font.size, dl.font.name = Pt(13), FONT
dl.font.color.rgb = rgb(INK)
dl.number_format, dl.number_format_is_linked = "#,##0", False
dl.position = XL_LABEL_POSITION.OUTSIDE_END
pl.series[0].format.fill.solid()
pl.series[0].format.fill.fore_color.rgb = rgb(TEAL)
ch.category_axis.tick_labels.font.size = Pt(13)
ch.category_axis.tick_labels.font.name = FONT
ch.category_axis.reverse_order = True
ch.category_axis.format.line.color.rgb = rgb(LINE)
ch.value_axis.visible = False
ch.value_axis.has_major_gridlines = False
bullets(s, 8.6, 1.6, 4.15, 5.2, [
    [("Dibaca dari database, ", {"bold": True}), ("bukan dari sumber, sehingga halaman cepat dan tetap tampil saat sumber tidak terjangkau.", {})],
    [("Riwayat dibangun sendiri: ", {"bold": True}), ("sesi WiFi, kejadian down, tren per jam, alert XDR.", {})],
    [("Retensi diatur parameter: ", {"bold": True}), ("sesi WiFi 90 hari, tren 400 hari.", {})],
    [("Rahasia terenkripsi ", {"bold": True}), ("(token, password konektor, SMTP, webhook) dan tidak dikirim ke browser.", {})],
    [("Backup database ", {"bold": True}), ("menjadi sumber kebenaran; jadwalkan terenkripsi di luar server.", {})]], size=14, space=10)

# ---------------------------------------------------------------- 8. Overview
s = new("Overview: status hari ini dan semua bidang", notes="Overview menampilkan kartu status per bidang dengan warna, daftar perhatian, siapa yang bertugas, dan panel ringkas tiap sumber. Semua panel bisa diatur lewat Customize.")
for i, (nm, tone, head, sub) in enumerate([("TICKETING", GREEN, "Terkendali", "tiket, open, SLA"), ("NETWORK", AMBER, "AP offline", "availability link, client WiFi"), ("CYBER SECURITY", AMBER, "Perlu tindak lanjut", "event NDR, alert XDR"), ("DEVICES", AMBER, "Perangkat down", "availability, total perangkat"), ("HANDOVER", GREEN, "Terkendali", "serah terima shift")]):
    x = M + i * 2.46
    box(s, x, 1.5, 2.3, 1.55, name="Status " + nm)
    box(s, x + 0.2, 1.72, 0.2, 0.2, fill=tone, shape=MSO_SHAPE.OVAL, shade=False)
    text(s, x + 0.5, 1.66, 1.7, 0.32, nm, size=11, bold=True, color=MUTED, anchor=MSO_ANCHOR.MIDDLE)
    text(s, x + 0.2, 2.08, 1.95, 0.4, head, size=16, bold=True, color=NAVY)
    text(s, x + 0.2, 2.5, 1.95, 0.5, sub, size=12, color=MUTED)
card(s, M, 3.35, 5.9, 3.4, "Yang ditampilkan", ["Status Hari Ini per bidang (hijau, kuning, merah)", "Attention: tiket lama, link di bawah target, alert tanpa blokir, AP offline, backlog XDR", "On Duty dan eskalasi, handover yang masih terbuka", "Grafik: tiket, downtime link, event NDR, alert XDR, tren WiFi"])
card(s, 6.8, 3.35, 5.93, 3.4, "Diatur sesuai kebutuhan", ["Customize: pindah, ubah ukuran, sembunyikan, tambah dari katalog", "Tata letak bisa berbeda per role", "Filter periode, shift, dan lokasi berlaku di semua panel", "Bandingkan dengan periode sebelumnya"])

# ---------------------------------------------------------------- 9. Network
s = new("Network: ringkasan gabungan PRTG dan WiFi", notes="Network Summary menggabungkan link PRTG dan WiFi Ruckus, termasuk tabel per lokasi. Sub-menu PRTG dan WiFi memuat rincian masing-masing.")
cw = (W - 2 * M - 0.5) / 3
card(s, M, 1.5, cw, 5.2, "Summary", ["Perhatian gabungan: link di bawah target, AP offline, sinyal lemah", "KPI link dan KPI WiFi berdampingan", "Downtime per hari dan top 5 link", "Ringkasan per lokasi: link, availability, AP, client"], tag="Σ", tag_color=NAVY)
card(s, M + cw + 0.25, 1.5, cw, 5.2, "PRTG · link dan trafik", ["Availability terhadap target SLA", "Trafik total dan per sensor, utilisasi puncak", "Ranking downtime, 20 kejadian terlama", "Ringkasan per ISP dan per lokasi", "Data per jam dari API; PDF harian tetap terbaca"], tag="P", tag_color=TEAL)
card(s, M + 2 * (cw + 0.25), 1.5, cw, 5.2, "WiFi · Ruckus vSZ", ["Client aktif, AP online, sinyal lemah, usage", "Portal Users: client SSID portal, status login", "Filter band, SSID, zone, lokasi", "Riwayat: usage per zone, SSID, client, jam sibuk", "Putus sesi (Disconnect, Deauth) untuk role berizin"], tag="W", tag_color=AMBER)

# ---------------------------------------------------------------- 10. Cyber
s = new("Cyber Security: NDR Palo Alto dan XDR Trend Micro", notes="Dua sumber keamanan dipisah sebagai NDR (firewall) dan XDR (endpoint). Summary menggabungkan perhatian dan KPI keduanya.")
card(s, M, 1.5, cw, 5.2, "Summary", ["Perhatian: event critical/high hanya alert, backlog XDR, data NDR belum lengkap", "KPI NDR dan XDR berdampingan", "Event dan alert per hari", "Severity, model deteksi, host terdampak, teknik MITRE"], tag="Σ", tag_color=NAVY)
card(s, M + cw + 0.25, 1.5, cw, 5.2, "NDR · Palo Alto", ["Total event, critical/high, persentase diblokir", "Per severity, tindakan, kategori ancaman, URL", "Tabel Top mengikuti filter periode", "Tarik otomatis 00.00 dan 12.00 WIB, tombol tarik manual", "Impor CSV tetap sebagai validasi"], tag="N", tag_color=TEAL)
card(s, M + 2 * (cw + 0.25), 1.5, cw, 5.2, "XDR · Trend Micro", ["Alert Workbench dengan severity dan status", "Host dan akun terdampak (dengan IP)", "Teknik MITRE ATT&CK dan insiden", "Umur backlog, hasil investigasi", "Tautan langsung ke Workbench"], tag="X", tag_color=RED)

# ---------------------------------------------------------------- 11. Devices
s = new("Devices: kondisi perangkat dari Zabbix", notes="Devices memakai nama host berpola untuk menurunkan lokasi, zona, dan tipe perangkat; kamus kodenya bisa diubah dari Admin.")
stat(s, M, 1.5, 2.9, "1.772", "perangkat dipantau (CCTV, Gate System, jaringan)")
stat(s, M, 3.25, 2.9, "51 + 36", "kode lokasi dan kode perangkat di kamus")
stat(s, M, 5.0, 2.9, "60 hari", "riwayat kejadian down langsung dari Zabbix")
card(s, 3.8, 1.5, 4.5, 5.2, "Tampilan", ["Peta lokasi (Leaflet, OpenStreetMap) dengan warna availability", "Status per kategori dan per tipe perangkat", "Down terlama, lama down, down per lokasi", "Filter lokasi, kategori, group, tipe, status", "Widget peta per group (mis. Network-SDWAN)"])
card(s, 8.5, 1.5, 4.23, 5.2, "Riwayat dan kamus", ["Kejadian down, downtime, MTTR, availability periode", "Perangkat paling sering down, masalah dominan", "Kode nama host diurai otomatis: cabang, zona, tipe, urutan", "Kode baru terdaftar otomatis untuk dilengkapi Admin"])

# ---------------------------------------------------------------- 12. Operasi
s = new("Ticketing, personel, dan serah terima shift", notes="Bagian operasional harian ITOC: tiket dari ManageEngine, jadwal rotasi, handover antar shift, dan kelengkapan data.")
cw = (W - 2 * M - 0.5) / 3
card(s, M, 1.5, cw, 5.2, "Ticketing", ["Tiket masuk, close, SLA, durasi median", "Ranking teknisi dan group", "Kategori, lokasi, jam, hari", "Tiket open terlama dan 25 tiket terlama", "Sinkron API tiap 15 menit + impor Excel"], tag="T", tag_color=TEAL)
card(s, M + cw + 0.25, 1.5, cw, 5.2, "Personnel", ["Rotasi 4 tim, 3 shift, jadwal bulanan", "Siapa bertugas sekarang dan berikutnya", "Kontak eskalasi dan layanan IT Care", "Pola rotasi dan anggota dari parameter"], tag="P", tag_color=NAVY)
card(s, M + 2 * (cw + 0.25), 1.5, cw, 5.2, "Handover dan Data", ["Serah terima shift: prioritas, tindak lanjut, penutupan", "Notifikasi webhook (Teams, Slack, Telegram)", "Kelengkapan data harian SOC dan log unggah", "Riwayat sinkron dan unggahan"], tag="H", tag_color=AMBER)

# ---------------------------------------------------------------- 13. Report
s = new("Report: sepuluh jenis laporan, tiga format, satu tampilan", notes="Semua jenis laporan memakai model yang sama: KPI, grafik, tabel, dan catatan. Format Excel, PDF, dan PowerPoint dibuat dari model yang sama sehingga angkanya identik.")
kinds = ["Summary", "Network (PRTG + WiFi)", "Cyber Security (NDR + XDR)", "Ticketing", "PRTG (Link)", "WiFi (Ruckus)", "NDR (Palo Alto)", "XDR (Trend Micro)", "Devices", "Full"]
for i, k in enumerate(kinds):
    x, y = M + (i % 5) * 2.45, 1.5 + (i // 5) * 0.8
    box(s, x, y, 2.3, 0.62, fill=CARD, line=LINE, shade=False)
    text(s, x + 0.08, y, 2.14, 0.62, k, size=13, bold=True, color=NAVY, anchor=MSO_ANCHOR.MIDDLE, align=PP_ALIGN.CENTER)
for i, (f, d) in enumerate([("Excel", "data dan format angka asli"), ("PDF", "siap cetak dan arsip"), ("PowerPoint", "template Pelindo untuk rapat")]):
    x = M + i * 4.1
    box(s, x, 3.4, 3.9, 1.2, name="Format " + f)
    text(s, x + 0.25, 3.52, 3.4, 0.5, f, size=20, bold=True, color=TEAL_D)
    text(s, x + 0.25, 4.05, 3.4, 0.4, d, size=14, color=MUTED)
bullets(s, M, 4.95, W - 2 * M, 1.9, [
    "Periode, shift, dan lokasi mengikuti filter; ukuran Compact, Standard, Full memilih jumlah grafik",
    "Bagian laporan mengikuti izin role dan lokasi yang dikunci",
    "Status perangkat dan WiFi adalah kondisi saat laporan dibuat; bagian riwayat mengikuti periode",
    "Setiap unduhan tercatat di audit log"], size=16, space=8)

# ---------------------------------------------------------------- 14. Customize
s = new("Tampilan yang bisa diatur tanpa mengubah kode", notes="Customize memberi kontrol tata letak per halaman dan per role. Katalog widget memuat panel bawaan halaman dan widget tambahan seperti peta per group.")
card(s, M, 1.5, 6.0, 5.2, "Customize per halaman dan role", ["Pindah (seret), ubah lebar, ganti judul", "Sembunyikan, hapus, atau tambah lagi dari katalog", "Setiap role bisa punya tata letak sendiri", "Reset kembali ke bawaan kapan saja", "Filter widget peta (group) langsung di toolbar"], tag="C", tag_color=TEAL)
card(s, 6.85, 1.5, 5.88, 5.2, "Filter seragam di semua menu", ["Period, Shift, Location di bar atas", "Filter khusus: Category, Group, Type, Status (Devices)", "Band, SSID, Zone (WiFi); Severity (XDR)", "Sidebar bisa diciutkan ke mode ikon", "Chip On duty hidup: jam berdetik, titik berdenyut"], tag="F", tag_color=NAVY)

# ---------------------------------------------------------------- 15. Role
s = new("Role dan hak akses", notes="Akses diatur per role: modul yang terlihat, hak unggah RAW, hak admin, dan kunci lokasi. Putus sesi WiFi dibatasi ke Super Admin, Admin, dan username tambahan (koordinator).")
table(s, M, 1.5, W - 2 * M, [2.1, 5.7, 2.1, 2.23], ["Role", "Modul yang terlihat", "Lokasi", "Catatan"], [
    ["Super Admin", "Semua modul dan Admin", "Semua", "Kelola pengguna, integrasi"],
    ["Admin", "Semua modul, Admin hanya baca", "Semua", "Koordinator ITOC"],
    ["ITOC Shift", "Overview, Ticketing, Network, Cyber, Devices, Personel, Report", "Semua", "Operator shift"],
    ["Management", "Overview, Ticketing, Network, Cyber, Devices, Personel, Report", "Semua", "Hanya melihat"],
    ["IT Care", "Overview, Ticketing, Network, Personel, Report", "Kantor pusat", "Dikunci ke lokasi"],
    ["EOS Branch", "Overview, Ticketing, Network, Personel, Report", "Lokasi akun", "Dikunci ke cabang"],
    ["WiFi Viewer", "Hanya WiFi", "Semua", "Tanpa putus sesi"]], size=13, row_h=0.58)
text(s, M, 6.15, W - 2 * M, 0.8, [[("Aksi sensitif: ", {"bold": True, "color": NAVY}), ("Disconnect dan Deauth client WiFi hanya untuk Super Admin, Admin, dan username yang didaftarkan di parameter; setiap aksi tercatat (siapa, client, SSID, AP, alasan).", {})]], size=14)

# ---------------------------------------------------------------- 16. Keamanan
s = new("Keamanan: kontrol yang sudah ada", notes="Ringkasan dari Panduan-Keamanan.md. Semua rute API wajib login kecuali login, teks publik, dan health.")
items = [("Sesi", "Cookie HttpOnly, SameSite=Strict, Secure via HTTPS; sesi gugur saat password diganti"), ("CSRF", "Header wajib untuk perubahan data pada sesi cookie"), ("Login", "bcrypt, lockout 5 gagal per 10 menit lintas worker, pesan galat seragam"),
         ("Otorisasi", "Semua /api wajib login; modul, admin, unggah, lokasi per role"), ("Input", "ORM berparameter, validasi Pydantic, unggahan dibatasi ukuran, ekstensi, isi zip"), ("Output", "Data luar di-escape, tanpa handler inline, CSP script-src 'self'"),
         ("SSRF", "URL webhook dan konektor menolak loopback dan link-local"), ("Rahasia", "Fernet di database, .env di luar git dan image, container non-root")]
cw, chh = (W - 2 * M - 0.6) / 4, 2.4
for i, (a, b) in enumerate(items):
    x, y = M + (i % 4) * (cw + 0.2), 1.5 + (i // 4) * (chh + 0.25)
    box(s, x, y, cw, chh, name="Kontrol " + a)
    text(s, x + 0.2, y + 0.2, cw - 0.4, 0.4, a, size=18, bold=True, color=TEAL_D)
    text(s, x + 0.2, y + 0.7, cw - 0.4, chh - 0.85, b, size=14, color=INK)

# ---------------------------------------------------------------- 17. Audit
s = new("Hasil audit dan kesiapan VAPT", notes="Hasil pemeriksaan otomatis (security-check) dan pip-audit. Yang masih terbuka adalah langkah di server saat go-live.")
card(s, M, 1.5, 6.0, 5.2, "Sudah diperbaiki", ["Password akun uji lemah: direset acak", "Sesi di localStorage: pindah ke cookie HttpOnly", "Lockout per proses: pindah ke database", "Dependensi rentan: pip-audit bersih", "SSRF, upload tanpa batas, header keamanan, container root"], tag="✓", tag_color=GREEN)
card(s, 6.85, 1.5, 5.88, 5.2, "Perlu dilakukan di server", ["ITOC_ENV=production dan rahasia kuat di .env", "HTTPS lewat reverse proxy (contoh Nginx tersedia)", "Verifikasi TLS konektor: aktifkan bila CA internal terpasang", "Batasi Super Admin dan jadwalkan backup terenkripsi", "Jalankan security-check sebelum VAPT"], tag="!", tag_color=AMBER)

# ---------------------------------------------------------------- 18. Deployment
s = new("Deployment dan operasi", notes="Tiga container: database, API, worker. Migrasi dan seed konfigurasi berjalan otomatis saat start. Panduan keamanan memuat contoh Nginx.")
for i, (a, b, c) in enumerate([("db", "PostgreSQL 16", "hanya 127.0.0.1, volume data"), ("api", "FastAPI + Uvicorn", "non-root, healthcheck, migrasi otomatis"), ("worker", "Penjadwal sinkron", "APScheduler, jam tetap dan interval")]):
    x = M + i * 3.0
    label_box(s, x, 1.55, 2.8, 1.45, a, b + "\n" + c, fill=NAVY if i == 1 else CARD, tcolor="FFFFFF" if i == 1 else NAVY, scolor=ICE if i == 1 else MUTED)
label_box(s, 9.65, 1.55, 3.08, 1.45, "Nginx (TLS)", "HTTPS, HSTS, pembatas laju", fill=TEAL, tcolor="FFFFFF", scolor="E6FAFC")
bullets(s, M, 3.4, 6.0, 3.4, [
    [("Konfigurasi: ", {"bold": True}), ("rahasia di .env, parameter bisnis di database lewat menu Admin.", {})],
    [("Perintah: ", {"bold": True}), ("migrate, seed-config, create-user, sync, security-check.", {})],
    [("Pemantauan: ", {"bold": True}), ("status sumber di Admin, log sinkron, audit log.", {})],
    [("Git: ", {"bold": True}), ("branch devices-map, 34 commit, belum di-push.", {})]], size=14, space=10)
box(s, 6.85, 3.4, 5.88, 3.3, fill=NAVY, shade=True)
text(s, 7.1, 3.55, 5.4, 0.4, "Perintah yang sering dipakai", size=15, bold=True, color="7FD6DF")
text(s, 7.1, 4.05, 5.4, 2.5, ["docker compose up -d --build", "docker compose exec api python -m app.cli security-check", "docker compose exec api python -m app.cli sync zabbix", "docker compose logs worker --tail 50"], size=13, color="FFFFFF", space=8)

# ---------------------------------------------------------------- 19. Batasan
s = new("Batasan yang perlu diketahui", notes="Disampaikan terbuka agar ekspektasi tepat: ini dampak dari data yang tersedia di sumber, bukan kekurangan antarmuka.")
table(s, M, 1.5, W - 2 * M, [2.8, 5.8, 3.53], ["Area", "Batasan", "Dampak"], [
    ["Panorama via API", "Dynamic report meringkas IP ke blok /24 dan tanpa nama host", "Detail host lebih kasar daripada CSV"],
    ["Panorama, Mei–Juni", "Trafik dan aplikasi belum tercatat di Panorama pada periode itu", "Hanya ancaman dan URL yang terisi"],
    ["WiFi portal", "vSZ hanya menampilkan username bila otentikasi lewat vSZ", "Portal QNAP di luar vSZ tampil belum login"],
    ["WiFi usage", "vSZ tidak memberi data aplikasi atau situs yang diakses", "Dominan = SSID, zone, AP, client"],
    ["Trend Micro", "Bentuk jawaban mengikuti API v3 dan hak role API key", "Tombol Test menampilkan field diterima"],
    ["TLS konektor", "Sertifikat internal membuat verifikasi dimatikan", "Risiko penyadapan di jaringan internal"]], size=13, row_h=0.75)

# ---------------------------------------------------------------- 20. Roadmap
s = new("Langkah berikutnya", notes="Usulan urutan kerja. Item bertanda usulan belum disepakati.")
steps = [("1", "Push dan review", "Push branch devices-map, buka PR ke main, review kode dan migrasi"), ("2", "Persiapan VAPT", "Server produksi, HTTPS, rahasia kuat, security-check bersih, backup"), ("3", "Uji penerimaan", "Operator shift dan koordinator mencoba alur harian dan putus sesi WiFi"),
         ("4", "Go-live bertahap", "Aktifkan role per kelompok, pantau sinkron dan audit log"), ("5", "Usulan lanjutan", "Notifikasi alert XDR critical, kebijakan retensi, akun portal WiFi di sisi QNAP")]
for i, (n, a, b) in enumerate(steps):
    y = 1.5 + i * 1.07
    box(s, M, y, W - 2 * M, 0.92, name="Langkah " + n)
    badge(s, M + 0.25, y + 0.21, n, TEAL if i < 4 else AMBER, size=16)
    text(s, M + 1.0, y + 0.1, 3.2, 0.72, a, size=20, bold=True, color=NAVY, anchor=MSO_ANCHOR.MIDDLE)
    text(s, M + 4.3, y + 0.1, W - 2 * M - 4.5, 0.72, b, size=16, color=INK, anchor=MSO_ANCHOR.MIDDLE)

# ---------------------------------------------------------------- 21. Penutup
s = new(dark=True, notes="Penutup dan tanya jawab.")
text(s, M, 2.5, 11.5, 1.2, "Terima kasih", size=54, bold=True, color="FFFFFF", name="Judul")
text(s, M, 3.8, 11.5, 1.6, ["Dashboard IT Pelindo Multi Terminal", "IT Operation Center · Pelindo Multi Terminal", "Panduan lengkap: docs/Tutorial-Integrasi.md dan docs/Panduan-Keamanan.md"], size=18, color=ICE, space=8)

prs.save(OUT.rstrip("/\\") + "/Paparan-Dashboard-IT-Pelindo-Multi-Terminal.pptx")
print("slides:", state["n"])
