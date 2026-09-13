from __future__ import annotations

from pathlib import Path
from datetime import date
import hashlib
import json
import re

from PIL import Image, ImageDraw, ImageFont
from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK, WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import nsdecls, qn
from docx.shared import Inches, Pt, RGBColor


ROOT = Path('/Users/thepoolwinpc/Desktop/Qyvox')
OUT_DOCX = ROOT / 'output/docx/Qyvox_Complete_Project_Handbook.docx'
WORK = ROOT / 'tmp/docs/qyvox-handbook'
ASSETS = WORK / 'assets'
LOGO = ROOT / 'frontend/public/brand/qyvox-wordmark-black.png'

PAGE_W_DXA = 12240
PAGE_H_DXA = 15840
CONTENT_W_DXA = 9360
TABLE_INDENT_DXA = 120

INK = '160F14'
NAVY = '26344A'
BLUE = '2E74B5'
DEEP_BLUE = '1F4D78'
ROSE = 'C76F8A'
PALE_ROSE = 'F8E8ED'
IVORY = 'FBF8F5'
LIGHT = 'F3F5F8'
MID = '697386'
GRID = 'CDD4DE'
GREEN = '237A57'
AMBER = '8A6500'
RED = '9B1C1C'
WHITE = 'FFFFFF'


def rgb(hex_value: str) -> RGBColor:
    value = hex_value.lstrip('#')
    return RGBColor(int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16))


def set_cell_shading(cell, fill: str) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = tc_pr.find(qn('w:shd'))
    if shd is None:
        shd = OxmlElement('w:shd')
        tc_pr.append(shd)
    shd.set(qn('w:fill'), fill)


def set_cell_margins(cell, top=80, start=120, bottom=80, end=120) -> None:
    tc = cell._tc
    tc_pr = tc.get_or_add_tcPr()
    tc_mar = tc_pr.first_child_found_in('w:tcMar')
    if tc_mar is None:
        tc_mar = OxmlElement('w:tcMar')
        tc_pr.append(tc_mar)
    for edge, value in [('top', top), ('start', start), ('bottom', bottom), ('end', end)]:
        element = tc_mar.find(qn(f'w:{edge}'))
        if element is None:
            element = OxmlElement(f'w:{edge}')
            tc_mar.append(element)
        element.set(qn('w:w'), str(value))
        element.set(qn('w:type'), 'dxa')


def set_repeat_table_header(row) -> None:
    tr_pr = row._tr.get_or_add_trPr()
    tbl_header = OxmlElement('w:tblHeader')
    tbl_header.set(qn('w:val'), 'true')
    tr_pr.append(tbl_header)


def set_cant_split(row) -> None:
    """Keep each logical data row together when it fits on a fresh page."""
    tr_pr = row._tr.get_or_add_trPr()
    cant_split = OxmlElement('w:cantSplit')
    cant_split.set(qn('w:val'), 'true')
    tr_pr.append(cant_split)


def set_table_borders(table, color=GRID, size='6') -> None:
    tbl_pr = table._tbl.tblPr
    borders = tbl_pr.first_child_found_in('w:tblBorders')
    if borders is None:
        borders = OxmlElement('w:tblBorders')
        tbl_pr.append(borders)
    for edge in ('top', 'left', 'bottom', 'right', 'insideH', 'insideV'):
        tag = borders.find(qn(f'w:{edge}'))
        if tag is None:
            tag = OxmlElement(f'w:{edge}')
            borders.append(tag)
        tag.set(qn('w:val'), 'single')
        tag.set(qn('w:sz'), size)
        tag.set(qn('w:space'), '0')
        tag.set(qn('w:color'), color)


def set_table_geometry(table, widths_dxa: list[int]) -> None:
    assert sum(widths_dxa) == CONTENT_W_DXA, widths_dxa
    table.autofit = False
    table.alignment = WD_TABLE_ALIGNMENT.LEFT
    tbl = table._tbl
    tbl_pr = tbl.tblPr
    tbl_w = tbl_pr.first_child_found_in('w:tblW')
    if tbl_w is None:
        tbl_w = OxmlElement('w:tblW')
        tbl_pr.append(tbl_w)
    tbl_w.set(qn('w:w'), str(CONTENT_W_DXA))
    tbl_w.set(qn('w:type'), 'dxa')
    tbl_ind = tbl_pr.first_child_found_in('w:tblInd')
    if tbl_ind is None:
        tbl_ind = OxmlElement('w:tblInd')
        tbl_pr.append(tbl_ind)
    tbl_ind.set(qn('w:w'), str(TABLE_INDENT_DXA))
    tbl_ind.set(qn('w:type'), 'dxa')
    layout = tbl_pr.first_child_found_in('w:tblLayout')
    if layout is None:
        layout = OxmlElement('w:tblLayout')
        tbl_pr.append(layout)
    layout.set(qn('w:type'), 'fixed')

    grid = tbl.tblGrid
    for child in list(grid):
        grid.remove(child)
    for width in widths_dxa:
        col = OxmlElement('w:gridCol')
        col.set(qn('w:w'), str(width))
        grid.append(col)

    for row in table.rows:
        for index, cell in enumerate(row.cells):
            width = widths_dxa[index]
            tc_pr = cell._tc.get_or_add_tcPr()
            tc_w = tc_pr.first_child_found_in('w:tcW')
            if tc_w is None:
                tc_w = OxmlElement('w:tcW')
                tc_pr.append(tc_w)
            tc_w.set(qn('w:w'), str(width))
            tc_w.set(qn('w:type'), 'dxa')
            cell.width = Inches(width / 1440)
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            set_cell_margins(cell)


def set_run_font(run, name='Calibri', size=11, color=INK, bold=None, italic=None) -> None:
    run.font.name = name
    run._element.get_or_add_rPr().rFonts.set(qn('w:ascii'), name)
    run._element.get_or_add_rPr().rFonts.set(qn('w:hAnsi'), name)
    run.font.size = Pt(size)
    run.font.color.rgb = rgb(color)
    if bold is not None:
        run.bold = bold
    if italic is not None:
        run.italic = italic


def set_keep_with_next(paragraph, value=True) -> None:
    paragraph.paragraph_format.keep_with_next = value


def add_page_number(paragraph) -> None:
    paragraph.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    run = paragraph.add_run('PAGE ')
    set_run_font(run, size=8.5, color=MID, bold=True)
    fld_char1 = OxmlElement('w:fldChar')
    fld_char1.set(qn('w:fldCharType'), 'begin')
    instr = OxmlElement('w:instrText')
    instr.set(qn('xml:space'), 'preserve')
    instr.text = ' PAGE '
    fld_char2 = OxmlElement('w:fldChar')
    fld_char2.set(qn('w:fldCharType'), 'end')
    run._r.append(fld_char1)
    run._r.append(instr)
    run._r.append(fld_char2)


def add_bookmark(paragraph, name: str, bookmark_id: int) -> None:
    start = OxmlElement('w:bookmarkStart')
    start.set(qn('w:id'), str(bookmark_id))
    start.set(qn('w:name'), name)
    end = OxmlElement('w:bookmarkEnd')
    end.set(qn('w:id'), str(bookmark_id))
    paragraph._p.insert(0, start)
    paragraph._p.append(end)


def add_internal_link(paragraph, text: str, anchor: str, color=BLUE, bold=False) -> None:
    hyperlink = OxmlElement('w:hyperlink')
    hyperlink.set(qn('w:anchor'), anchor)
    run = OxmlElement('w:r')
    r_pr = OxmlElement('w:rPr')
    r_fonts = OxmlElement('w:rFonts')
    r_fonts.set(qn('w:ascii'), 'Calibri')
    r_fonts.set(qn('w:hAnsi'), 'Calibri')
    r_pr.append(r_fonts)
    c = OxmlElement('w:color')
    c.set(qn('w:val'), color)
    r_pr.append(c)
    if bold:
        r_pr.append(OxmlElement('w:b'))
    u = OxmlElement('w:u')
    u.set(qn('w:val'), 'none')
    r_pr.append(u)
    run.append(r_pr)
    t = OxmlElement('w:t')
    t.text = text
    run.append(t)
    hyperlink.append(run)
    paragraph._p.append(hyperlink)


def add_alt_text(inline_shape, title: str, description: str) -> None:
    doc_pr = inline_shape._inline.docPr
    doc_pr.set('title', title)
    doc_pr.set('descr', description)


def add_bottom_border(paragraph, color=ROSE, size='16', space='8') -> None:
    p_pr = paragraph._p.get_or_add_pPr()
    p_bdr = p_pr.find(qn('w:pBdr'))
    if p_bdr is None:
        p_bdr = OxmlElement('w:pBdr')
        p_pr.append(p_bdr)
    bottom = OxmlElement('w:bottom')
    bottom.set(qn('w:val'), 'single')
    bottom.set(qn('w:sz'), size)
    bottom.set(qn('w:space'), space)
    bottom.set(qn('w:color'), color)
    p_bdr.append(bottom)


def add_shading(paragraph, fill: str) -> None:
    p_pr = paragraph._p.get_or_add_pPr()
    shd = OxmlElement('w:shd')
    shd.set(qn('w:fill'), fill)
    p_pr.append(shd)


def add_left_border(paragraph, color=ROSE, size='18', space='8') -> None:
    p_pr = paragraph._p.get_or_add_pPr()
    p_bdr = p_pr.find(qn('w:pBdr'))
    if p_bdr is None:
        p_bdr = OxmlElement('w:pBdr')
        p_pr.append(p_bdr)
    left = OxmlElement('w:left')
    left.set(qn('w:val'), 'single')
    left.set(qn('w:sz'), size)
    left.set(qn('w:space'), space)
    left.set(qn('w:color'), color)
    p_bdr.append(left)


def create_numbering(doc: Document) -> tuple[int, int]:
    numbering = doc.part.numbering_part.element
    existing_abs = [int(x.get(qn('w:abstractNumId'))) for x in numbering.findall(qn('w:abstractNum'))]
    existing_num = [int(x.get(qn('w:numId'))) for x in numbering.findall(qn('w:num'))]
    next_abs = max(existing_abs or [0]) + 1
    next_num = max(existing_num or [0]) + 1

    def abstract(abstract_id: int, fmt: str, text: str, font: str | None = None):
        abs_num = OxmlElement('w:abstractNum')
        abs_num.set(qn('w:abstractNumId'), str(abstract_id))
        multi = OxmlElement('w:multiLevelType')
        multi.set(qn('w:val'), 'singleLevel')
        abs_num.append(multi)
        lvl = OxmlElement('w:lvl')
        lvl.set(qn('w:ilvl'), '0')
        start = OxmlElement('w:start')
        start.set(qn('w:val'), '1')
        lvl.append(start)
        num_fmt = OxmlElement('w:numFmt')
        num_fmt.set(qn('w:val'), fmt)
        lvl.append(num_fmt)
        lvl_text = OxmlElement('w:lvlText')
        lvl_text.set(qn('w:val'), text)
        lvl.append(lvl_text)
        suff = OxmlElement('w:suff')
        suff.set(qn('w:val'), 'tab')
        lvl.append(suff)
        p_pr = OxmlElement('w:pPr')
        tabs = OxmlElement('w:tabs')
        tab = OxmlElement('w:tab')
        tab.set(qn('w:val'), 'num')
        tab.set(qn('w:pos'), '540')
        tabs.append(tab)
        p_pr.append(tabs)
        ind = OxmlElement('w:ind')
        ind.set(qn('w:left'), '540')
        ind.set(qn('w:hanging'), '270')
        p_pr.append(ind)
        spacing = OxmlElement('w:spacing')
        spacing.set(qn('w:after'), '80')
        spacing.set(qn('w:line'), '300')
        spacing.set(qn('w:lineRule'), 'auto')
        p_pr.append(spacing)
        lvl.append(p_pr)
        if font:
            r_pr = OxmlElement('w:rPr')
            fonts = OxmlElement('w:rFonts')
            fonts.set(qn('w:ascii'), font)
            fonts.set(qn('w:hAnsi'), font)
            r_pr.append(fonts)
            lvl.append(r_pr)
        abs_num.append(lvl)
        numbering.append(abs_num)

    def num_instance(num_id: int, abstract_id: int):
        num = OxmlElement('w:num')
        num.set(qn('w:numId'), str(num_id))
        abstract_num_id = OxmlElement('w:abstractNumId')
        abstract_num_id.set(qn('w:val'), str(abstract_id))
        num.append(abstract_num_id)
        numbering.append(num)

    abstract(next_abs, 'bullet', '•', 'Calibri')
    num_instance(next_num, next_abs)
    abstract(next_abs + 1, 'decimal', '%1.')
    num_instance(next_num + 1, next_abs + 1)
    return next_num, next_num + 1


def apply_num(paragraph, num_id: int) -> None:
    p_pr = paragraph._p.get_or_add_pPr()
    num_pr = p_pr.find(qn('w:numPr'))
    if num_pr is None:
        num_pr = OxmlElement('w:numPr')
        p_pr.append(num_pr)
    ilvl = OxmlElement('w:ilvl')
    ilvl.set(qn('w:val'), '0')
    num_id_el = OxmlElement('w:numId')
    num_id_el.set(qn('w:val'), str(num_id))
    num_pr.append(ilvl)
    num_pr.append(num_id_el)


def configure_document(doc: Document) -> tuple[int, int]:
    sec = doc.sections[0]
    sec.page_width = Inches(8.5)
    sec.page_height = Inches(11)
    sec.top_margin = Inches(1)
    sec.bottom_margin = Inches(1)
    sec.left_margin = Inches(1)
    sec.right_margin = Inches(1)
    sec.header_distance = Inches(0.492)
    sec.footer_distance = Inches(0.492)
    sec.different_first_page_header_footer = True

    styles = doc.styles
    normal = styles['Normal']
    normal.font.name = 'Calibri'
    normal._element.rPr.rFonts.set(qn('w:ascii'), 'Calibri')
    normal._element.rPr.rFonts.set(qn('w:hAnsi'), 'Calibri')
    normal.font.size = Pt(11)
    normal.font.color.rgb = rgb(INK)
    normal.paragraph_format.space_before = Pt(0)
    normal.paragraph_format.space_after = Pt(5)
    normal.paragraph_format.line_spacing = 1.18

    heading_tokens = {
        'Heading 1': (16, BLUE, 18, 10),
        'Heading 2': (13, BLUE, 14, 7),
        'Heading 3': (12, DEEP_BLUE, 10, 5),
    }
    for name, (size, color, before, after) in heading_tokens.items():
        style = styles[name]
        style.font.name = 'Calibri'
        style._element.rPr.rFonts.set(qn('w:ascii'), 'Calibri')
        style._element.rPr.rFonts.set(qn('w:hAnsi'), 'Calibri')
        style.font.size = Pt(size)
        style.font.bold = True
        style.font.color.rgb = rgb(color)
        style.paragraph_format.space_before = Pt(before)
        style.paragraph_format.space_after = Pt(after)
        style.paragraph_format.keep_with_next = True
        style.paragraph_format.keep_together = True

    for name in ('Title', 'Subtitle'):
        styles[name].font.name = 'Calibri'
        styles[name]._element.rPr.rFonts.set(qn('w:ascii'), 'Calibri')
        styles[name]._element.rPr.rFonts.set(qn('w:hAnsi'), 'Calibri')

    header = sec.header
    hp = header.paragraphs[0]
    hp.clear()
    hp.alignment = WD_ALIGN_PARAGRAPH.LEFT
    r = hp.add_run('QYVOX  /  TECHNICAL & PRODUCT HANDBOOK')
    set_run_font(r, size=8.5, color=MID, bold=True)
    add_bottom_border(hp, color=GRID, size='5', space='4')

    first_header = sec.first_page_header
    first_header.paragraphs[0].clear()

    footer = sec.footer
    fp = footer.paragraphs[0]
    fp.clear()
    add_page_number(fp)
    first_footer = sec.first_page_footer
    ffp = first_footer.paragraphs[0]
    ffp.clear()
    ffp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    rr = ffp.add_run('QYVOX  /  PROVE THE FACT. KEEP THE DATA.')
    set_run_font(rr, size=8.5, color=MID, bold=True)

    doc.core_properties.title = 'Qyvox Complete Technical & Product Handbook'
    doc.core_properties.subject = 'Zero-Knowledge Verifiable Identity Engine'
    doc.core_properties.author = 'Qyvox'
    doc.core_properties.keywords = 'Qyvox, zero knowledge, Groth16, Circom, SnarkJS, FastAPI, Supabase, WebAssembly'
    doc.core_properties.comments = 'Generated from the implementation baseline. No credentials are embedded.'
    return create_numbering(doc)


