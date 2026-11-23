"""Shared executive DOCX & Pelindo-template PPTX builder library for TERA Dashboard documentation suite."""
from __future__ import annotations
import copy
from pathlib import Path
from lxml import etree

from docx import Document
from docx.shared import Inches as DIn, Pt as DPt, RGBColor as DRGB, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn as dqn

from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.oxml.ns import qn

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_PPTX = ROOT / "backend" / "assets" / "template_pelindo.pptx"
LOGO_LOCKUP = ROOT / "frontend" / "assets" / "tera-lockup-col.png"
LOGO_ICON = ROOT / "frontend" / "assets" / "tera-icon-col.png"
DOCS_DIR = ROOT / "docs"

# Official Pelindo / TERA Palette
NAVY = "0B2F6B"
BLUE = "0B75BB"
CYAN = "25B7E5"
INK = "1F2937"
MUTED = "586879"
LINE = "D9E2EC"
ZEBRA = "F3F6FA"
PALE = "EBF5FC"
AMBER = "D97706"
RED = "D03B3B"
GREEN = "0B7A0B"
WHITE = "FFFFFF"


# =============================================================================
# DOCX BUILDER
# =============================================================================
def _set_cell_bg(cell, hex_color: str):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{hex_color}"/>')
    tcPr.append(shd)


def _set_cell_margins(cell, top=80, bottom=80, left=130, right=130):
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = OxmlElement("w:tcMar")
    for m, val in (("top", top), ("bottom", bottom), ("left", left), ("right", right)):
        node = OxmlElement(f"w:{m}")
        node.set(dqn("w:w"), str(val))
        node.set(dqn("w:type"), "dxa")
        tcMar.append(node)
    tcPr.append(tcMar)


def _set_table_borders(table, color=LINE):
    tblPr = table._tbl.tblPr
    borders = parse_xml(
        f'<w:tblBorders {nsdecls("w")}>'
        f'<w:top w:val="single" w:sz="6" w:space="0" w:color="{NAVY}"/>'
        f'<w:bottom w:val="single" w:sz="6" w:space="0" w:color="{NAVY}"/>'
        f'<w:insideH w:val="single" w:sz="4" w:space="0" w:color="{color}"/>'
        f'<w:left w:val="none"/><w:right w:val="none"/><w:insideV w:val="none"/>'
        f"</w:tblBorders>"
    )
    tblPr.append(borders)


def _add_p_border_bottom(p, color=BLUE, sz="12"):
    pPr = p._p.get_or_add_pPr()
    pBdr = parse_xml(f'<w:pBdr {nsdecls("w")}><w:bottom w:val="single" w:sz="{sz}" w:space="4" w:color="{color}"/></w:pBdr>')
    pPr.append(pBdr)


def _add_page_number(run):
    fld1 = parse_xml(f'<w:fldChar {nsdecls("w")} w:fldCharType="begin"/>')
    instr = parse_xml(f'<w:instrText {nsdecls("w")} xml:space="preserve"> PAGE </w:instrText>')
    fld2 = parse_xml(f'<w:fldChar {nsdecls("w")} w:fldCharType="end"/>')
    run._r.append(fld1)
    run._r.append(instr)
    run._r.append(fld2)