def p(doc, text: str = '', *, bold_lead: str | None = None, italic=False, color=INK, align=None, after=6, keep=False):
    para = doc.add_paragraph()
    para.paragraph_format.space_after = Pt(after)
    if align is not None:
        para.alignment = align
    if keep:
        para.paragraph_format.keep_together = True
    if bold_lead and text.startswith(bold_lead):
        lead = para.add_run(bold_lead)
        set_run_font(lead, bold=True, color=color)
        rest = para.add_run(text[len(bold_lead):])
        set_run_font(rest, color=color, italic=italic)
    else:
        run = para.add_run(text)
        set_run_font(run, color=color, italic=italic)
    return para


def kicker(doc, text: str, *, color=ROSE, after=6, align=WD_ALIGN_PARAGRAPH.LEFT):
    para = doc.add_paragraph()
    para.alignment = align
    para.paragraph_format.space_after = Pt(after)
    run = para.add_run(text.upper())
    set_run_font(run, name='Arial', size=8.5, color=color, bold=True)
    run.font.all_caps = True
    run.font.letter_spacing = Pt(1.2)
    set_keep_with_next(para)
    return para


def heading(doc, text: str, level=1, anchor: str | None = None, bookmark_id: int | None = None):
    para = doc.add_paragraph(text, style=f'Heading {level}')
    if anchor and bookmark_id is not None:
        add_bookmark(para, anchor, bookmark_id)
    return para


def chapter(doc, number: str, title: str, purpose: str, anchor: str, bookmark_id: int):
    kicker(doc, f'Chapter {number}  /  Qyvox implementation guide')
    h = heading(doc, title, 1, anchor, bookmark_id)
    h.paragraph_format.space_after = Pt(4)
    lead = p(doc, purpose, color=MID, after=14)
    lead.paragraph_format.keep_with_next = True
    rule = doc.add_paragraph()
    rule.paragraph_format.space_after = Pt(12)
    add_bottom_border(rule, color=ROSE, size='14', space='0')


def add_bullets(doc, items: list[str], bullet_num_id: int):
    for item in items:
        para = doc.add_paragraph()
        apply_num(para, bullet_num_id)
        para.paragraph_format.space_after = Pt(3)
        para.paragraph_format.line_spacing = 1.15
        run = para.add_run(item)
        set_run_font(run)


def add_steps(doc, items: list[tuple[str, str]], decimal_num_id: int):
    # Render sequence numbers explicitly. Reusing one Word numbering instance
    # across chapters makes later lists continue at 8, 14, 24, and so on. A local
    # ordinal is stable across Word/LibreOffice and makes every procedure start at 1.
    for index, (label, detail) in enumerate(items, 1):
        para = doc.add_paragraph()
        para.paragraph_format.left_indent = Inches(0.38)
        para.paragraph_format.first_line_indent = Inches(-0.23)
        para.paragraph_format.space_after = Pt(4)
        para.paragraph_format.line_spacing = 1.15
        number = para.add_run(f'{index}.  ')
        set_run_font(number, color=INK)
        run = para.add_run(f'{label}. ')
        set_run_font(run, bold=True, color=DEEP_BLUE)
        run2 = para.add_run(detail)
        set_run_font(run2)


def callout(doc, label: str, text: str, kind='note'):
    fill = {'note': LIGHT, 'privacy': PALE_ROSE, 'warning': 'FFF5D9', 'risk': 'FBEAEA', 'success': 'EAF6F0'}[kind]
    accent = {'note': BLUE, 'privacy': ROSE, 'warning': AMBER, 'risk': RED, 'success': GREEN}[kind]
    para = doc.add_paragraph()
    para.paragraph_format.left_indent = Inches(0.15)
    para.paragraph_format.right_indent = Inches(0.1)
    para.paragraph_format.space_before = Pt(7)
    para.paragraph_format.space_after = Pt(9)
    para.paragraph_format.line_spacing = 1.18
    add_shading(para, fill)
    add_left_border(para, color=accent, size='26', space='6')
    r1 = para.add_run(label.upper() + '  ')
    set_run_font(r1, size=9, color=accent, bold=True)
    r2 = para.add_run(text)
    set_run_font(r2, size=10.2, color=INK)
    para.paragraph_format.keep_together = True
    return para


def code_block(doc, code: str, caption: str | None = None):
    if caption:
        cap = doc.add_paragraph()
        cap.paragraph_format.space_before = Pt(6)
        cap.paragraph_format.space_after = Pt(3)
        run = cap.add_run(caption)
        set_run_font(run, size=8.5, color=MID, bold=True)
        cap.paragraph_format.keep_with_next = True
    para = doc.add_paragraph()
    para.paragraph_format.left_indent = Inches(0.12)
    para.paragraph_format.right_indent = Inches(0.12)
    para.paragraph_format.space_before = Pt(0)
    para.paragraph_format.space_after = Pt(10)
    para.paragraph_format.line_spacing = 1.0
    add_shading(para, INK)
    for index, line in enumerate(code.strip('\n').splitlines()):
        if index:
            para.add_run().add_break()
        run = para.add_run(line if line else ' ')
        set_run_font(run, name='Courier New', size=8.2, color=IVORY)
    para.paragraph_format.keep_together = True
    return para


def table(doc, headers: list[str], rows: list[list[str]], widths: list[int], *, caption: str | None = None, small=False):
    if caption:
        cap = doc.add_paragraph()
        cap.paragraph_format.space_before = Pt(4)
        cap.paragraph_format.space_after = Pt(4)
        cap.paragraph_format.keep_with_next = True
        rr = cap.add_run(caption)
        set_run_font(rr, size=9, color=MID, bold=True)
    t = doc.add_table(rows=1, cols=len(headers))
    set_table_geometry(t, widths)
    set_table_borders(t)
    set_repeat_table_header(t.rows[0])
    set_cant_split(t.rows[0])
    for idx, header in enumerate(headers):
        cell = t.rows[0].cells[idx]
        set_cell_shading(cell, 'E8EEF5')
        para = cell.paragraphs[0]
        para.paragraph_format.space_after = Pt(0)
        para.alignment = WD_ALIGN_PARAGRAPH.LEFT
        run = para.add_run(header)
        set_run_font(run, size=8.5 if small else 9, color=NAVY, bold=True)
    for row_index, row in enumerate(rows):
        cells = t.add_row().cells
        set_cant_split(t.rows[-1])
        if row_index % 2 == 1:
            for cell in cells:
                set_cell_shading(cell, 'F8FAFC')
        for idx, value in enumerate(row):
            para = cells[idx].paragraphs[0]
            para.paragraph_format.space_after = Pt(0)
            para.paragraph_format.line_spacing = 1.05
            run = para.add_run(value)
            set_run_font(run, size=8.5 if small else 9.2, color=INK)
    set_table_geometry(t, widths)
    # Keep short reference tables together. This avoids a lone continuation row
    # followed by a mostly empty page, while longer matrices may still paginate
    # cleanly by complete rows.
    if len(rows) <= 7:
        for table_row in t.rows[:-1]:
            for cell in table_row.cells:
                for para in cell.paragraphs:
                    para.paragraph_format.keep_with_next = True
    after = doc.add_paragraph()
    after.paragraph_format.space_before = Pt(4)
    after.paragraph_format.space_after = Pt(4)
    return t


def part_opener(doc, roman: str, title: str, summary: str, chapters: list[str]):
    spacer = doc.add_paragraph()
    # `page_break_before` starts a divider cleanly without emitting an empty page
    # when the preceding chapter already ended exactly at a page boundary.
    spacer.paragraph_format.page_break_before = True
    spacer.paragraph_format.space_after = Pt(70)
    kicker(doc, f'Part {roman}', align=WD_ALIGN_PARAGRAPH.CENTER, after=16)
    title_p = doc.add_paragraph()
    title_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title_p.paragraph_format.space_after = Pt(14)
    run = title_p.add_run(title)
    set_run_font(run, size=30, color=NAVY, bold=True)
    summary_p = p(doc, summary, color=MID, align=WD_ALIGN_PARAGRAPH.CENTER, after=24)
    summary_p.paragraph_format.left_indent = Inches(0.45)
    summary_p.paragraph_format.right_indent = Inches(0.45)
    rule = doc.add_paragraph()
    add_bottom_border(rule, color=ROSE, size='14', space='0')
    rule.paragraph_format.space_after = Pt(18)
    for index, item in enumerate(chapters, 1):
        item_p = doc.add_paragraph()
        item_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        item_p.paragraph_format.space_after = Pt(5)
        r1 = item_p.add_run(f'{index:02d}  ')
        set_run_font(r1, size=9.5, color=ROSE, bold=True)
        r2 = item_p.add_run(item)
        set_run_font(r2, size=10.5, color=INK)
    # The part opener is a true divider page; the first chapter begins cleanly.
    doc.add_page_break()


def figure(doc, path: Path, title: str, description: str, width=6.25):
    para = doc.add_paragraph()
    para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    para.paragraph_format.space_before = Pt(6)
    para.paragraph_format.space_after = Pt(4)
    shape = para.add_run().add_picture(str(path), width=Inches(width))
    add_alt_text(shape, title, description)
    cap = doc.add_paragraph()
    cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
    cap.paragraph_format.space_after = Pt(10)
    run = cap.add_run(title)
    set_run_font(run, size=8.5, color=MID, bold=True)
    return shape


def pil_font(size: int, bold=False):
    candidates = [
        '/System/Library/Fonts/Supplemental/Arial Bold.ttf' if bold else '/System/Library/Fonts/Supplemental/Arial.ttf',
        '/Library/Fonts/Arial Bold.ttf' if bold else '/Library/Fonts/Arial.ttf',
        '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf' if bold else '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
    ]
    for candidate in candidates:
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, size=size)
    return ImageFont.load_default()


def wrap(draw, text, font, width):
    words = text.split()
    lines, current = [], ''
    for word in words:
        trial = f'{current} {word}'.strip()
        if draw.textbbox((0, 0), trial, font=font)[2] <= width:
            current = trial
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def rounded_box(draw, xy, fill, outline=GRID, radius=24, width=3):
    draw.rounded_rectangle(xy, radius=radius, fill='#' + fill, outline='#' + outline, width=width)


def draw_box_text(draw, xy, eyebrow, title, body, fill='FFFFFF', accent=ROSE):
    x1, y1, x2, y2 = xy
    rounded_box(draw, xy, fill)
    draw.rectangle((x1, y1, x1 + 10, y2), fill='#' + accent)
    draw.text((x1 + 30, y1 + 26), eyebrow.upper(), font=pil_font(20, True), fill='#' + accent)
    draw.text((x1 + 30, y1 + 62), title, font=pil_font(32, True), fill='#' + NAVY)
    y = y1 + 112
    for line in wrap(draw, body, pil_font(22), x2 - x1 - 60):
        draw.text((x1 + 30, y), line, font=pil_font(22), fill='#' + MID)
        y += 30


def arrow(draw, start, end, color=ROSE, width=7):
    draw.line([start, end], fill='#' + color, width=width)
    ex, ey = end
    sx, sy = start
    import math
    angle = math.atan2(ey - sy, ex - sx)
    length = 20
    for delta in (2.55, -2.55):
        px = ex + length * math.cos(angle + delta)
        py = ey + length * math.sin(angle + delta)
        draw.line([(ex, ey), (px, py)], fill='#' + color, width=width)


def make_diagrams():
    ASSETS.mkdir(parents=True, exist_ok=True)

    img = Image.new('RGB', (1800, 980), '#' + IVORY)
    d = ImageDraw.Draw(img)
    d.text((70, 45), 'Qyvox trust-boundary architecture', font=pil_font(46, True), fill='#' + NAVY)
    d.text((70, 105), 'Only the shaded proof envelope crosses from the browser to the server.', font=pil_font(25), fill='#' + MID)
    draw_box_text(d, (70, 210, 545, 530), 'Untrusted input / trusted device boundary', 'Browser prover', 'Birth year exists only as a local witness. Circom WASM constructs a witness and SnarkJS generates a Groth16 proof.', fill='FFF8FA')
    draw_box_text(d, (665, 210, 1135, 530), 'Authenticated service boundary', 'FastAPI verifier', 'Accepts proof and publicSignals only. Enforces schema, policy year, replay check, proof verification, and fail-closed errors.', fill='F7F9FC', accent=BLUE)
    draw_box_text(d, (1255, 210, 1730, 530), 'Persistence boundary', 'Supabase receipt', 'Stores user UUID, UTC timestamp, and SHA-256 proof fingerprint. No birth year, DOB, age, name, address, or document image.', fill='F5FAF7', accent=GREEN)
    arrow(d, (545, 370), (665, 370))
    arrow(d, (1135, 370), (1255, 370), color=GREEN)
    d.rounded_rectangle((475, 600, 1325, 870), radius=26, fill='#' + INK)
    d.text((520, 640), 'NETWORK ENVELOPE', font=pil_font(20, True), fill='#' + ROSE)
    d.text((520, 690), '{ proof, publicSignals }', font=pil_font(38, True), fill='#' + WHITE)
    d.text((520, 755), 'Authorization: Bearer <anonymous session token>', font=pil_font(24), fill='#D6CCD1')
    d.text((520, 810), 'Explicitly absent: birthYear, DOB, age, identity document', font=pil_font(24), fill='#72D6A5')
    img.save(ASSETS / 'architecture.png', quality=95)

    img = Image.new('RGB', (1800, 1100), '#' + IVORY)
    d = ImageDraw.Draw(img)
    d.text((70, 45), 'One verification request: actual execution path', font=pil_font(46, True), fill='#' + NAVY)
    steps = [
        ('01', 'Input', 'A qualifying birth year is entered locally.'),
        ('02', 'Witness', 'WASM maps private and public inputs into circuit signals.'),
        ('03', 'Prove', 'Groth16 fullProve creates proof + public signals.'),
        ('04', 'Purge', 'React state and mutable local reference are cleared.'),
        ('05', 'Authenticate', 'A PII-free Supabase anonymous session token is resolved.'),
        ('06', 'Policy', 'API checks isEligible = 1 and current UTC year.'),
        ('07', 'Replay', 'Canonical payload hash is checked for prior use.'),
        ('08', 'Verify', 'Pinned verification key validates the Groth16 proof.'),
        ('09', 'Commit', 'Minimal receipt is inserted; trace is returned.'),
    ]
    y = 150
    for i, (num, title, body) in enumerate(steps):
        x = 80 if i % 2 == 0 else 930
        draw_box_text(d, (x, y, x + 790, y + 160), num, title, body, fill='FFFFFF', accent=ROSE if i < 5 else BLUE)
        if i % 2 == 1:
            y += 190
    img.save(ASSETS / 'request_lifecycle.png', quality=95)

    img = Image.new('RGB', (1800, 820), '#' + IVORY)
    d = ImageDraw.Draw(img)
    d.text((70, 45), 'Private witness versus public statement', font=pil_font(46, True), fill='#' + NAVY)
    draw_box_text(d, (100, 180, 820, 680), 'Private / never serialized', 'birthYear', 'Used to construct the witness and calculate currentYear - birthYear. It is not listed in component main public signals and it is forbidden by the API schema.', fill='FFF8FA')
    draw_box_text(d, (980, 180, 1700, 680), 'Public / intentionally disclosed', 'isEligible + currentYear', 'The output states that the threshold relation is satisfied. The year binds the proof to the current policy epoch. These two values are visible to the verifier.', fill='F7F9FC', accent=BLUE)
    arrow(d, (820, 430), (980, 430))
    d.text((735, 720), 'PROOF LINKS THE TWO WITHOUT REVEALING THE PRIVATE VALUE', font=pil_font(20, True), fill='#' + MID)
    img.save(ASSETS / 'signal_boundary.png', quality=95)

    img = Image.new('RGB', (1800, 900), '#' + IVORY)
    d = ImageDraw.Draw(img)
    d.text((70, 45), 'From source code to runtime artifacts', font=pil_font(46, True), fill='#' + NAVY)
    nodes = [
        ('Circom source', 'age_check.circom', ROSE),
        ('Constraint system', 'age_check.r1cs', BLUE),
        ('Witness runtime', 'age_check.wasm', BLUE),
        ('Proving key', 'age_check_final.zkey', AMBER),
        ('Verification key', 'verification_key.json', GREEN),
    ]
    x_positions = [70, 410, 750, 1090, 1430]
    for x, (title, file, accent) in zip(x_positions, nodes):
        rounded_box(d, (x, 260, x + 300, 570), 'FFFFFF', accent, 24, 4)
        d.text((x + 25, 300), title, font=pil_font(25, True), fill='#' + NAVY)
        for j, line in enumerate(wrap(d, file, pil_font(21), 250)):
            d.text((x + 25, 370 + j * 30), line, font=pil_font(21), fill='#' + MID)
        if x != x_positions[-1]:
            arrow(d, (x + 300, 415), (x + 340, 415), color=accent, width=5)
    d.rounded_rectangle((300, 650, 1500, 835), radius=24, fill='#' + INK)
    y_text = 684
    for line in wrap(d, 'Development setup is reproducible, but the included one-machine ceremony is not production trust evidence.', pil_font(21, True), 1110):
        d.text((345, y_text), line, font=pil_font(21, True), fill='#' + WHITE)
        y_text += 29
    y_text += 10
    for line in wrap(d, 'Production must publish transcript hashes, independent contributions, checksums, and source binding.', pil_font(20), 1110):
        d.text((345, y_text), line, font=pil_font(20), fill='#D8CDD2')
        y_text += 27
    img.save(ASSETS / 'artifact_pipeline.png', quality=95)