class DocBuilder:
    def __init__(self, doc_type: str, title: str, subtitle: str, doc_code: str, version: str = "2.0", date_str: str = "November 2026"):
        self.doc = Document()
        self.doc_type = doc_type
        self.title = title
        self.subtitle = subtitle
        self.doc_code = doc_code
        self.version = version
        self.date_str = date_str

        sec = self.doc.sections[0]
        sec.page_width = Cm(21.0)
        sec.page_height = Cm(29.7)
        sec.top_margin = Cm(2.0)
        sec.bottom_margin = Cm(2.0)
        sec.left_margin = Cm(2.2)
        sec.right_margin = Cm(2.2)
        sec.different_first_page_header_footer = True

        # Base normal style
        st = self.doc.styles["Normal"]
        st.font.name = "Calibri"
        st.font.size = DPt(10.5)
        st.font.color.rgb = DRGB.from_string(INK)
        st.paragraph_format.space_after = DPt(5)
        st.paragraph_format.line_spacing = 1.18

        # Running header & footer (pages 2+)
        hp = sec.header.paragraphs[0]
        hp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        hr = hp.add_run(f"TERA Dashboard · {doc_type}  |  PT Pelindo Multi Terminal (ITOC)")
        hr.font.name = "Calibri"
        hr.font.size = DPt(8.5)
        hr.font.color.rgb = DRGB.from_string(MUTED)
        _add_p_border_bottom(hp, LINE, "4")

        fp = sec.footer.paragraphs[0]
        fp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        fr1 = fp.add_run(f"{doc_code} · v{version} · {date_str}   |   Halaman ")
        fr1.font.name = "Calibri"
        fr1.font.size = DPt(8.5)
        fr1.font.color.rgb = DRGB.from_string(MUTED)
        fr2 = fp.add_run()
        fr2.font.name = "Calibri"
        fr2.font.size = DPt(8.5)
        fr2.font.color.rgb = DRGB.from_string(NAVY)
        fr2.bold = True
        _add_page_number(fr2)

        self._build_cover()

    def _build_cover(self):
        # Top accent banner
        tbl = self.doc.add_table(rows=1, cols=1)
        tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
        cell = tbl.cell(0, 0)
        _set_cell_bg(cell, NAVY)
        _set_cell_margins(cell, top=120, bottom=120, left=180, right=180)
        p = cell.paragraphs[0]
        p.paragraph_format.space_after = DPt(0)
        r = p.add_run("PT PELINDO MULTI TERMINAL  ·  DIVISI TEKNOLOGI INFORMASI  ·  IT OPERATION CENTER (ITOC)")
        r.font.name = "Calibri"
        r.font.size = DPt(9)
        r.font.bold = True
        r.font.color.rgb = DRGB.from_string(WHITE)

        self.doc.add_paragraph().paragraph_format.space_after = DPt(24)

        if LOGO_LOCKUP.exists():
            lp = self.doc.add_paragraph()
            lp.paragraph_format.space_after = DPt(18)
            lp.add_run().add_picture(str(LOGO_LOCKUP), width=DIn(3.1))

        # Document type pill line
        tp = self.doc.add_paragraph()
        tp.paragraph_format.space_after = DPt(6)
        tr = tp.add_run(self.doc_type.upper())
        tr.font.name = "Calibri"
        tr.font.size = DPt(11.5)
        tr.font.bold = True
        tr.font.color.rgb = DRGB.from_string(BLUE)

        # Main Title
        mp = self.doc.add_paragraph()
        mp.paragraph_format.space_after = DPt(8)
        mr = mp.add_run(self.title)
        mr.font.name = "Calibri"
        mr.font.size = DPt(26)
        mr.font.bold = True
        mr.font.color.rgb = DRGB.from_string(NAVY)

        # Subtitle
        sp = self.doc.add_paragraph()
        sp.paragraph_format.space_after = DPt(16)
        sr = sp.add_run(self.subtitle)
        sr.font.name = "Calibri"
        sr.font.size = DPt(12.5)
        sr.font.color.rgb = DRGB.from_string(MUTED)
        _add_p_border_bottom(sp, CYAN, "18")

        self.doc.add_paragraph().paragraph_format.space_after = DPt(36)

        # Metadata table
        meta = [
            ("Nama Aplikasi", "TERA Dashboard (Telemetry, Evaluation, Reporting & Analytics)"),
            ("Unit Pemilik", "IT Operation Center (ITOC) — Divisi Teknologi Informasi"),
            ("Perusahaan", "PT Pelindo Multi Terminal (Subholding Pelindo)"),
            ("Kode Dokumen", self.doc_code),
            ("Versi / Tanggal", f"Versi {self.version} — {self.date_str}"),
            ("Klasifikasi", "Internal PT Pelindo Multi Terminal"),
        ]
        self.table(["Informasi Dokumen", "Keterangan"], meta, col_widths=[4.8, 11.8])
        self.doc.add_page_break()

    def h1(self, text_str: str):
        p = self.doc.add_paragraph()
        p.paragraph_format.space_before = DPt(14)
        p.paragraph_format.space_after = DPt(6)
        p.paragraph_format.keep_with_next = True
        r = p.add_run(text_str)
        r.font.name = "Calibri"
        r.font.size = DPt(15.5)
        r.font.bold = True
        r.font.color.rgb = DRGB.from_string(NAVY)
        _add_p_border_bottom(p, BLUE, "10")
        return p

    def h2(self, text_str: str):
        p = self.doc.add_paragraph()
        p.paragraph_format.space_before = DPt(10)
        p.paragraph_format.space_after = DPt(4)
        p.paragraph_format.keep_with_next = True
        r = p.add_run(text_str)
        r.font.name = "Calibri"
        r.font.size = DPt(12.5)
        r.font.bold = True
        r.font.color.rgb = DRGB.from_string(BLUE)
        return p

    def h3(self, text_str: str):
        p = self.doc.add_paragraph()
        p.paragraph_format.space_before = DPt(7)
        p.paragraph_format.space_after = DPt(3)
        p.paragraph_format.keep_with_next = True
        r = p.add_run(text_str)
        r.font.name = "Calibri"
        r.font.size = DPt(11)
        r.font.bold = True
        r.font.color.rgb = DRGB.from_string(INK)
        return p

    def p(self, text_str: str, bold_prefix: str = ""):
        par = self.doc.add_paragraph()
        par.paragraph_format.space_after = DPt(5)
        if bold_prefix:
            rb = par.add_run(bold_prefix)
            rb.bold = True
            rb.font.color.rgb = DRGB.from_string(NAVY)
        par.add_run(text_str)
        return par

    def bullets(self, items: list[str | tuple[str, str]]):
        for it in items:
            par = self.doc.add_paragraph(style="List Bullet")
            par.paragraph_format.space_after = DPt(3)
            par.paragraph_format.line_spacing = 1.14
            if isinstance(it, tuple):
                rb = par.add_run(it[0])
                rb.bold = True
                rb.font.color.rgb = DRGB.from_string(NAVY)
                par.add_run(it[1])
            else:
                par.add_run(it)

    def callout(self, title: str, body: str, bg: str = PALE, accent: str = BLUE):
        tbl = self.doc.add_table(rows=1, cols=1)
        tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
        cell = tbl.cell(0, 0)
        _set_cell_bg(cell, bg)
        _set_cell_margins(cell, top=100, bottom=100, left=160, right=140)
        tcPr = cell._tc.get_or_add_tcPr()
        tcPr.append(parse_xml(
            f'<w:tcBorders {nsdecls("w")}>'
            f'<w:left w:val="single" w:sz="24" w:space="0" w:color="{accent}"/>'
            f'<w:top w:val="none"/><w:right w:val="none"/><w:bottom w:val="none"/>'
            f"</w:tcBorders>"
        ))
        p = cell.paragraphs[0]
        p.paragraph_format.space_after = DPt(2)
        rt = p.add_run(title + "\n")
        rt.bold = True
        rt.font.size = DPt(10.5)
        rt.font.color.rgb = DRGB.from_string(NAVY)
        rb = p.add_run(body)
        rb.font.size = DPt(9.8)
        rb.font.color.rgb = DRGB.from_string(INK)
        sp = self.doc.add_paragraph()
        sp.paragraph_format.space_after = DPt(3)

    def code(self, text_str: str):
        tbl = self.doc.add_table(rows=1, cols=1)
        tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
        cell = tbl.cell(0, 0)
        _set_cell_bg(cell, "F1F5F9")
        _set_cell_margins(cell, top=90, bottom=90, left=130, right=130)
        tcPr = cell._tc.get_or_add_tcPr()
        tcPr.append(parse_xml(
            f'<w:tcBorders {nsdecls("w")}>'
            f'<w:top w:val="single" w:sz="4" w:space="0" w:color="{LINE}"/>'
            f'<w:bottom w:val="single" w:sz="4" w:space="0" w:color="{LINE}"/>'
            f'<w:left w:val="single" w:sz="12" w:space="0" w:color="{NAVY}"/>'
            f'<w:right w:val="single" w:sz="4" w:space="0" w:color="{LINE}"/>'
            f"</w:tcBorders>"
        ))
        p = cell.paragraphs[0]
        p.paragraph_format.space_after = DPt(0)
        p.paragraph_format.line_spacing = 1.08
        r = p.add_run(text_str)
        r.font.name = "Consolas"
        r.font.size = DPt(8.8)
        r.font.color.rgb = DRGB.from_string("0F172A")
        sp = self.doc.add_paragraph()
        sp.paragraph_format.space_after = DPt(3)

    def table(self, headers: list[str], rows: list[list | tuple], col_widths: list[float] | None = None):
        tbl = self.doc.add_table(rows=len(rows) + 1, cols=len(headers))
        tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
        _set_table_borders(tbl)
        # Header row
        hdr_cells = tbl.rows[0].cells
        trPr = tbl.rows[0]._tr.get_or_add_trPr()
        trPr.append(parse_xml(f'<w:tblHeader {nsdecls("w")}/>'))
        for i, h in enumerate(headers):
            c = hdr_cells[i]
            _set_cell_bg(c, NAVY)
            _set_cell_margins(c, top=90, bottom=90, left=110, right=110)
            c.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
            p = c.paragraphs[0]
            p.paragraph_format.space_after = DPt(0)
            r = p.add_run(str(h))
            r.bold = True
            r.font.name = "Calibri"
            r.font.size = DPt(9.5)
            r.font.color.rgb = DRGB.from_string(WHITE)
        for ri, row in enumerate(rows):
            trPr = tbl.rows[ri + 1]._tr.get_or_add_trPr()
            trPr.append(parse_xml(f'<w:cantSplit {nsdecls("w")}/>'))
            cells = tbl.rows[ri + 1].cells
            bg = ZEBRA if ri % 2 == 1 else WHITE
            for ci, val in enumerate(row):
                c = cells[ci]
                _set_cell_bg(c, bg)
                _set_cell_margins(c, top=65, bottom=65, left=110, right=110)
                c.vertical_alignment = WD_ALIGN_VERTICAL.TOP
                p = c.paragraphs[0]
                p.paragraph_format.space_after = DPt(0)
                p.paragraph_format.line_spacing = 1.12
                r = p.add_run(str(val))
                r.font.name = "Calibri"
                r.font.size = DPt(9.2)
                if ci == 0:
                    r.bold = True
                    r.font.color.rgb = DRGB.from_string(NAVY)
                else:
                    r.font.color.rgb = DRGB.from_string(INK)
        if col_widths:
            for row in tbl.rows:
                for i, w in enumerate(col_widths):
                    row.cells[i].width = Cm(w)
        sp = self.doc.add_paragraph()
        sp.paragraph_format.space_after = DPt(4)
        return tbl

    def page_break(self):
        self.doc.add_page_break()

    def save(self, path: Path):
        self.doc.save(str(path))