def add_cover(doc: Document):
    spacer = doc.add_paragraph()
    spacer.paragraph_format.space_after = Pt(24)
    if LOGO.exists():
        para = doc.add_paragraph()
        para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        shape = para.add_run().add_picture(str(LOGO), width=Inches(2.8))
        add_alt_text(shape, 'Qyvox wordmark', 'Black Qyvox wordmark on a transparent background.')
        para.paragraph_format.space_after = Pt(80)
    kicker(doc, 'Complete technical & product handbook', align=WD_ALIGN_PARAGRAPH.CENTER, after=20)
    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title.paragraph_format.space_after = Pt(12)
    run = title.add_run('Qyvox')
    set_run_font(run, size=38, color=NAVY, bold=True)
    subtitle = doc.add_paragraph()
    subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
    subtitle.paragraph_format.space_after = Pt(18)
    run = subtitle.add_run('Zero-Knowledge Verifiable Identity Engine')
    set_run_font(run, size=18, color=ROSE, bold=True)
    line = p(doc, 'Prove the fact. Keep the data.', color=INK, align=WD_ALIGN_PARAGRAPH.CENTER, after=18)
    line.runs[0].font.size = Pt(14)
    line.runs[0].italic = True
    rule = doc.add_paragraph()
    add_bottom_border(rule, color=ROSE, size='18', space='0')
    rule.paragraph_format.space_after = Pt(28)
    audience = p(doc, 'A beginner-friendly but implementation-grounded guide for product leaders, investors, engineers, security reviewers, auditors, and enterprise evaluators.', color=MID, align=WD_ALIGN_PARAGRAPH.CENTER, after=54)
    audience.paragraph_format.left_indent = Inches(0.5)
    audience.paragraph_format.right_indent = Inches(0.5)
    meta = doc.add_paragraph()
    meta.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = meta.add_run('IMPLEMENTATION BASELINE  /  27 AUGUST 2026  /  VERSION 1.0')
    set_run_font(r, size=8.5, color=MID, bold=True)


def add_front_matter(doc, bullet_id, decimal_id, chapters):
    doc.add_page_break()
    kicker(doc, 'Document guide')
    heading(doc, 'How to use this handbook', 1, 'how_to_use', 1)
    p(doc, 'This handbook is deliberately written in layers. A reader with no cryptography background can begin with the executive overview and the plain-language primer. A technical reader can move directly to the circuit, API, database, test, and deployment chapters. A security reviewer should concentrate on the trust boundaries, threat model, failure behavior, limitations, and production roadmap.')
    table(doc, ['Reader', 'Recommended path'], [
        ['New to zero knowledge', 'Chapters 1-8, then the glossary and FAQ.'],
        ['Investor or grant reviewer', 'Chapters 1-4, 24-26, 33-35, and the validation snapshot.'],
        ['Frontend engineer', 'Chapters 5-8, 14-16, 22, 28-31.'],
        ['Backend or platform engineer', 'Chapters 5-8, 17-23, 28-32.'],
        ['Cryptography engineer or auditor', 'Chapters 9-13 and 24-27, then source appendices.'],
        ['Enterprise buyer or compliance reviewer', 'Chapters 3-4, 17-27, 33-36, and the FAQ.'],
    ], [2400, 6960], caption='Reading paths by audience')
    callout(doc, 'Baseline versus production', 'Every section distinguishes what exists in the repository today from what Qyvox must add before it should be marketed as an issuer-backed, production identity network.', 'warning')

    heading(doc, 'Document control and accuracy boundary', 2)
    add_bullets(doc, [
        'Source of truth: the Qyvox repository located at the project workspace on 27 August 2026.',
        'Credentials: no Supabase key, bearer token, password, ceremony entropy, or private environment value is reproduced in this document.',
        'Legal posture: privacy and compliance commentary is technical guidance, not legal advice.',
        'Cryptographic posture: Groth16 security is computational and assumption-based; this guide avoids claims of absolute or information-theoretic secrecy.',
        'Benchmark posture: timing results are environment-specific observations, not service-level guarantees or mobile-device claims.',
    ], bullet_id)

    doc.add_page_break()
    kicker(doc, 'Navigation')
    heading(doc, 'Contents', 1, 'contents', 2)
    p(doc, 'The editable Word edition uses real heading styles and internal links. Select any chapter below to jump to it. Page numbering may be refreshed in Microsoft Word after future edits.')
    for part, part_title, entries in chapters:
        para = doc.add_paragraph()
        para.paragraph_format.space_before = Pt(10)
        para.paragraph_format.space_after = Pt(5)
        rr = para.add_run(f'PART {part}  /  {part_title.upper()}')
        set_run_font(rr, size=9.5, color=ROSE, bold=True)
        for num, title, anchor in entries:
            q = doc.add_paragraph()
            q.paragraph_format.left_indent = Inches(0.18)
            q.paragraph_format.space_after = Pt(3)
            r = q.add_run(f'{num}  ')
            set_run_font(r, size=9.5, color=MID, bold=True)
            add_internal_link(q, title, anchor, color=NAVY)

    heading(doc, 'Core promise in one sentence', 2)
    callout(doc, 'Qyvox', 'The browser proves that a private birth-year witness satisfies an 18+ threshold, while the server receives only a Groth16 proof and two public signals and stores only a minimal verification receipt.', 'privacy')


def add_part_one(doc, bullet_id, decimal_id):
    part_opener(doc, 'I', 'Understanding the problem', 'Why privacy-preserving predicates matter, what Qyvox is, and exactly what the current baseline can and cannot claim.', ['Executive overview', 'The identity-data problem', 'What Qyvox proves', 'What Qyvox does not prove'])

    chapter(doc, '01', 'Executive overview', 'A ten-minute orientation to the product, architecture, and honest security boundary.', 'ch01', 101)
    p(doc, 'Qyvox is a zero-knowledge age-eligibility demonstrator. A user enters a birth year into a Next.js interface. The browser constructs a witness and generates a Groth16 proof with WebAssembly and SnarkJS. The birth year is never placed in the application request. FastAPI authenticates the requester, checks the public statement, rejects exact proof replays, verifies the proof against a pinned verification key, and writes a privacy-minimal receipt to Supabase PostgreSQL.')
    p(doc, 'The key product idea is data minimization by architecture. Many businesses need a yes/no policy decision, such as “is this person at least eighteen?”, but collect the underlying personal fact anyway. Qyvox demonstrates how a verifier can receive evidence of a predicate instead of receiving the raw witness. This shifts the server from being a custodian of a sensitive fact to being a verifier of a cryptographic statement.')
    figure(doc, ASSETS / 'architecture.png', 'Figure 1. Qyvox trust-boundary architecture', 'Three-stage architecture diagram. The browser holds the private birth year and sends only a proof envelope to FastAPI. FastAPI verifies and stores only a user UUID, timestamp, and proof fingerprint in Supabase.')
    heading(doc, 'The current implementation at a glance', 2)
    table(doc, ['Layer', 'Technology', 'Responsibility'], [
        ['Circuit', 'Circom 2 + circomlib', 'Constrains 16-bit years and forces currentYear - birthYear to be at least 18.'],
        ['Local prover', 'SnarkJS + WebAssembly', 'Generates Groth16 proof inside the browser from private and public inputs.'],
        ['Web portal', 'Next.js 16 + React 19 + Tailwind CSS 4', 'Explains the system, collects the private witness, displays the execution receipt, and exposes developer material.'],
        ['API', 'FastAPI + Pydantic', 'Authenticates, validates, checks replay, invokes verification, persists a minimal receipt, and returns a trace.'],
        ['Authentication', 'Supabase Auth', 'Creates or restores a PII-free anonymous session and resolves the server-side user UUID.'],
        ['Database', 'Supabase PostgreSQL', 'Stores user_id, verified_at, and proof_hash only; RLS denies browser access.'],
        ['Proof system', 'Groth16 on BN254 / bn128', 'Produces a succinct non-interactive proof with a circuit-specific trusted setup.'],
    ], [1500, 2500, 5360], caption='Qyvox implementation stack', small=True)
    callout(doc, 'Most important qualification', 'The baseline proves knowledge of a qualifying number. It does not prove that the number is true or was issued by a government, bank, school, or other trusted authority.', 'warning')

    chapter(doc, '02', 'The identity-data problem', 'Why conventional verification creates unnecessary custody, correlation, and breach risk.', 'ch02', 102)
    p(doc, 'Traditional age checks often copy more information than the business decision requires. A merchant may need only an eligibility bit but receive a full document image, name, date of birth, address, document number, face image, and metadata. Once copied, those values become assets that must be encrypted, access-controlled, retained, deleted, audited, disclosed after breaches, and protected from insiders and secondary use.')
    p(doc, 'Encryption at rest and in transit are necessary controls, but they do not eliminate collection. Authorized applications and operators must still decrypt data to use it. Backups, exports, support systems, analytics pipelines, logs, and incident tooling can widen the exposure surface. Data minimization asks a more fundamental question: can the system make the decision without taking custody of the sensitive fact at all?')
    table(doc, ['Conventional model', 'Qyvox baseline'], [
        ['Server receives a birth year or document.', 'Server receives proof and public signals only.'],
        ['Database may become a demographic honeypot.', 'Receipt table has no DOB, age, name, address, or image field.'],
        ['Operational staff may access raw identity data.', 'Routine verification path has no raw witness to retrieve.'],
        ['Breach can expose reusable identity facts.', 'Breach exposes verification receipts and account identifiers, which remain sensitive but are materially narrower.'],
        ['Policy logic is evaluated on disclosed data.', 'Policy logic is compiled into constraints and proved locally.'],
    ], [4680, 4680], caption='Data-custody comparison')
    heading(doc, 'What data minimization changes', 2)
    add_bullets(doc, [
        'Collection risk falls because the application request has no raw birth year field.',
        'Retention scope narrows because the database schema cannot store the omitted field without an explicit migration.',
        'Secondary-use opportunities shrink because there is no raw age attribute in the receipt table.',
        'Incident impact can be reduced, although account UUIDs, timestamps, and proof fingerprints still require protection.',
        'Compliance work may become simpler, but lawful basis, notices, access rights, retention rules, and sector obligations still apply.',
    ], bullet_id)
    callout(doc, 'Principle', 'The safest sensitive datum is often the datum the server never receives.', 'privacy')

    chapter(doc, '03', 'What Qyvox proves', 'The exact statement, public disclosure, and decision that a valid proof supports.', 'ch03', 103)
    p(doc, 'A valid baseline proof supports this statement: “I know a 16-bit integer birthYear such that currentYear - birthYear is at least 18, and the public currentYear is the value included in this proof.” The circuit additionally forces the public output isEligible to equal one. The API accepts only that eligible branch and independently requires currentYear to match the server’s current UTC year.')
    figure(doc, ASSETS / 'signal_boundary.png', 'Figure 2. Private witness and public statement', 'Diagram dividing the private birthYear witness from the public isEligible and currentYear signals. The proof links the two without serializing the private value.')
    heading(doc, 'Meaning of each value', 2)
    table(doc, ['Signal or artifact', 'Visibility', 'Meaning'], [
        ['birthYear', 'Private witness', 'The integer used locally to satisfy the age constraint. It is not serialized into the request.'],
        ['currentYear', 'Public input', 'The policy epoch. The server requires it to equal its UTC year.'],
        ['isEligible', 'Public output', 'Must be exactly 1; the circuit cannot produce an accepted underage branch.'],
        ['proof', 'Public cryptographic artifact', 'Elliptic-curve points that a verifier checks against the public signals and verification key.'],
        ['verification receipt', 'Persistent server record', 'Authenticated user UUID, verification time, and exact-proof fingerprint.'],
    ], [2000, 1750, 5610], caption='Signal and artifact dictionary')
    p(doc, 'The proof is non-interactive: after it is generated, the verifier does not need to question the prover in multiple rounds. It is succinct: the proof object is much smaller than the witness or a general execution trace. It is zero knowledge under the scheme’s assumptions: the proof is designed not to disclose the private witness beyond what can be inferred from the public statement.')
    callout(doc, 'What is intentionally revealed', 'The verifier learns that the threshold statement is true for the disclosed policy year. Zero knowledge does not mean “the verifier learns nothing”; it means the verifier learns no additional witness information beyond the public statement under the stated assumptions.', 'note')

    chapter(doc, '04', 'What Qyvox does not prove', 'The limitations that must remain visible in product, security, and sales conversations.', 'ch04', 104)
    p(doc, 'The current circuit accepts any qualifying integer supplied by the user. It has no issuer signature, credential commitment, document authenticity check, biometric binding, revocation registry, or hardware-backed key. Therefore, it proves knowledge of a satisfying witness, not the truth or provenance of that witness. A user can type a false year and, if it satisfies the relation, generate a mathematically valid proof.')
    p(doc, 'The arithmetic is year-granular. Someone born late in a year is treated the same as someone born early in that year. Exact legal-age rules generally require month/day logic, jurisdiction-specific definitions, leap-year handling, and sometimes time-zone policy. Those are not modeled by this baseline.')
    heading(doc, 'Current boundaries', 2)
    add_bullets(doc, [
        'No trusted issuer: the witness is self-asserted.',
        'No exact date: eligibility uses calendar-year subtraction.',
        'No cryptographic challenge binding: exact replay is blocked by storage, but a next-generation circuit should bind a server nonce, session commitment, and expiry.',
        'Development-only ceremony: setup.sh performs a one-machine ceremony and is not production trust evidence.',
        'No formal secure-memory erasure: JavaScript state and references are cleared promptly, but managed runtimes do not guarantee physical zeroization.',
        'No universal compliance guarantee: deployment obligations remain contextual.',
        'No blockchain requirement or ledger-based consensus: verification runs on ordinary web infrastructure.',
    ], bullet_id)
    table(doc, ['Claim', 'Safe wording', 'Unsafe wording'], [
        ['Witness privacy', 'Recovering the witness should be computationally infeasible under Groth16 assumptions.', 'It is mathematically impossible to recover any information.'],
        ['Identity truth', 'The baseline proves knowledge of a qualifying value.', 'Qyvox proves the user’s real government-certified age.'],
        ['Replay', 'Exact proof reuse is rejected; challenge binding is planned.', 'The current circuit is fully replay and front-running resistant.'],
        ['Compliance', 'Data minimization can reduce exposure.', 'The architecture automatically guarantees GDPR/KYC/AML compliance.'],
        ['Performance', 'Measured on a stated machine and sample size.', 'Always verifies in under 10 ms everywhere.'],
    ], [1600, 3600, 4160], caption='Security-claim language guide', small=True)


def add_part_two(doc, bullet_id, decimal_id):
    part_opener(doc, 'II', 'Zero knowledge from first principles', 'A plain-language path from statements and witnesses to arithmetic circuits, R1CS, elliptic curves, Groth16, and trusted setup.', ['Mental model', 'Arithmetic circuits and R1CS', 'Groth16 lifecycle', 'Trusted setup and assumptions'])

    chapter(doc, '05', 'A zero-knowledge mental model', 'The vocabulary a first-time reader needs before looking at code.', 'ch05', 105)
    p(doc, 'Imagine a locked rulebook that says which secret inputs are acceptable. A prover wants to convince a verifier that one acceptable input exists and that the prover knows it, without opening the secret page. The prover runs a cryptographic algorithm using the secret witness and public statement. The verifier checks the resulting proof using public verification material.')
    table(doc, ['Term', 'Plain-language meaning', 'Qyvox example'], [
        ['Statement', 'The claim the verifier is willing to accept.', 'Eligibility is true for the current year.'],
        ['Witness', 'Private values that make the statement true.', 'birthYear.'],
        ['Circuit', 'A fixed set of mathematical relations that defines valid witnesses.', 'Range checks plus currentYear - birthYear >= 18.'],
        ['Prover', 'Algorithm that uses the witness to create a proof.', 'SnarkJS groth16.fullProve in the browser.'],
        ['Proof', 'Succinct public evidence checked without seeing the witness.', 'The pi_a, pi_b, pi_c Groth16 object.'],
        ['Verifier', 'Algorithm that checks proof + public inputs.', 'SnarkJS groth16.verify launched by FastAPI.'],
        ['Verification key', 'Public material tied to a particular circuit setup.', 'backend/zk/verification_key.json.'],
    ], [1500, 3820, 4040], caption='Zero-knowledge vocabulary', small=True)
    heading(doc, 'Three security properties', 2)
    add_bullets(doc, [
        'Completeness: an honest prover with a valid witness should be able to produce a proof the verifier accepts.',
        'Soundness or knowledge soundness: a prover should not be able to convince the verifier without a witness that satisfies the circuit, except with negligible probability under the scheme’s assumptions.',
        'Zero knowledge: the proof should reveal no useful information about the private witness beyond the public statement, under the scheme’s assumptions and correct implementation.',
    ], bullet_id)
    callout(doc, 'Important distinction', 'A circuit can be cryptographically sound and still encode the wrong business rule. Circuit review must check both mathematics and policy semantics.', 'warning')

    chapter(doc, '06', 'Arithmetic circuits and R1CS', 'How a business rule becomes field equations that a proving system can enforce.', 'ch06', 106)
    p(doc, 'Circom programs do not execute like ordinary JavaScript. They describe constraints over a finite field. The compiler turns signals and component relations into a Rank-1 Constraint System (R1CS). Each constraint has the conceptual form ⟨A,w⟩ × ⟨B,w⟩ = ⟨C,w⟩, where w is the full assignment of constants, public signals, private signals, and intermediate values.')
    p(doc, 'A witness calculator evaluates the circuit for a particular input and produces candidate signal values. A valid witness must satisfy every R1CS equation. The proving algorithm then creates an argument that those equations are satisfied without disclosing the private components of w.')
    heading(doc, 'Why comparisons need special gadgets', 2)
    p(doc, 'Finite fields do not have an intrinsic “greater than” operator. Comparisons are implemented by constraining bit decompositions and arithmetic relations. Qyvox uses circomlib’s Num2Bits and GreaterEqThan components with a 16-bit width. The explicit bit range is security-relevant: without it, finite-field subtraction can wrap and a future birth year might be represented as a large field element that appears to exceed eighteen.')
    table(doc, ['Circuit concern', 'Control in Qyvox'], [
        ['Year range', 'Num2Bits(16) constrains both birthYear and currentYear.'],
        ['Future-year wraparound', 'The private difference is also decomposed to 16 bits, so negative field representations cannot masquerade as a small valid age.'],
        ['Threshold', 'GreaterEqThan(16) compares the constrained difference against 18.'],
        ['Eligible output', 'isEligible is connected to the comparator output and constrained to equal 1.'],
        ['Public binding', 'currentYear is declared public; output isEligible is public by Circom convention.'],
    ], [2600, 6760], caption='Circuit-safety controls')
    callout(doc, 'R1CS lesson', '“Calculated” is not the same as “constrained.” Every security-relevant relationship must be enforced by constraints, not merely assigned in witness-generation code.', 'risk')

    chapter(doc, '07', 'Groth16 lifecycle', 'What the proving key, verification key, proof points, and pairing check do at a conceptual level.', 'ch07', 107)
    p(doc, 'Groth16 is a succinct non-interactive argument system for arithmetic circuits. During setup, circuit constraints are transformed into structured public parameters. The proving key is used with a full witness to create proof elements. The verification key is used with public signals to evaluate pairing-based equations on the BN254 curve. A successful pairing equation convinces the verifier that a satisfying witness exists, subject to the setup and cryptographic assumptions.')
    add_steps(doc, [
        ('Compile', 'Circom produces R1CS, a WebAssembly witness generator, and a symbol map.'),
        ('Prepare', 'A Powers of Tau transcript provides universal structured randomness sized above the circuit’s constraint count.'),
        ('Specialize', 'Groth16 setup binds parameters to the exact age_check R1CS.'),
        ('Contribute', 'Additional circuit-specific entropy is mixed into the zkey.'),
        ('Export', 'The verification key is derived from the final zkey.'),
        ('Prove', 'The browser combines the private witness, public input, WASM calculator, and proving key.'),
        ('Verify', 'The server checks proof, public signals, and verification key.'),
    ], decimal_id)
    p(doc, 'The proof object serialized by SnarkJS contains three groups of elliptic-curve coordinates: pi_a, pi_b, and pi_c, plus protocol and curve labels. The API validates the JSON shape and decimal-scalar syntax before invoking the cryptographic verifier. Shape validation is not proof validation; it merely prevents malformed or unbounded inputs from reaching deeper layers.')
    callout(doc, 'Curve naming', 'The repository and SnarkJS use bn128; the handbook also refers to BN254. These names commonly refer to the same pairing-friendly curve family in this tooling context.', 'note')

    chapter(doc, '08', 'Trusted setup and security assumptions', 'Why the ceremony matters and how to describe it without either panic or hand-waving.', 'ch08', 108)
    p(doc, 'Groth16 requires a circuit-specific structured reference string. Setup participants temporarily know secret randomness sometimes described as toxic waste. If every participant colludes and retains enough secret material, soundness can be compromised. A multi-party computation ceremony mitigates this: security holds if at least one contributor generates its randomness honestly and destroys it.')
    figure(doc, ASSETS / 'artifact_pipeline.png', 'Figure 3. Circuit source and artifact pipeline', 'Pipeline diagram from Circom source to R1CS, WASM, proving key, and verification key, with a warning that the included setup ceremony is development-only.', width=5.6)
    heading(doc, 'What setup.sh actually does', 2)
    add_bullets(doc, [
        'Enables strict shell error handling and a restrictive umask.',
        'Checks that Circom, OpenSSL, and the pinned SnarkJS executable are available.',
        'Compiles age_check.circom to R1CS, WASM, and symbol outputs.',
        'Creates a bn128 Powers of Tau transcript at power 12, sufficient for up to 2^12 constraints.',
        'Adds local random entropy, prepares phase two, performs circuit-specific Groth16 setup, and contributes again.',
        'Verifies the final zkey, exports the verification key, and copies runtime artifacts to frontend/public/zk and backend/zk.',
    ], bullet_id)
    heading(doc, 'Production ceremony requirements', 2)
    add_bullets(doc, [
        'Use an independently reviewed public Powers of Tau transcript.',
        'Publish the exact R1CS hash and source revision before contributions begin.',
        'Accept independent contributors using separated machines and documented procedures.',
        'Publish contribution hashes, verification logs, software versions, and final artifact checksums.',
        'Apply a public random beacon when appropriate and record the derivation.',
        'Have external cryptography reviewers verify that deployed artifacts match the published ceremony outputs.',
    ], bullet_id)
    callout(doc, 'Current status', 'The one-machine setup script is valuable for development reproducibility. It must never be represented as proof that production toxic waste was independently destroyed.', 'warning')


def add_part_three(doc, bullet_id, decimal_id):
    part_opener(doc, 'III', 'The Qyvox circuit', 'A line-by-line explanation of signals, range constraints, comparison logic, public ordering, artifacts, and negative tests.', ['Circuit specification', 'Line-by-line walkthrough', 'Boundary conditions and tests', 'Artifacts and version binding'])

    chapter(doc, '09', 'Circuit specification', 'The formal inputs, outputs, invariant, and public signal ordering of age_check.circom.', 'ch09', 109)
    code = """pragma circom 2.0.0;

include "circomlib/circuits/comparators.circom";
include "circomlib/circuits/bitify.circom";

template AgeCheck(nBits) {
    signal input birthYear;
    signal input currentYear;
    signal output isEligible;
    signal ageInYears;

    component birthYearBits = Num2Bits(nBits);
    component currentYearBits = Num2Bits(nBits);
    component ageBits = Num2Bits(nBits);
    component ageThreshold = GreaterEqThan(nBits);

    birthYearBits.in <== birthYear;
    currentYearBits.in <== currentYear;
    ageInYears <== currentYear - birthYear;
    ageBits.in <== ageInYears;
    ageThreshold.in[0] <== ageInYears;
    ageThreshold.in[1] <== 18;
    isEligible <== ageThreshold.out;
    isEligible === 1;
}

component main { public [currentYear] } = AgeCheck(16);"""
    code_block(doc, code, 'Simplified complete circuit listing')
    table(doc, ['Property', 'Value'], [
        ['Private input', 'birthYear'],
        ['Explicit public input', 'currentYear'],
        ['Public output', 'isEligible'],
        ['Threshold', '18 calendar years'],
        ['Bit width', '16'],
        ['Field / curve environment', 'BN254 / bn128 through SnarkJS Groth16'],
        ['Observed compiled size', '74 constraints and 72 wires'],
        ['Public signal order', '[isEligible, currentYear]'],
    ], [2400, 6960], caption='Age-check circuit contract')
    callout(doc, 'Public-output ordering', 'Circom exposes output signals before explicitly public input signals. The API therefore interprets publicSignals[0] as isEligible and publicSignals[1] as currentYear.', 'note')

    chapter(doc, '10', 'Line-by-line circuit walkthrough', 'Why each component exists and what can go wrong if it is removed.', 'ch10', 110)
    heading(doc, 'Pragma and imports', 2)
    p(doc, 'The pragma requires the Circom 2 language family. comparators.circom provides GreaterEqThan; bitify.circom provides Num2Bits. Imports are resolved from the pinned circomlib 2.0.5 dependency. Pinning avoids silently changing constraint implementations when dependencies update.')
    heading(doc, 'Signals and data flow', 2)
    p(doc, 'birthYear and currentYear are inputs to the template. Privacy is determined at the main component declaration, not by the word “private” attached to a signal. currentYear is explicitly listed as public; birthYear is omitted and therefore remains private. isEligible is a signal output and becomes public. ageInYears is an internal witness signal.')
    heading(doc, 'Range constraints', 2)
    p(doc, 'Num2Bits(16) constrains a value to a 16-bit non-negative integer representation. Qyvox applies this to both years and to their difference. This is not cosmetic input validation. It turns the application’s integer assumptions into circuit-enforced facts and closes a finite-field wraparound avenue.')
    heading(doc, 'Comparison and forced outcome', 2)
    p(doc, 'GreaterEqThan(16) receives ageInYears and the constant 18. Its output is one when the first is at least the second. The assignment isEligible <== ageThreshold.out constrains the output to the comparator result. The final equality isEligible === 1 ensures that only an eligible witness can satisfy the circuit. Without the final equality, the circuit could prove either branch and ask the server to interpret the output; Qyvox intentionally makes ineligibility unsatisfiable.')
    callout(doc, 'Review question', 'Can every security-relevant signal float freely? For each value, trace both its witness assignment and the constraints that force it to be correct.', 'risk')

    chapter(doc, '11', 'Boundary conditions and negative tests', 'How the repository demonstrates behavior at the threshold and under adversarial inputs.', 'ch11', 111)
    table(doc, ['Case', 'Input', 'Expected result', 'Reason'], [
        ['Clearly eligible', '2000 / 2026', 'Proof valid; signals [1, 2026]', 'Age difference is 26.'],
        ['Exact boundary', '2008 / 2026', 'Proof valid', 'Difference is exactly 18.'],
        ['Underage', '2010 / 2026', 'Witness/proof generation rejects', 'Difference is 16; isEligible cannot equal 1.'],
        ['Future year', '2027 / 2026', 'Rejects', 'Negative difference cannot fit the constrained 16-bit range.'],
        ['Out-of-range public year', '65517 / 65536', 'Rejects', '65536 does not fit in 16 bits.'],
        ['Tampered public signal', 'Valid proof, year changed to 2027', 'Verification false', 'Proof is cryptographically bound to the original public signal.'],
    ], [1500, 1700, 2500, 3660], caption='Circuit smoke-test matrix', small=True)
    p(doc, 'The smoke test also invokes the exact backend/verify.mjs helper used by FastAPI, providing an integration bridge between circuit artifacts and the server verifier. The test terminates Node explicitly because SnarkJS worker handles can otherwise keep the event loop alive after assertions complete.')
    heading(doc, 'Additional tests recommended before production', 2)
    add_bullets(doc, [
        'Property-based generation across all relevant year boundaries.',
        'Differential tests against an independent reference implementation of the policy.',
        'Mutation tests that remove or weaken one constraint at a time and require tests to fail.',
        'Independent R1CS inspection and unconstrained-signal analysis.',
        'Fuzzing of public signal order, scalar encodings, and verifier input parsing.',
        'Cross-browser proof generation on low-memory mobile devices.',
    ], bullet_id)

    chapter(doc, '12', 'Artifacts and version binding', 'How source, R1CS, WASM, proving key, and verification key must remain one coherent release.', 'ch12', 112)
    p(doc, 'A proof generated from one circuit setup cannot be treated as interchangeable with another. The R1CS defines the relation. The WASM constructs a witness for that relation. The proving key is circuit-specific. The verification key is derived from the same final setup. Deploying a mismatched combination results in failure—or, worse, in confusing provenance if releases are not labeled.')
    table(doc, ['Artifact', 'Consumer', 'Repository location', 'Release control'], [
        ['age_check.circom', 'Circuit compiler and reviewers', 'circuits/age_check.circom', 'Source commit and code review.'],
        ['age_check.r1cs', 'Setup and auditors', 'circuits/build', 'Publish hash and circuit statistics.'],
        ['age_check.wasm', 'Browser prover', 'frontend/public/zk', 'Immutable asset hash and cache policy.'],
        ['age_check_final.zkey', 'Browser prover', 'frontend/public/zk', 'Ceremony transcript binding and checksum.'],
        ['verification_key.json', 'Backend verifier', 'backend/zk', 'Pinned image/release hash.'],
        ['age_check.sym', 'Developers and auditors', 'circuits/build', 'Debug-only mapping; publish with audit bundle.'],
    ], [1900, 1900, 2800, 2760], caption='Cryptographic artifact inventory', small=True)
    heading(doc, 'Recommended release manifest', 2)
    code_block(doc, """{
  "circuit": "age_check",
  "version": "1.0.0",
  "source_commit": "<git commit>",
  "r1cs_sha256": "<64 hex characters>",
  "wasm_sha256": "<64 hex characters>",
  "zkey_sha256": "<64 hex characters>",
  "verification_key_sha256": "<64 hex characters>",
  "public_signals": ["isEligible", "currentYear"],
  "ceremony_transcript": "<public URL and digest>"
}""", 'Illustrative release-manifest shape')
    callout(doc, 'Deployment invariant', 'The frontend artifacts and backend verification key must be released atomically from the same verified manifest.', 'warning')