# =============================================================================
# PELINDO-TEMPLATE PPTX BUILDER
# =============================================================================
R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
FONT = "Arial"
S = 1.5
YO = 0.3
W, M = 13.333, 0.55
rgb = lambda h: RGBColor.from_string(h)
I = lambda v: Inches(v * S)
IY = lambda v: Inches((v - YO) * S)
FS = lambda v: Pt(v * S * 0.85)


def _named(slide, key):
    return next((x for x in slide.shapes if f";{key};" in x.name), None)


def _set_runs(par, text_str):
    runs = par.runs
    if runs:
        runs[0].text = text_str
        for r in runs[1:]:
            r._r.getparent().remove(r._r)
    else:
        par.text = text_str


def _set_text(shape, text_str):
    if shape is None:
        return
    tf = shape.text_frame
    _set_runs(tf.paragraphs[0], text_str)
    for p in tf.paragraphs[1:]:
        p._p.getparent().remove(p._p)


def _clone_frame(src, dst):
    for shp in src.shapes:
        if shp._element.tag.endswith("graphicFrame"):
            continue
        el = copy.deepcopy(shp._element)
        for node in el.iter():
            for attr in ("embed", "link", "id"):
                key = f"{{{R_NS}}}{attr}"
                old = node.get(key)
                if old and old in src.part.rels and not src.part.rels[old].is_external:
                    rel = src.part.rels[old]
                    node.set(key, dst.part.relate_to(rel.target_part, rel.reltype))
        dst.shapes._spTree.append(el)