def add_part_four(doc, bullet_id, decimal_id):
    part_opener(doc, 'IV', 'Browser proving and user experience', 'How the Next.js application constructs the proof locally, clears private state, authenticates without identity fields, and exposes real execution evidence.', ['Frontend architecture', 'Private input lifecycle', 'Proof generation', 'Execution receipt and developer playground'])

    chapter(doc, '13', 'Frontend architecture', 'The routes, components, libraries, assets, and rendering choices that make up the Qyvox portal.', 'ch13', 113)
    table(doc, ['Path', 'Role'], [
        ['frontend/app/page.tsx', 'Executive landing page and live proof demo placement.'],
        ['frontend/app/whitepaper/page.tsx', 'Technical narrative, primitives, trust model, and security bounds.'],
        ['frontend/app/docs/page.tsx', 'Quickstart, architecture, circuit, SDK patterns, API, schema, and playground.'],
        ['frontend/app/research/page.tsx', 'Benchmark results, methodology boundaries, and validation roadmap.'],
        ['frontend/app/faq/page.tsx', 'Enterprise due-diligence questions and bounded answers.'],
        ['frontend/components/ProofDemo.tsx', 'Private input form, proof lifecycle, execution receipt, and exact payload inspector.'],
        ['frontend/lib/zkProver.ts', 'Dynamic SnarkJS import and browser-only fullProve wrapper.'],
        ['frontend/lib/verifyProof.ts', 'Anonymous session resolution and proof-only API request.'],
        ['frontend/lib/supabaseClient.ts', 'Lazy browser client and anonymous authentication.'],
        ['frontend/public/zk/*', 'Public WASM and proving key consumed by the browser.'],
    ], [3200, 6160], caption='Frontend source map', small=True)
    p(doc, 'The App Router statically prerenders the marketing and technical pages. The proof component is explicitly a client component because it depends on browser state, performance timing, WebAssembly, and dynamic SnarkJS loading. Dynamic import prevents proof code from being executed during server-side rendering.')
    heading(doc, 'Design system', 2)
    p(doc, 'The portal uses a dark ink, ivory, and restrained rose palette; Space Grotesk for display and interface text; and IBM Plex Mono for technical labels. The interface uses responsive grid layouts, smooth but bounded motion, reduced-motion handling, minimum interactive target sizes, semantic landmarks, live regions for proof status, and overflow protections for narrow screens.')
    callout(doc, 'Product principle', 'The interface should make the privacy boundary observable: show what stayed local, what crossed the network, what the verifier did, and what was stored.', 'privacy')

    # Start the lifecycle chapter on a clean page. Without this explicit boundary,
    # LibreOffice can pull the heading above the printable frame after the preceding
    # source-map table and callout have been kept together.
    doc.add_page_break()
    chapter(doc, '14', 'Private input lifecycle', 'Every place the birth year exists, and the controls that limit its lifetime.', 'ch14', 114)
    add_steps(doc, [
        ('Form state', 'The value begins as a string in React state bound to the numeric input.'),
        ('Validation copy', 'Submit converts the string to a local number and checks integer/range/eligibility conditions.'),
        ('Proof input', 'generateAgeProof receives birthYear and currentYear and converts them to decimal strings for SnarkJS.'),
        ('Witness calculation', 'The WASM calculator uses the birth year inside browser memory.'),
        ('Proof completion', 'After fullProve returns, the component clears React state and sets the mutable local variable to zero before authentication or fetch.'),
        ('Final cleanup', 'The finally branch zeroes the local variable and clears state again on both success and error paths.'),
    ], decimal_id)
    p(doc, 'The outgoing JSON is constructed from the ProofBundle only. verifyProof serializes exactly two top-level keys: proof and publicSignals. TypeScript interfaces document the fixed proof shape. The backend separately rejects unknown top-level fields, so a body containing birthYear fails validation even if a caller bypasses the official frontend.')
    heading(doc, 'What “cleared” means in JavaScript', 2)
    p(doc, 'Clearing state and overwriting a reference shortens the value’s reachable lifetime. It does not provide certified physical memory erasure. Garbage collectors, copies made by browser internals, swap, crash reports, malicious extensions, compromised scripts, screen recording, and operating-system memory inspection remain outside the guarantee. A production privacy statement should say that the application promptly removes references and never serializes the value, not that every physical byte is provably zeroized.')
    callout(doc, 'Browser threat boundary', 'Zero knowledge protects the witness from the verifier. It does not protect a user whose browser, device, supply chain, or loaded JavaScript is already compromised.', 'risk')

    # Keep this code-heavy chapter away from a page-top collision in LibreOffice's
    # paginator when the preceding risk callout exactly fills the prior page.
    doc.add_page_break()
    chapter(doc, '15', 'Proof generation in the browser', 'How zkProver.ts loads artifacts, runs fullProve, and validates the public statement before transport.', 'ch15', 115)
    code_block(doc, """const snarkjs = await import("snarkjs");
const result = await snarkjs.groth16.fullProve(
  {
    birthYear: birthYear.toString(10),
    currentYear: currentYear.toString(10),
  },
  "/zk/age_check.wasm",
  "/zk/age_check_final.zkey",
);

if (
  result.publicSignals.length !== 2 ||
  result.publicSignals[0] !== "1" ||
  result.publicSignals[1] !== currentYear.toString(10)
) throw new Error("Unexpected public statement");""", 'Browser prover control flow (abridged)')
    p(doc, 'The function refuses to run during server rendering and requires safe integers. Decimal strings prevent accidental floating-point notation. After proving, it normalizes public signals to strings and applies a client-side defense-in-depth check. The server repeats the policy check; client validation is never treated as authoritative.')
    heading(doc, 'Public artifact delivery', 2)
    add_bullets(doc, [
        'WASM and zkey are public cryptographic artifacts, not secrets.',
        'They should be served with immutable versioned URLs or content hashes in production.',
        'Subresource integrity, a strict Content Security Policy, dependency pinning, and build provenance reduce supply-chain risk.',
        'Larger future circuits should move proving to a Web Worker to keep the interface responsive.',
        'Cold-download, cache-hit, memory, and thermal behavior must be measured separately on mobile devices.',
    ], bullet_id)
    callout(doc, 'Do not confuse public with unimportant', 'The proving key is intentionally public, but an attacker who replaces it or the WASM can alter availability or trick the user interface. Artifact integrity still matters.', 'warning')

    chapter(doc, '16', 'Execution receipt and developer playground', 'How Qyvox demonstrates that a real proof path ran instead of showing a fabricated animation.', 'ch16', 116)
    figure(doc, ASSETS / 'request_lifecycle.png', 'Figure 4. Live verification request lifecycle', 'Nine-step vertical flow from local input to witness, proof, purge, anonymous authentication, policy check, replay check, cryptographic verification, and minimal database commit.')
    p(doc, 'ProofDemo records browser events with performance.now(), changes stage labels as authentication and transport proceed, and appends server-measured trace steps returned by FastAPI. The server trace names policy, replay, verifier, and database operations and includes non-negative durations. The UI displays the exact request JSON after proof generation, excluding authorization headers and explicitly noting the absence of the witness.')
    table(doc, ['Evidence element', 'Source', 'What it demonstrates'], [
        ['Browser prover duration', 'performance.now() around fullProve', 'Real work occurred in this tab.'],
        ['Auth and round-trip duration', 'verifyProof client timing', 'Actual session resolution and network request.'],
        ['Policy/replay/verifier/database durations', 'FastAPI perf_counter', 'Server returned trace from this successful request.'],
        ['Exact payload inspector', 'Serialized ProofBundle', 'Only proof and publicSignals are in the body.'],
        ['Stored-fields boundary', 'Server trace constant', 'Intended persistent fields are user_id, verified_at, proof_hash.'],
    ], [2300, 2500, 4560], caption='Execution-receipt evidence', small=True)
    p(doc, 'The receipt is observability, not a second proof system. A malicious server could lie about its internal timings or stored fields. Independent assurance requires source review, deployment attestation, database policy review, audit logs, and where appropriate remote attestation or third-party audits. The receipt’s value is transparency for a live demo and integration debugging.')


def add_part_five(doc, bullet_id, decimal_id):
    part_opener(doc, 'V', 'API, authentication, and persistence', 'The server’s strict request boundary, bearer-token resolution, replay logic, isolated verifier, minimal schema, CORS, and fail-closed behavior.', ['API contract', 'Authentication and authorization', 'Verification pipeline', 'Replay protection', 'Database and RLS', 'Status, CORS, and failure semantics'])

    chapter(doc, '17', 'API contract', 'The exact request/response schema and why strict validation matters.', 'ch17', 117)
    code_block(doc, """POST /api/v1/verify
Authorization: Bearer <Supabase access token>
Content-Type: application/json

{
  "proof": {
    "pi_a": ["...", "...", "1"],
    "pi_b": [["...", "..."], ["...", "..."], ["1", "0"]],
    "pi_c": ["...", "...", "1"],
    "protocol": "groth16",
    "curve": "bn128"
  },
  "publicSignals": ["1", "2026"]
}""", 'Accepted request shape (coordinates abbreviated)')
    p(doc, 'Pydantic forbids extra fields at both the request and proof levels. Scalar strings must contain one to eighty decimal digits. pi_a and pi_c have exactly three elements; pi_b has exactly three rows with exactly two coordinates. publicSignals has exactly two values. The content-length middleware rejects oversized verify requests before JSON parsing when the header is present, and infrastructure should enforce the same limit for chunked bodies.')
    table(doc, ['Status', 'Meaning', 'Example'], [
        ['200', 'Proof accepted and receipt committed', 'verified=true with verified_at and trace.'],
        ['400', 'Malformed transport metadata', 'Invalid Content-Length.'],
        ['401', 'Missing, invalid, or expired bearer session', 'No accepted Supabase user.'],
        ['403', 'Policy statement or cryptographic proof rejected', 'Stale year, isEligible ≠ 1, or invalid proof.'],
        ['409', 'Account or exact proof already consumed', 'Replay fingerprint or primary-key conflict.'],
        ['413', 'Payload exceeds configured bound', 'Content length over MAX_REQUEST_BYTES.'],
        ['422', 'JSON shape or scalar validation failed', 'birthYear field, wrong proof dimensions, or unknown field.'],
        ['502', 'Replay or persistence database dependency failed', 'System fails closed instead of accepting without a receipt.'],
        ['503', 'Verifier unavailable or timed out', 'Missing artifact, Node failure, timeout, malformed verdict.'],
    ], [1000, 3300, 5060], caption='Verifier API error semantics', small=True)

    chapter(doc, '18', 'Authentication and authorization', 'How Qyvox obtains an account-scoped receipt without collecting identity attributes in the demo.', 'ch18', 118)
    p(doc, 'The browser lazily creates a Supabase client from NEXT_PUBLIC_SUPABASE_URL and a publishable key. It first restores an existing session. If none exists, it calls signInAnonymously. The resulting access token is attached as a bearer header. The birth year is already cleared before this step.')
    p(doc, 'FastAPI never accepts a client-provided user_id. It sends the bearer token to Supabase Auth, requires a user object, and converts the returned identifier to UUID. This prevents a caller from choosing a different receipt owner by editing JSON. The service-role key stays on the backend and must never be prefixed NEXT_PUBLIC or shipped to the browser.')
    table(doc, ['Credential', 'Location', 'Exposure rule'], [
        ['Supabase publishable key', 'Frontend environment', 'Designed for browser use; still rely on RLS and Auth, not key secrecy.'],
        ['Anonymous access token', 'Browser session + Authorization header', 'Short-lived bearer credential; protect from XSS and logs.'],
        ['Supabase service-role key', 'Backend environment only', 'Secret and privileged; never commit, print, embed, or expose to the client.'],
        ['Ceremony entropy', 'Ephemeral setup process', 'Generated locally and never written to source or runtime configuration.'],
    ], [2600, 2700, 4060], caption='Credential boundary', small=True)
    callout(doc, 'Credential hygiene', 'Any service-role or secret key pasted into a chat, issue, screenshot, log, or repository should be treated as exposed and rotated. This handbook contains placeholders only.', 'risk')

    chapter(doc, '19', 'Verification pipeline', 'The ordered server controls applied to each authenticated proof.', 'ch19', 119)
    add_steps(doc, [
        ('Request bound', 'Reject declared bodies over the configured maximum before parsing.'),
        ('Schema validation', 'Require exact proof dimensions, decimal scalar syntax, protocol, curve, and two public signals.'),
        ('Authentication', 'Resolve the bearer token through Supabase Auth and derive the user UUID.'),
        ('Policy binding', 'Require isEligible = 1 and public year = server current UTC year.'),
        ('Fingerprint', 'Serialize the validated payload canonically and compute SHA-256.'),
        ('Replay query', 'Look up the fingerprint; fail closed if the database query cannot complete.'),
        ('Concurrency gate', 'Acquire a bounded semaphore slot before launching the verifier.'),
        ('Cryptographic verification', 'Invoke verify.mjs with a pinned verification key, memory bound, timeout, fixed working directory, and JSON over stdin.'),
        ('Persistence', 'Insert user UUID, UTC timestamp, and proof hash. Never return success if the record cannot be saved.'),
        ('Response', 'Return verified=true, timestamp, and a privacy-safe timing trace.'),
    ], decimal_id)
    p(doc, 'The order is intentional. Cheap checks run before expensive verification. Replay detection runs before the verifier to avoid repeated CPU use. Persistence runs after proof validation, and its failure prevents a success receipt. Configuration failures are 503 server errors, not 403 invalid-proof responses, which preserves meaningful operational diagnosis.')
    callout(doc, 'Fail closed', 'If replay storage or receipt persistence is unavailable, the API rejects the request. It does not silently skip the control and claim success.', 'success')

    chapter(doc, '20', 'Replay protection', 'What the current fingerprint control blocks, what it does not block, and the challenge-bound design needed next.', 'ch20', 120)
    p(doc, 'The API serializes the validated proof and public signals with sorted keys and compact separators, hashes the bytes with SHA-256, and checks proof_hash in verified_users. The column is unique. A repeated canonical payload is rejected before verification, and a racing duplicate insert is caught by the unique constraint.')
    table(doc, ['Scenario', 'Current result', 'Explanation'], [
        ['Identical request resent', 'Blocked', 'Same canonical hash already exists.'],
        ['Same proof with JSON whitespace changed', 'Blocked', 'Server hashes its own canonical model dump, not raw bytes.'],
        ['Same valid proof submitted by another account', 'Blocked after first use', 'Fingerprint uniqueness is global.'],
        ['New proof generated from same witness', 'Not necessarily blocked', 'Groth16 proving is randomized; a fresh proof has a new fingerprint.'],
        ['Proof copied before first submission and front-run', 'Not cryptographically solved', 'Current proof is not bound to a server challenge or intended account inside the circuit.'],
        ['Stale public year', 'Blocked', 'Policy check requires current server UTC year.'],
    ], [2600, 2300, 4460], caption='Replay and freshness behavior', small=True)
    heading(doc, 'Next-generation challenge binding', 2)
    p(doc, 'A production circuit should include public challenge data such as a random server nonce, verifier or relying-party identifier, session commitment, policy identifier, and expiry. The server issues a one-time challenge, the browser proves against it, and the server atomically consumes it. This binds the proof to a session and purpose rather than merely detecting an identical serialized proof after the fact.')
    callout(doc, 'Current error message', '“Replay protection is temporarily unavailable” means the database lookup failed. It is a 502 dependency failure, not evidence that a proof was invalid.', 'note')

    chapter(doc, '21', 'Database schema and row-level security', 'Why the persistence model is deliberately small and how Supabase access is constrained.', 'ch21', 121)
    code_block(doc, """create table public.verified_users (
  user_id uuid primary key references auth.users(id) on delete cascade,
  verified_at timestamptz not null default timezone('utc', now()),
  proof_hash text not null unique
    check (proof_hash ~ '^[0-9a-f]{64}$')
);

alter table public.verified_users enable row level security;
revoke all on table public.verified_users from anon, authenticated;""", 'Privacy-minimal receipt schema')
    table(doc, ['Column', 'Purpose', 'Privacy note'], [
        ['user_id', 'Account-scoped verification identity and primary key.', 'Pseudonymous identifier, still personal/security-relevant in context.'],
        ['verified_at', 'UTC time of accepted verification.', 'Can reveal activity timing and must be access-controlled.'],
        ['proof_hash', 'Exact-proof replay fingerprint.', 'One-way fingerprint of public proof payload; not a DOB hash.'],
    ], [1800, 3400, 4160], caption='Persistent data dictionary')
    p(doc, 'There is no browser policy granting select, insert, update, or delete. The backend uses the service role to bypass RLS for controlled operations. Anonymous and authenticated roles are explicitly revoked. The live integration test checks that direct browser-role reads and writes are denied and that the persisted row contains exactly the three expected columns.')
    callout(doc, 'Privacy nuance', 'A minimal receipt is not “zero data.” UUIDs, timestamps, and proof fingerprints still need retention rules, access control, monitoring, and breach analysis.', 'warning')

    chapter(doc, '22', 'Status, CORS, and failure semantics', 'Operational controls that keep browser-to-API communication narrow and diagnosable.', 'ch22', 122)
    p(doc, 'CORSMiddleware permits only configured exact origins, with GET, POST, and OPTIONS and only Authorization and Content-Type request headers. Wildcards are rejected by the settings parser. This protects browser integrations from accidental broad origin exposure, although CORS is not an authentication control and does not stop non-browser clients.')
    p(doc, 'GET /health reports only that the FastAPI process responds. GET /status performs a bounded dependency check and returns operational or unavailable labels for the verifier artifacts and database. It avoids exposing raw stack traces, credentials, file paths, or database diagnostics to public callers.')
    table(doc, ['Failure', 'External response', 'Security rationale'], [
        ['Malformed or oversized request', '400/413/422', 'Reject before expensive cryptography.'],
        ['Invalid/stale proof', '403', 'No receipt is written.'],
        ['Missing/expired auth', '401', 'No client-chosen identity accepted.'],
        ['Replay', '409', 'Exact proof or already-verified account is not accepted again.'],
        ['Replay database outage', '502', 'Cannot establish non-reuse, so fail closed.'],
        ['Verifier runtime outage', '503', 'Do not mislabel infrastructure failure as a bad proof.'],
        ['Receipt write outage', '502', 'Do not return a success that was not durably recorded.'],
    ], [2600, 1700, 5060], caption='Failure classification')


def add_part_six(doc, bullet_id, decimal_id):
    part_opener(doc, 'VI', 'Security model and production hardening', 'Assets, actors, trust assumptions, attack paths, current controls, residual risk, and the upgrades required for issuer-backed identity assurance.', ['Threat model', 'Attack analysis', 'Secrets and supply chain', 'Privacy and compliance posture', 'Production architecture roadmap'])

    chapter(doc, '23', 'Threat model', 'What Qyvox protects, who may attack it, and which systems remain trusted.', 'ch23', 123)
    table(doc, ['Asset', 'Why it matters'], [
        ['Private birth-year witness', 'Exposure defeats the data-minimization objective.'],
        ['Proof acceptance integrity', 'False acceptance undermines relying-party policy.'],
        ['Circuit and artifact provenance', 'A modified relation can prove the wrong statement.'],
        ['Service-role key', 'Compromise grants privileged database access.'],
        ['Anonymous access tokens', 'Theft can impersonate sessions and create receipts.'],
        ['Verification receipts', 'They encode account activity and eligibility events.'],
        ['Availability and bounded compute', 'Proof verification can be used for resource exhaustion.'],
    ], [3000, 6360], caption='Protected assets')
    heading(doc, 'Representative adversaries', 2)
    add_bullets(doc, [
        'A dishonest user supplying a false but qualifying witness.',
        'A network attacker replaying, modifying, or front-running proof traffic.',
        'A malicious website script, dependency, extension, or compromised browser environment.',
        'An unauthenticated API client sending malformed, off-curve, oversized, or high-volume payloads.',
        'A database attacker seeking receipts or attempting to bypass replay controls.',
        'A compromised operator or deployment pipeline replacing circuit artifacts or configuration.',
        'Colluding ceremony participants retaining toxic-waste material.',
    ], bullet_id)
    heading(doc, 'Trusted computing base', 2)
    p(doc, 'The baseline trusts the user’s browser and loaded application bundle to handle the witness honestly, Circom/circomlib/SnarkJS and their build chain, the ceremony outcome, FastAPI and Node runtimes, the verification key, Supabase Auth and database, environment-secret handling, TLS termination, and the deployment operator. Zero knowledge narrows data disclosure to the verifier; it does not eliminate the rest of the system’s trust assumptions.')

    chapter(doc, '24', 'Attack analysis and current controls', 'A structured review of likely failure modes and residual risk.', 'ch24', 124)
    table(doc, ['Vector', 'Current control', 'Residual risk / next step'], [
        ['False self-asserted age', 'Circuit enforces arithmetic only.', 'Add issuer-signed credential commitment and revocation.'],
        ['Finite-field wraparound', '16-bit Num2Bits on years and difference.', 'Independent circuit audit and mutation testing.'],
        ['Underconstrained signal', 'Explicit comparator wiring and forced output.', 'Formal constraint review and unconstrained-signal tooling.'],
        ['Tampered public year', 'Proof binding + server UTC year check.', 'Move to exact date and signed policy version.'],
        ['Exact replay', 'Canonical SHA-256 fingerprint + unique DB index.', 'Add one-time challenge consumed atomically.'],
        ['Front-running', 'Authenticated submitter and exact replay detection.', 'Bind account/session/verifier/challenge in public signals.'],
        ['Malformed/off-curve proof', 'Strict Pydantic shape; SnarkJS false verdict handling.', 'Fuzz parsers and use native hardened verifier.'],
        ['Resource exhaustion', '32 KB request default, 20 s timeout, semaphore, Node memory bound.', 'Rate limiting, queueing, WAF, persistent verifier pool, load tests.'],
        ['XSS/witness theft', 'No intentional network serialization.', 'Strict CSP, dependency integrity, Trusted Types, security review.'],
        ['Service-role leakage', 'Backend-only environment secret.', 'Secret manager, rotation, scoped networks, audit alerts.'],
        ['Artifact substitution', 'Pinned files in release tree.', 'Signed manifest, immutable URLs, checksums, reproducible builds.'],
        ['Ceremony compromise', 'Development contributions only.', 'Independent public MPC with published transcript.'],
    ], [1800, 3500, 4060], caption='Threat-control matrix', small=True)
    callout(doc, 'Security posture', 'The most consequential current risk is not breaking Groth16; it is that the witness is self-asserted. Production value depends on adding trusted provenance.', 'risk')

    chapter(doc, '25', 'Secrets, dependencies, and supply-chain security', 'Operational controls for the parts of the system that cryptography does not protect automatically.', 'ch25', 125)
    add_bullets(doc, [
        'Keep service-role and other privileged secrets in a managed secret store; never in NEXT_PUBLIC variables, source control, build logs, client bundles, or documentation.',
        'Rotate any key that appears in chat, screenshots, tickets, logs, shell history, or a public artifact.',
        'Pin dependencies and lockfiles; review advisories for Next.js, FastAPI/Starlette, Supabase clients, SnarkJS, circomlib, and transitive packages.',
        'Generate software bills of materials for frontend, backend, container, and circuit toolchains.',
        'Sign release artifacts and container images; verify provenance in deployment.',
        'Use a restrictive Content Security Policy and avoid unreviewed third-party scripts on the proof page.',
        'Separate ceremony machines and production build machines; preserve reproducible hashes.',
        'Log only privacy-safe event identifiers and outcomes. Never log request bodies, authorization headers, proof coordinates at high volume, or private input.',
    ], bullet_id)
    heading(doc, 'Container controls', 2)
    p(doc, 'The backend Dockerfile uses a multi-stage build, separates Node dependency installation from the Python runtime image, and runs the final service as a non-root qyvox user with UID 10001. Production should additionally use a read-only filesystem, drop Linux capabilities, constrain CPU/memory/PIDs, pin base-image digests, scan images, and define health checks and graceful termination.')

    chapter(doc, '26', 'Privacy, governance, and compliance posture', 'How to talk about regulatory value accurately and what work remains outside the code.', 'ch26', 126)
    p(doc, 'Qyvox can reduce the amount of personal information a relying party receives and stores. That may reduce breach impact, retention burden, data-subject response scope, and opportunities for secondary use. It does not automatically determine whether a deployment is lawful, exempt from identity rules, or compliant with GDPR, KYC, AML, COPPA, age-assurance, financial, gaming, or jurisdiction-specific requirements.')
    table(doc, ['Governance question', 'Qyvox technical contribution', 'Still required'], [
        ['Data minimization', 'Raw birth year omitted from API and schema.', 'Document the purpose and confirm public signals are proportionate.'],
        ['Lawful basis', 'Not determined by cryptography.', 'Legal analysis, notices, consent or other basis as applicable.'],
        ['Retention', 'Minimal three-column receipt.', 'Define retention duration and deletion workflows.'],
        ['Access rights', 'No DOB record to return from Qyvox.', 'Account/receipt access, correction, deletion, and audit procedures.'],
        ['Vendor management', 'Portable self-hostable architecture direction.', 'Contracts, subprocessors, regions, SLAs, and incident terms.'],
        ['Assurance', 'Public circuit and verification artifacts.', 'External audit, ceremony review, penetration test, and operational evidence.'],
    ], [2200, 3400, 3760], caption='Compliance boundary', small=True)
    callout(doc, 'Not legal advice', 'Use this architecture as evidence for counsel and compliance teams, not as a substitute for their deployment-specific analysis.', 'warning')

    chapter(doc, '27', 'Production architecture roadmap', 'The sequence that transforms the research baseline into issuer-backed, challenge-bound identity assurance.', 'ch27', 127)
    add_steps(doc, [
        ('Issuer provenance', 'Define a credential format whose age attribute is signed or committed by an authorized issuer. Prove signature possession or membership without revealing DOB.'),
        ('Exact-date policy', 'Model year, month, day, leap years, jurisdiction, policy version, and trusted current time.'),
        ('Challenge binding', 'Add nonce, session/account commitment, verifier identifier, policy identifier, and expiry as public inputs.'),
        ('Revocation', 'Prove non-revocation or check privacy-preserving status data with bounded freshness.'),
        ('Ceremony', 'Run and publish an independent multi-party setup tied to the audited R1CS.'),
        ('Verifier service', 'Replace per-request Node startup with a persistent bounded pool or audited native verifier while preserving isolation and limits.'),
        ('Wallet and recovery', 'Protect credential keys, device migration, consent, loss recovery, and multi-device use.'),
        ('Audit and governance', 'Commission cryptographic, application, infrastructure, privacy, and legal reviews; publish resolved findings.'),
        ('Operations', 'Add rate limits, idempotency, observability, incident response, key rotation, backup/restore tests, and SLOs.'),
    ], decimal_id)
    table(doc, ['Phase', 'Exit evidence'], [
        ['Research baseline', 'Current circuit, real browser proof, strict verifier, minimal receipt, repeatable tests.'],
        ['Private alpha', 'Issuer prototype, challenge binding, worker prover, persistent verifier, internal threat review.'],
        ['External pilot', 'Independent audit, mobile benchmark matrix, ceremony transcript, privacy assessment, monitored operations.'],
        ['Production', 'Issuer contracts, revocation, hardened key management, SLOs, incident drills, signed releases, recurring audits.'],
    ], [1900, 7460], caption='Suggested maturity gates')