def _shadow(shape, blur=8, dist=2, alpha=14):
    sp = shape._element.spPr
    for e in sp.findall(qn("a:effectLst")):
        sp.remove(e)
    eff = etree.SubElement(sp, qn("a:effectLst"))
    sh = etree.SubElement(eff, qn("a:outerShdw"), blurRad=str(int(blur * 12700)), dist=str(int(dist * 12700)), dir="5400000", algn="t", rotWithShape="0")
    clr = etree.SubElement(sh, qn("a:srgbClr"), val=NAVY)
    etree.SubElement(clr, qn("a:alpha"), val=str(alpha * 1000))


class PelindoDeck:
    def __init__(self, cover_title: str, cover_sub: str):
        self.prs = Presentation(str(TEMPLATE_PPTX))
        self.orig_slides = list(self.prs.slides)
        self.cover = next(x for x in self.orig_slides if _named(x, "166") is not None and _named(x, "167") is not None)
        self.content_src = next((x for x in self.orig_slides[1:] if _named(x, "190") is not None and _named(x, "194") is not None), self.orig_slides[1])
        self.thanks = self.orig_slides[-1]
        self.blank = self.content_src.slide_layout
        _set_text(_named(self.cover, "166"), cover_title)
        _set_text(_named(self.cover, "167"), cover_sub)

    def slide(self, title: str, subtitle: str = ""):
        s = self.prs.slides.add_slide(self.blank)
        _clone_frame(self.content_src, s)
        _set_text(_named(s, "194"), title)
        if subtitle:
            self.text(s, M, 1.32, W - 2 * M, 0.35, subtitle, size=12.5, color=MUTED)
        return s

    def box(self, slide, x, y, w, h, fill=WHITE, line=LINE, radius=0.05, shape=MSO_SHAPE.ROUNDED_RECTANGLE, shade=True):
        sh = slide.shapes.add_shape(shape, I(x), IY(y), I(w), I(h))
        if shape == MSO_SHAPE.ROUNDED_RECTANGLE:
            sh.adjustments[0] = radius
        if fill:
            sh.fill.solid()
            sh.fill.fore_color.rgb = rgb(fill)
        else:
            sh.fill.background()
        if line:
            sh.line.color.rgb = rgb(line)
            sh.line.width = Pt(1)
        else:
            sh.line.fill.background()
        if shade and fill:
            _shadow(sh)
        else:
            sh.shadow.inherit = False
        return sh

    def text(self, slide, x, y, w, h, content, size=13, bold=False, color=INK, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP, space=0, font=FONT):
        t = slide.shapes.add_textbox(I(x), IY(y), I(w), I(h))
        tf = t.text_frame
        tf.word_wrap = True
        tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
        tf.vertical_anchor = anchor
        lines = content if isinstance(content, list) else [content]
        for i, ln in enumerate(lines):
            p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
            p.alignment = align
            if space:
                p.space_after = Pt(space * S)
            runs = ln if isinstance(ln, list) else [(ln, {})]
            for r in runs:
                txt, o = (r if isinstance(r, tuple) else (r, {}))
                run = p.add_run()
                run.text = txt
                f = run.font
                f.name = o.get("font", font)
                f.size = FS(o.get("size", size))
                f.bold = o.get("bold", bold)
                f.color.rgb = rgb(o.get("color", color))
        return t

    def bullets(self, slide, x, y, w, h, items, size=13, color=INK, space=5, bullet_color=BLUE):
        t = slide.shapes.add_textbox(I(x), IY(y), I(w), I(h))
        tf = t.text_frame
        tf.word_wrap = True
        tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
        for i, it in enumerate(items):
            p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
            p.space_after = Pt(space * S)
            pPr = p._p.get_or_add_pPr()
            pPr.set("marL", str(int(0.18 * S * 914400)))
            pPr.set("indent", str(int(-0.18 * S * 914400)))
            bc = etree.SubElement(pPr, qn("a:buClr"))
            etree.SubElement(bc, qn("a:srgbClr"), val=bullet_color)
            etree.SubElement(pPr, qn("a:buFont"), typeface="Arial")
            etree.SubElement(pPr, qn("a:buChar"), char="•")
            if isinstance(it, tuple):
                r1 = p.add_run()
                r1.text = it[0]
                r1.font.name, r1.font.size, r1.font.bold, r1.font.color.rgb = FONT, FS(size), True, rgb(NAVY)
                r2 = p.add_run()
                r2.text = it[1]
                r2.font.name, r2.font.size, r2.font.bold, r2.font.color.rgb = FONT, FS(size), False, rgb(color)
            else:
                r1 = p.add_run()
                r1.text = str(it)
                r1.font.name, r1.font.size, r1.font.bold, r1.font.color.rgb = FONT, FS(size), False, rgb(color)
        return t

    def card(self, slide, x, y, w, h, title, items, accent=BLUE, title_size=14.5, body_size=12, fill=WHITE):
        self.box(slide, x, y, w, h, fill=fill, line=LINE, radius=0.04)
        self.box(slide, x, y, w, 0.08, fill=accent, line=None, shape=MSO_SHAPE.RECTANGLE, shade=False)
        self.text(slide, x + 0.18, y + 0.16, w - 0.36, 0.38, title, size=title_size, bold=True, color=NAVY)
        if isinstance(items, str):
            self.text(slide, x + 0.18, y + 0.56, w - 0.36, h - 0.68, items, size=body_size, color=INK)
        else:
            self.bullets(slide, x + 0.18, y + 0.56, w - 0.36, h - 0.68, items, size=body_size, space=4.5, bullet_color=accent)

    def kpi_strip(self, slide, y, items: list[tuple[str, str, str, str]]):
        """items: list of (value, label, sub, accent_hex)."""
        n = len(items)
        gap = 0.2
        cw = (W - 2 * M - gap * (n - 1)) / n
        for i, (val, lab, sub, acc) in enumerate(items):
            x = M + i * (cw + gap)
            self.box(slide, x, y, cw, 1.25, fill=WHITE, line=LINE, radius=0.06)
            self.box(slide, x, y, 0.09, 1.25, fill=acc, line=None, shape=MSO_SHAPE.RECTANGLE, shade=False)
            self.text(slide, x + 0.2, y + 0.12, cw - 0.3, 0.48, val, size=24, bold=True, color=NAVY)
            self.text(slide, x + 0.2, y + 0.62, cw - 0.3, 0.28, lab, size=11.5, bold=True, color=INK)
            self.text(slide, x + 0.2, y + 0.90, cw - 0.3, 0.26, sub, size=10, color=MUTED)

    def table(self, slide, x, y, w, h, headers, rows, col_ratios=None, font_size=11):
        tbl_shape = slide.shapes.add_table(len(rows) + 1, len(headers), I(x), IY(y), I(w), I(h))
        tbl = tbl_shape.table
        if col_ratios:
            tot = sum(col_ratios)
            for i, r in enumerate(col_ratios):
                tbl.columns[i].width = I(w * r / tot)
        for ci, h_txt in enumerate(headers):
            cell = tbl.cell(0, ci)
            cell.fill.solid()
            cell.fill.fore_color.rgb = rgb(NAVY)
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            p = cell.text_frame.paragraphs[0]
            r = p.add_run()
            r.text = str(h_txt)
            r.font.name, r.font.size, r.font.bold, r.font.color.rgb = FONT, FS(font_size), True, rgb(WHITE)
        for ri, row in enumerate(rows):
            bg = ZEBRA if ri % 2 == 1 else WHITE
            for ci, val in enumerate(row):
                cell = tbl.cell(ri + 1, ci)
                cell.fill.solid()
                cell.fill.fore_color.rgb = rgb(bg)
                cell.vertical_anchor = MSO_ANCHOR.MIDDLE
                p = cell.text_frame.paragraphs[0]
                r = p.add_run()
                r.text = str(val)
                r.font.name, r.font.size, r.font.bold = FONT, FS(font_size - 0.5), (ci == 0)
                r.font.color.rgb = rgb(NAVY if ci == 0 else INK)
        return tbl

    def save(self, path: Path):
        lst = self.prs.slides._sldIdLst
        ids = list(lst)
        n_old = len(self.orig_slides)
        first_id = ids[self.orig_slides.index(self.cover)]
        last_id = ids[n_old - 1]
        for sid in ids[:n_old]:
            if sid is not first_id and sid is not last_id:
                self.prs.part.drop_rel(sid.rId)
        new_ids = ids[n_old:]
        for sid in ids:
            lst.remove(sid)
        for sid in [first_id] + new_ids + [last_id]:
            lst.append(sid)
        for i, sld in enumerate(self.prs.slides, 1):
            for key in ("164", "193", "457"):
                sh = _named(sld, key)
                if sh is None:
                    continue
                _set_text(sh, str(i))
                sh.text_frame.word_wrap = False
                sh.left, sh.width = sh.left - Inches(0.45), sh.width + Inches(0.45)
                for p in sh.text_frame.paragraphs:
                    p.alignment = PP_ALIGN.RIGHT
        self.prs.save(str(path))
        return len(self.prs.slides)