def add_part_seven(doc, bullet_id, decimal_id):
    part_opener(doc, 'VII', 'Build, run, test, and operate', 'A practical operator guide for local setup, environment variables, testing, deployment, observability, incident response, and troubleshooting.', ['Repository map', 'Local setup', 'Configuration reference', 'Testing and validation', 'Deployment and operations', 'Troubleshooting'])

    chapter(doc, '28', 'Repository map', 'Where every major component lives and how artifacts flow between directories.', 'ch28', 128)
    code_block(doc, """Qyvox/
├── circuits/
│   ├── age_check.circom
│   ├── setup.sh
│   ├── smoke_test.mjs
│   └── benchmark.mjs
├── frontend/
│   ├── app/{page,whitepaper,docs,research,faq}.tsx
│   ├── components/
│   ├── lib/{zkProver,verifyProof,supabaseClient}.ts
│   └── public/zk/{age_check.wasm,age_check_final.zkey}
├── backend/
│   ├── main.py
│   ├── verify.mjs
│   ├── test_main.py
│   ├── live_integration_test.mjs
│   ├── Dockerfile
│   └── zk/verification_key.json
├── supabase/schema.sql
└── README.md""", 'Current monorepo topology')
    p(doc, 'The circuit build produces public prover assets for the frontend and a verification key for the backend. The frontend does not need the verification key for normal proving, and the backend does not need the private witness or proving key. This separation maps cryptographic roles to deployment roles.')

    chapter(doc, '29', 'Local setup and first proof', 'A clean-room sequence from dependencies to a working browser-to-database verification.', 'ch29', 129)
    add_steps(doc, [
        ('Install circuit dependencies', 'Run npm ci in circuits and ensure Circom 2.x and OpenSSL are available.'),
        ('Build artifacts', 'Run npm run setup in circuits. Confirm WASM/zkey are copied to frontend/public/zk and verification_key.json to backend/zk.'),
        ('Prepare Supabase', 'Enable Anonymous Sign-Ins, execute supabase/schema.sql, and verify browser roles cannot access verified_users.'),
        ('Configure frontend', 'Set NEXT_PUBLIC_SUPABASE_URL, NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY, NEXT_PUBLIC_API_URL, and optionally NEXT_PUBLIC_SITE_URL.'),
        ('Configure backend', 'Set SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, and exact FRONTEND_ORIGINS; tune verifier limits only with testing.'),
        ('Start API', 'Install backend requirements and run Uvicorn for backend.main:app.'),
        ('Start portal', 'Run the Next.js development server in frontend.'),
        ('Exercise demo', 'Enter a qualifying year, inspect the real execution receipt, and confirm the request body lacks the witness.'),
        ('Check storage', 'Verify that only user_id, verified_at, and proof_hash were written.'),
    ], decimal_id)
    callout(doc, 'Security setup', 'Use placeholders in documentation and .env.example files. Never copy a service-role secret into frontend/.env.local.', 'risk')

    chapter(doc, '30', 'Configuration reference', 'Every important environment control and the boundary it governs.', 'ch30', 130)
    table(doc, ['Variable', 'Side', 'Purpose / safe guidance'], [
        ['NEXT_PUBLIC_SUPABASE_URL', 'Frontend', 'Project URL; safe to expose as connection metadata.'],
        ['NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY', 'Frontend', 'Browser key; security depends on Auth and RLS.'],
        ['NEXT_PUBLIC_API_URL', 'Frontend', 'Verifier base URL; use HTTPS in non-local environments.'],
        ['NEXT_PUBLIC_SITE_URL', 'Frontend', 'Canonical metadata URL.'],
        ['SUPABASE_URL', 'Backend', 'Same project endpoint used by server client.'],
        ['SUPABASE_SERVICE_ROLE_KEY', 'Backend secret', 'Privileged key; store and rotate as a secret.'],
        ['FRONTEND_ORIGINS', 'Backend', 'Comma-separated exact origins; wildcard rejected.'],
        ['NODE_BINARY', 'Backend', 'Node runtime path for isolated verifier.'],
        ['VERIFIER_SCRIPT', 'Backend', 'Path to verify.mjs.'],
        ['VERIFICATION_KEY_PATH', 'Backend', 'Pinned verification_key.json path.'],
        ['VERIFICATION_TIMEOUT_SECONDS', 'Backend', '1-60 second bound; default 20.'],
        ['VERIFIER_CONCURRENCY', 'Backend', 'Bounded parallel verifiers; default 2, maximum 16.'],
        ['MAX_REQUEST_BYTES', 'Backend', 'Body limit; default 32,768 bytes.'],
        ['EXPECTED_CURRENT_YEAR', 'Backend/test', 'Optional deterministic override; normally UTC year.'],
    ], [3000, 1700, 4660], caption='Environment-variable reference', small=True)

    chapter(doc, '31', 'Testing and validation', 'How to reproduce circuit, API, frontend, integration, and benchmark evidence.', 'ch31', 131)
    table(doc, ['Layer', 'Command or suite', 'Coverage'], [
        ['Circuit', 'npm test in circuits', 'Eligible, exact boundary, underage, future year, out-of-range year, tampered public signal, backend helper.'],
        ['Benchmark', 'node benchmark.mjs in circuits', '5 proving samples, 50 warm verifies, 10 subprocess verifies, payload and artifact sizes.'],
        ['Backend unit', 'python -m unittest -v test_main.py', '11 focused cases using mocks; no live Supabase required.'],
        ['Live integration', 'node live_integration_test.mjs', 'Anonymous auth, real proof, RLS denial, storage columns, replay, stale/private/missing-auth/oversize/CORS cases, cleanup.'],
        ['Frontend lint', 'npm run lint', 'ESLint and Next.js rules.'],
        ['Frontend production build', 'npm run build', 'Compilation, TypeScript, page-data collection, static generation.'],
        ['Manual browser QA', 'Desktop and narrow viewport', 'Proof flow, payload inspector, execution trace, navigation, overflow, reduced motion.'],
    ], [1800, 2800, 4760], caption='Validation matrix', small=True)
    heading(doc, 'Validation snapshot - 27 August 2026', 2)
    add_bullets(doc, [
        'Circuit smoke test: passed.',
        'Frontend lint: passed.',
        'Frontend production build: passed; all public routes generated successfully.',
        'Fresh Node reference benchmark: prover median 104.20 ms and p95 601.69 ms across 5 samples; warm verifier median 25.68 ms and p95 45.16 ms across 50 samples; subprocess verifier median 817.90 ms and p95 1,077.76 ms across 10 samples.',
        'Payload and artifact sizes in that run: 724-byte proof JSON, 763-byte complete request JSON, 38,561-byte WASM, 41,244-byte proving key.',
        'Backend unit suite contains 11 focused tests. It was not rerun in the document-authoring runtime because the backend Python dependencies were not installed in that isolated runtime; run the documented command in the project backend environment before release.',
    ], bullet_id)
    callout(doc, 'Benchmark interpretation', 'These timings differ from the older website research snapshot, demonstrating why benchmarks need date, environment, sample count, and percentile. Update public benchmark pages from a controlled campaign before making performance claims.', 'warning')

    chapter(doc, '32', 'Deployment, observability, and incident response', 'The operational practices needed to run the verifier safely.', 'ch32', 132)
    heading(doc, 'Deployment checklist', 2)
    add_bullets(doc, [
        'Terminate TLS at a trusted edge and redirect HTTP to HTTPS.',
        'Set exact production CORS origins and verify denied preflights.',
        'Keep the service-role key in a secret manager and restrict who can read or rotate it.',
        'Run the backend container as non-root with a read-only filesystem and resource limits.',
        'Pin the circuit release manifest and verification key in the deployed image.',
        'Apply edge and account rate limits before expensive verification.',
        'Use a bounded persistent verifier pool or audited native verifier for predictable latency.',
        'Monitor health, dependency status, rejection classes, queue depth, verifier timeouts, database latency, and receipt conflicts without logging proof bodies or tokens.',
        'Test backup/restore and receipt-retention deletion procedures.',
    ], bullet_id)
    heading(doc, 'Incident priorities', 2)
    table(doc, ['Incident', 'Immediate action', 'Follow-up'], [
        ['Service-role exposure', 'Revoke/rotate; disable affected service; audit database access.', 'Identify leak path, narrow permissions, notify stakeholders as required.'],
        ['Artifact mismatch', 'Stop acceptance; roll back to known manifest.', 'Rebuild, verify hashes, investigate pipeline, reissue release evidence.'],
        ['Verifier vulnerability', 'Disable or isolate affected path; deploy patched verifier.', 'Revalidate proofs/receipts per risk assessment and publish advisory.'],
        ['Database outage', 'Maintain fail-closed behavior; communicate degraded status.', 'Restore service, reconcile attempts, test replay uniqueness.'],
        ['Frontend compromise', 'Take proof page offline; revoke sessions if necessary.', 'Audit scripts, CSP, dependencies, and potential witness exposure.'],
    ], [1800, 3700, 3860], caption='Incident-response playbook', small=True)

    chapter(doc, '33', 'Troubleshooting', 'A symptom-to-cause guide for the most likely setup and runtime failures.', 'ch33', 133)
    table(doc, ['Symptom', 'Likely cause', 'Resolution'], [
        ['“Qyvox authentication is not configured.”', 'Missing frontend Supabase URL or publishable key at build/runtime.', 'Set NEXT_PUBLIC variables, restart Next.js, inspect browser bundle configuration; never substitute the service-role key.'],
        ['Private sign-in disabled', 'Anonymous sign-ins are off in Supabase Auth.', 'Enable Anonymous Sign-Ins and retry with a fresh session.'],
        ['Replay protection temporarily unavailable', 'verified_users query failed: schema, credentials, network, RLS/service-role, or Supabase outage.', 'Check /status, backend logs without secrets, schema deployment, service-role configuration, network and project status.'],
        ['Verifier temporarily unavailable', 'Node missing, verify.mjs/vkey missing, timeout, nonzero subprocess, malformed stdout.', 'Confirm image contents, paths, Node runtime, artifact manifest, memory and timeout.'],
        ['Proof invalid', 'Wrong artifacts, public signals, witness, or tampered/off-curve points.', 'Rebuild one artifact set, verify public order/year, reproduce circuit smoke test.'],
        ['403 current period', 'publicSignals are not [1, server UTC year].', 'Use UTC year and a qualifying witness; check time/config override.'],
        ['422 body validation', 'Extra/private field, scalar formatting, wrong coordinate dimensions, protocol/curve mismatch.', 'Send the exact proof-only schema.'],
        ['CORS preflight rejected', 'Origin absent or has mismatched scheme/host/port/trailing configuration.', 'Add exact origin to FRONTEND_ORIGINS and restart API.'],
        ['Duplicate/409', 'Account already has receipt or proof hash was consumed.', 'Treat as expected idempotency/replay outcome; decide product recovery policy.'],
        ['Mobile tab stalls', 'Main-thread proving or memory/thermal pressure.', 'Move proving to worker, show progress, reduce constraints/artifacts, benchmark target devices.'],
    ], [2600, 3000, 3760], caption='Troubleshooting matrix', small=True)


def add_part_eight(doc, bullet_id, decimal_id):
    part_opener(doc, 'VIII', 'Product, business, and research strategy', 'How the architecture creates value, which customers benefit, how to evaluate adoption, and what evidence should guide the next research phase.', ['Value proposition', 'Enterprise adoption', 'Research and benchmarking', 'Open source and assurance'])

    chapter(doc, '34', 'Product and business value', 'How to translate the architecture into a credible outcome for buyers, investors, and grant reviewers.', 'ch34', 134)
    p(doc, 'Qyvox’s product value is not “cryptography for its own sake.” It is the ability to separate an eligibility decision from custody of the underlying personal fact. This can reduce the data stored by a relying party, improve user trust, narrow breach consequences, and make privacy a verifiable system property rather than a privacy-policy promise.')
    table(doc, ['Audience', 'Primary value', 'Evidence they need'], [
        ['Enterprise buyer', 'Reduced PII custody with a familiar API integration.', 'Threat model, deployment model, issuer plan, audit results, SLAs, legal assessment.'],
        ['Developer/CTO', 'Portable browser prover and strict proof-only endpoint.', 'Quickstart, SDK ergonomics, versioned artifacts, tests, performance, self-hosting.'],
        ['Investor/grant committee', 'Deep-tech differentiation and defensible privacy architecture.', 'Technical proof of work, market problem, milestones, independent validation, adoption path.'],
        ['End user', 'Eligibility without uploading a birth year or identity image to Qyvox.', 'Clear UX, trustworthy issuer, transparent disclosure, recovery and support.'],
        ['Auditor/researcher', 'Public relation and measurable trust boundaries.', 'Source, R1CS, ceremony transcript, manifests, test corpus, findings and remediation.'],
    ], [1900, 3200, 4260], caption='Stakeholder value map', small=True)
    heading(doc, 'Responsible positioning', 2)
    p(doc, 'The honest near-term positioning is “privacy-preserving eligibility infrastructure and research baseline,” not “complete identity truth.” The strongest commercialization milestone is an issuer-backed credential flow that preserves the current proof-only relying-party boundary.')

    chapter(doc, '35', 'Enterprise adoption and integration', 'A practical evaluation sequence for prospective relying parties and self-hosting teams.', 'ch35', 135)
    add_steps(doc, [
        ('Define the predicate', 'Identify the minimum fact the business truly needs and the policy/jurisdiction governing it.'),
        ('Choose issuer trust', 'Decide which authorities can attest the underlying attribute and how revocation works.'),
        ('Model public signals', 'Expose only the necessary result, policy, verifier, challenge, and expiry fields.'),
        ('Integrate SDK', 'Run proving locally and ensure application analytics never capture witness fields.'),
        ('Integrate API', 'Authenticate, issue challenges, verify proofs, and consume challenges atomically.'),
        ('Design receipts', 'Store only identifiers, timestamps, policy references, and fingerprints required for accountability.'),
        ('Audit', 'Review circuit, ceremony, frontend supply chain, backend, infrastructure, privacy, and legal controls.'),
        ('Pilot', 'Measure completion, error rate, mobile performance, support burden, fraud outcomes, and user trust.'),
    ], decimal_id)
    table(doc, ['Adoption question', 'Current answer'], [
        ['Blockchain required?', 'No. Browser WASM, REST API, and PostgreSQL are sufficient.'],
        ['Can verifier be self-hosted?', 'Architecture supports it; production packaging, manifests, support, and terms remain roadmap work.'],
        ['Can Qyvox recover DOB?', 'The baseline never receives DOB/birthYear; proof privacy is computational under assumptions.'],
        ['Does it prove truth?', 'Not until a trusted issuer credential is included.'],
        ['Does it reduce compliance scope?', 'Potentially, through minimization; exact effect is jurisdiction and deployment specific.'],
        ['Can one proof be reused?', 'Exact reuse is blocked now; challenge binding is required for stronger freshness.'],
    ], [3300, 6060], caption='Enterprise due-diligence summary')

    chapter(doc, '36', 'Research and benchmarking program', 'How to produce evidence that is comparable, honest, and useful for engineering decisions.', 'ch36', 136)
    p(doc, 'The current circuit is intentionally small, so performance conclusions must not be generalized to issuer signatures, revocation proofs, or richer date logic. Every public benchmark should publish hardware, operating system, browser/runtime, power state, artifact cache state, sample counts, warmup, median, p95/p99, failure rate, memory, and artifact sizes.')
    table(doc, ['Campaign', 'Measurements', 'Decision enabled'], [
        ['Mobile prover matrix', 'Cold/warm p50/p95, peak memory, thermal drift, crash rate, artifact download.', 'Worker strategy, circuit budget, supported device floor.'],
        ['Verifier load test', 'Throughput, p50/p95/p99, queue depth, CPU/RAM, timeout/error rate.', 'Pool size, autoscaling, rate limits, SLOs.'],
        ['Network impairment', '3G/4G latency, loss, cache misses, retry behavior.', 'Payload delivery and UX resilience.'],
        ['Circuit growth', 'Constraints, zkey/WASM size, proving and verification deltas per feature.', 'Issuer/revocation design tradeoffs.'],
        ['Security failure injection', 'DB outage, stale challenge, verifier crash, malformed points, concurrency exhaustion.', 'Fail-closed confidence and incident readiness.'],
        ['User study', 'Completion, comprehension, trust, abandonment, support questions.', 'Disclosure language and interface improvements.'],
    ], [1900, 4200, 3260], caption='Research campaign matrix', small=True)
    callout(doc, 'Current benchmark', 'The 27 August 2026 reference run is a Node measurement on one environment. It is evidence that the pipeline works—not proof of mobile performance or a production latency guarantee.', 'note')

    chapter(doc, '37', 'Open source, auditability, and trust', 'How public artifacts can convert technical claims into independently reproducible evidence.', 'ch37', 137)
    add_bullets(doc, [
        'Publish circuit source, R1CS, symbol map, WASM, proving key, verification key, and cryptographic hashes as one release.',
        'Publish ceremony transcripts, contributor verification, and the exact circuit hash used during setup.',
        'Publish negative tests, benchmark scripts, test vectors, and expected public-signal ordering.',
        'Maintain a security policy, vulnerability-reporting channel, disclosure timeline, and signed advisories.',
        'Separate open-source SDK/circuit licensing from commercial orchestration only with clear, reviewable terms.',
        'Track external audit findings and remediation status without presenting a point-in-time audit as permanent safety.',
        'Expose a live status page that distinguishes API, verifier, and database readiness without leaking internals.',
    ], bullet_id)
    p(doc, 'A polished portal supports reproducible trust, but it cannot replace published source, artifact hashes, test vectors, and deployment-key verification.')


def add_appendices(doc, bullet_id, decimal_id):
    part_opener(doc, 'IX', 'Reference appendices', 'Compact source-of-truth material for integration, review, operations, and first-time learning.', ['API examples', 'Glossary', 'Frequently asked questions', 'Release checklist', 'Source-of-truth index'])

    chapter(doc, 'A', 'API examples', 'Copyable request and response patterns with private fields deliberately absent.', 'appa', 201)
    code_block(doc, """curl -X POST "$QYVOX_API_URL/api/v1/verify" \\
  -H "Authorization: Bearer $SUPABASE_ACCESS_TOKEN" \\
  -H "Content-Type: application/json" \\
  --data-binary @proof-bundle.json""", 'Illustrative authenticated verification request')
    code_block(doc, """{
  "verified": true,
  "verified_at": "2026-08-27T00:00:00Z",
  "trace": {
    "proof_system": "Groth16",
    "curve": "BN254 / bn128",
    "received_fields": ["proof", "publicSignals"],
    "stored_fields": ["user_id", "verified_at", "proof_hash"],
    "steps": [
      {"component": "policy", "outcome": "passed", "ms": 0.1},
      {"component": "replay", "outcome": "passed", "ms": 12.3},
      {"component": "verifier", "outcome": "passed", "ms": 800.0},
      {"component": "database", "outcome": "committed", "ms": 20.0}
    ],
    "total_ms": 832.4
  }
}""", 'Successful response shape; durations are illustrative')
    callout(doc, 'Prohibited body field', 'A request that adds birthYear, dob, age, user_id, or any unknown top-level field fails strict validation. The authorization token belongs in the header, not the JSON body.', 'privacy')

    chapter(doc, 'B', 'Glossary', 'Plain-language definitions for the cryptography, web, database, and security terms used throughout Qyvox.', 'appb', 202)
    glossary = [
        ('Anonymous authentication', 'A session with a stable account identifier but no required name, email, or profile attributes.'),
        ('Artifact manifest', 'A signed or published record binding source, circuit, keys, and hashes into one release.'),
        ('BN254 / bn128', 'The pairing-friendly elliptic curve used by the current SnarkJS Groth16 setup.'),
        ('Canonical serialization', 'A deterministic JSON representation used so equivalent payloads produce the same fingerprint.'),
        ('Challenge', 'A fresh server-issued value that a proof can bind to for stronger replay and front-running resistance.'),
        ('Circom', 'A language for describing arithmetic constraints used by zero-knowledge proving systems.'),
        ('Circuit', 'The mathematical relation that decides whether witness and public signals are valid.'),
        ('Completeness', 'Valid witnesses can produce proofs accepted by an honest verifier.'),
        ('Constraint', 'A field equation that every valid witness assignment must satisfy.'),
        ('CORS', 'A browser policy controlling which origins may call an API; not an authentication mechanism.'),
        ('Credential commitment', 'A cryptographic representation that can bind hidden credential attributes to an issuer statement.'),
        ('Data minimization', 'Collecting, using, and retaining only information necessary for a purpose.'),
        ('Elliptic-curve point', 'A group element used in proof construction and pairing-based verification.'),
        ('Fail closed', 'Reject or stop when a security dependency is unavailable rather than bypassing the control.'),
        ('Finite field', 'A bounded arithmetic system in which operations wrap modulo a large prime.'),
        ('Front-running', 'Submitting another party’s observed transaction or proof first to capture its effect.'),
        ('Groth16', 'A succinct non-interactive argument system with a circuit-specific trusted setup.'),
        ('JWT / bearer token', 'A credential presented in an HTTP Authorization header; possession grants the represented session authority.'),
        ('Knowledge soundness', 'A successful prover is understood to know a witness satisfying the relation, under formal assumptions.'),
        ('Nonce', 'A value intended for one use, commonly added to make a proof fresh.'),
        ('Num2Bits', 'A Circom gadget that constrains a value to a specific non-negative bit width.'),
        ('Pairing', 'A bilinear map used by Groth16 verification to check algebraic relationships efficiently.'),
        ('PII', 'Personally identifiable information; exact legal definitions vary.'),
        ('Predicate', 'A yes/no statement such as age eligibility.'),
        ('Proof', 'Public cryptographic evidence that a witness satisfying the circuit exists.'),
        ('Proof fingerprint', 'Qyvox’s SHA-256 digest of the canonical proof bundle, used to reject exact reuse.'),
        ('Proving key', 'Public circuit-specific material used with the witness to generate a Groth16 proof.'),
        ('Public signal', 'A value intentionally disclosed and cryptographically bound to the proof.'),
        ('Powers of Tau', 'A reusable multi-party setup phase used by pairing-based SNARK workflows.'),
        ('R1CS', 'Rank-1 Constraint System, the multiplication-of-linear-combinations representation of circuit constraints.'),
        ('Replay attack', 'Reusing a valid message or proof outside its intended one-time context.'),
        ('Revocation', 'Invalidating a credential before its nominal expiry.'),
        ('RLS', 'PostgreSQL row-level security, which controls database-row access per role and policy.'),
        ('SNARK', 'Succinct Non-interactive Argument of Knowledge.'),
        ('Soundness', 'Invalid statements should not be accepted except with negligible probability under assumptions.'),
        ('Structured reference string', 'Public parameters produced by setup and used by the prover and verifier.'),
        ('Toxic waste', 'Secret setup randomness that must not remain available to a colluding adversary.'),
        ('Verification key', 'Public circuit-specific material used to verify Groth16 proofs.'),
        ('Verifier', 'The algorithm or service that checks a proof against public signals and a verification key.'),
        ('WASM / WebAssembly', 'Portable bytecode executed by the browser for the witness calculation.'),
        ('Witness', 'Private and intermediate values assigned to circuit signals for one proof.'),
        ('Zero knowledge', 'A property that the proof reveals no witness information beyond the public statement under the scheme’s assumptions.'),
    ]
    table(doc, ['Term', 'Definition'], [[a, b] for a, b in glossary], [2600, 6760], caption='Qyvox glossary', small=True)

    chapter(doc, 'C', 'Frequently asked questions', 'Short, review-ready answers that preserve the current implementation boundary.', 'appc', 203)
    faqs = [
        ('Can Qyvox recover a user’s birth year?', 'The server never receives it. Recovering the witness from a valid proof should be computationally infeasible under Groth16 assumptions; this is not a claim of information-theoretic impossibility.'),
        ('Does Qyvox need a blockchain?', 'No. The baseline uses browser WebAssembly, a REST API, and PostgreSQL.'),
        ('Does the proof prove the year is true?', 'No. It proves knowledge of a qualifying value. Trusted issuer provenance is the principal production upgrade.'),
        ('What is stored?', 'Authenticated user UUID, verification timestamp, and exact-proof SHA-256 fingerprint.'),
        ('Why is currentYear public?', 'It binds the proof to a policy epoch the server can check.'),
        ('Why is isEligible public?', 'The relying party needs the yes/no result; the circuit forces it to one.'),
        ('Can a proof be replayed?', 'Exact payload reuse is blocked. Fresh randomized proofs and front-running require challenge/session binding for stronger prevention.'),
        ('What if Supabase is down?', 'Replay and persistence failures return 502; the service does not claim success.'),
        ('What if the verifier crashes?', 'The API returns 503 rather than classifying the proof as invalid.'),
        ('Are the proving key and WASM secret?', 'No. They are public artifacts, but their integrity and version provenance remain critical.'),
        ('Is the setup production-ready?', 'No. The included ceremony is a reproducible development ceremony on one machine.'),
        ('Does clearing React state erase RAM?', 'It removes application references promptly but cannot guarantee physical zeroization in a managed browser runtime.'),
        ('Is Qyvox compliant by default?', 'No. Data minimization helps, but legal and operational obligations depend on jurisdiction and deployment.'),
    ]
    for question, answer in faqs:
        h = heading(doc, question, 2)
        h.paragraph_format.space_before = Pt(10)
        p(doc, answer)

    chapter(doc, 'D', 'Release and audit checklist', 'A single gate for cryptography, application, infrastructure, privacy, and evidence before external use.', 'appd', 204)
    checklist = [
        'Circuit policy specification approved by product, legal, and cryptography reviewers.',
        'No unconstrained or underconstrained security-relevant signals found.',
        'Negative, boundary, property, mutation, and cross-implementation tests pass.',
        'Independent circuit and verifier audit findings resolved or explicitly accepted.',
        'Issuer signature/commitment and revocation model implemented for production claims.',
        'One-time challenge, session/verifier binding, policy identifier, and expiry enforced.',
        'Public MPC ceremony complete; transcripts and artifact hashes published.',
        'Frontend artifacts use immutable version binding and strong supply-chain controls.',
        'Birth year absent from requests, logs, analytics, traces, error reports, and database schemas.',
        'Service-role and signing secrets held in managed secret systems and rotation tested.',
        'RLS, grants, and direct browser access validated in a live project.',
        'Rate limits, body limits, timeouts, concurrency caps, and resource limits load-tested.',
        'Mobile prover matrix completed with memory, thermal, latency, and failure metrics.',
        'CORS, CSP, TLS, dependency, container, and penetration-testing controls verified.',
        'Monitoring and alerting avoid private payload capture and are tested under failure injection.',
        'Retention, deletion, incident response, backup/restore, and user-rights procedures approved.',
        'Legal/compliance review completed for each target jurisdiction and use case.',
        'Release manifest signed; deployed WASM, zkey, and verification key match it.',
        'User-facing copy states capabilities, assumptions, and limitations accurately.',
    ]
    for item in checklist:
        para = doc.add_paragraph()
        para.paragraph_format.left_indent = Inches(0.05)
        para.paragraph_format.space_after = Pt(5)
        box = para.add_run('☐  ')
        set_run_font(box, size=11, color=ROSE, bold=True)
        text = para.add_run(item)
        set_run_font(text, size=10.2)

    chapter(doc, 'E', 'Source-of-truth index', 'The implementation files a reviewer should inspect first.', 'appe', 205)
    table(doc, ['Question', 'Primary source'], [
        ['What relation is proved?', 'circuits/age_check.circom'],
        ['How are artifacts generated?', 'circuits/setup.sh'],
        ['Which adversarial cases are tested?', 'circuits/smoke_test.mjs and backend/test_main.py'],
        ['How are performance values measured?', 'circuits/benchmark.mjs'],
        ['How is the proof created locally?', 'frontend/lib/zkProver.ts'],
        ['When is the witness cleared?', 'frontend/components/ProofDemo.tsx'],
        ['What body is sent?', 'frontend/lib/verifyProof.ts'],
        ['How is anonymous auth configured?', 'frontend/lib/supabaseClient.ts'],
        ['What does the API accept and enforce?', 'backend/main.py'],
        ['How is SnarkJS isolated?', 'backend/verify.mjs and backend/Dockerfile'],
        ['What is stored?', 'supabase/schema.sql'],
        ['What does the live end-to-end test cover?', 'backend/live_integration_test.mjs'],
        ['What are known limitations and setup steps?', 'README.md, /whitepaper, /docs, /faq'],
    ], [4200, 5160], caption='Implementation evidence index', small=True)
    heading(doc, 'Final perspective', 2)
    p(doc, 'Qyvox already demonstrates the most important architectural inversion: the sensitive witness stays on the user side while the verifier receives a proof of the policy fact. The engineering baseline is credible because the circuit, proof generation, strict API, replay store, receipt schema, and execution trace can be inspected and tested. Its next stage is equally clear: add issuer-backed provenance, exact-date policy, cryptographic freshness, an independent ceremony, hardened operations, and external audit without surrendering the proof-only server boundary.')
    callout(doc, 'Qyvox', 'Prove the fact. Keep the data.', 'privacy')


def main():
    make_diagrams()
    doc = Document()
    bullet_id, decimal_id = configure_document(doc)
    add_cover(doc)
    chapters = [
        ('I', 'Understanding the problem', [('01', 'Executive overview', 'ch01'), ('02', 'The identity-data problem', 'ch02'), ('03', 'What Qyvox proves', 'ch03'), ('04', 'What Qyvox does not prove', 'ch04')]),
        ('II', 'Zero knowledge from first principles', [('05', 'A zero-knowledge mental model', 'ch05'), ('06', 'Arithmetic circuits and R1CS', 'ch06'), ('07', 'Groth16 lifecycle', 'ch07'), ('08', 'Trusted setup and security assumptions', 'ch08')]),
        ('III', 'The Qyvox circuit', [('09', 'Circuit specification', 'ch09'), ('10', 'Line-by-line circuit walkthrough', 'ch10'), ('11', 'Boundary conditions and negative tests', 'ch11'), ('12', 'Artifacts and version binding', 'ch12')]),
        ('IV', 'Browser proving and user experience', [('13', 'Frontend architecture', 'ch13'), ('14', 'Private input lifecycle', 'ch14'), ('15', 'Proof generation in the browser', 'ch15'), ('16', 'Execution receipt and developer playground', 'ch16')]),
        ('V', 'API, authentication, and persistence', [('17', 'API contract', 'ch17'), ('18', 'Authentication and authorization', 'ch18'), ('19', 'Verification pipeline', 'ch19'), ('20', 'Replay protection', 'ch20'), ('21', 'Database schema and row-level security', 'ch21'), ('22', 'Status, CORS, and failure semantics', 'ch22')]),
        ('VI', 'Security model and production hardening', [('23', 'Threat model', 'ch23'), ('24', 'Attack analysis and current controls', 'ch24'), ('25', 'Secrets, dependencies, and supply-chain security', 'ch25'), ('26', 'Privacy, governance, and compliance posture', 'ch26'), ('27', 'Production architecture roadmap', 'ch27')]),
        ('VII', 'Build, run, test, and operate', [('28', 'Repository map', 'ch28'), ('29', 'Local setup and first proof', 'ch29'), ('30', 'Configuration reference', 'ch30'), ('31', 'Testing and validation', 'ch31'), ('32', 'Deployment, observability, and incident response', 'ch32'), ('33', 'Troubleshooting', 'ch33')]),
        ('VIII', 'Product, business, and research strategy', [('34', 'Product and business value', 'ch34'), ('35', 'Enterprise adoption and integration', 'ch35'), ('36', 'Research and benchmarking program', 'ch36'), ('37', 'Open source, auditability, and trust', 'ch37')]),
        ('IX', 'Reference appendices', [('A', 'API examples', 'appa'), ('B', 'Glossary', 'appb'), ('C', 'Frequently asked questions', 'appc'), ('D', 'Release and audit checklist', 'appd'), ('E', 'Source-of-truth index', 'appe')]),
    ]
    add_front_matter(doc, bullet_id, decimal_id, chapters)
    add_part_one(doc, bullet_id, decimal_id)
    add_part_two(doc, bullet_id, decimal_id)
    add_part_three(doc, bullet_id, decimal_id)
    add_part_four(doc, bullet_id, decimal_id)
    add_part_five(doc, bullet_id, decimal_id)
    add_part_six(doc, bullet_id, decimal_id)
    add_part_seven(doc, bullet_id, decimal_id)
    add_part_eight(doc, bullet_id, decimal_id)
    add_appendices(doc, bullet_id, decimal_id)

    # Preserve link/bookmark updates and pagination when Word opens the file.
    settings = doc.settings.element
    update_fields = settings.find(qn('w:updateFields'))
    if update_fields is None:
        update_fields = OxmlElement('w:updateFields')
        settings.append(update_fields)
    update_fields.set(qn('w:val'), 'true')

    OUT_DOCX.parent.mkdir(parents=True, exist_ok=True)
    doc.save(OUT_DOCX)
    payload = OUT_DOCX.read_bytes()
    print(json.dumps({
        'docx': str(OUT_DOCX),
        'bytes': len(payload),
        'sha256': hashlib.sha256(payload).hexdigest(),
        'paragraphs': len(doc.paragraphs),
        'tables': len(doc.tables),
        'inline_shapes': len(doc.inline_shapes),
    }, indent=2))


if __name__ == '__main__':
    main()
