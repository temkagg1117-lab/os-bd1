#!/usr/bin/env python3
"""Generate the BD2 Final Report, Manual and one-page Poster PDFs.

Requirements: pip install reportlab 'qrcode[pil]' ; DejaVuSans TTF fonts.
Screenshot evidence is an actual program screenshot (MOCK, not kernel proof).
Release QR defaults to the *repository* until a verified release URL is supplied.
"""
import argparse
import os
import re
import textwrap
from pathlib import Path
from xml.sax.saxutils import escape

import qrcode
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4, landscape, A3
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle,
    KeepTogether, Image, Preformatted, HRFlowable,
)

DOCS = Path(__file__).resolve().parent
REPO_URL = "https://github.com/temkagg1117-lab/os-bd1"
C_NAVY = colors.HexColor("#12243d")
C_BLUE = colors.HexColor("#376fae")
C_AMBER = colors.HexColor("#dca544")
C_TEXT = colors.HexColor("#1e314b")
C_GREY = colors.HexColor("#62778e")
C_PALE = colors.HexColor("#f0f5fa")


def fonts():
    choices = [os.environ.get("BD2_FONT_DIR"),
               "/usr/share/fonts/truetype/dejavu", "/usr/local/share/fonts", "/Library/Fonts"]
    for folder in filter(None, choices):
        base = Path(folder)
        if all((base / name).exists() for name in ("DejaVuSans.ttf", "DejaVuSans-Bold.ttf", "DejaVuSansMono.ttf")):
            pdfmetrics.registerFont(TTFont("BD2", str(base / "DejaVuSans.ttf")))
            pdfmetrics.registerFont(TTFont("BD2B", str(base / "DejaVuSans-Bold.ttf")))
            pdfmetrics.registerFont(TTFont("BD2Mono", str(base / "DejaVuSansMono.ttf")))
            pdfmetrics.registerFontFamily("BD2", normal="BD2", bold="BD2B", italic="BD2", boldItalic="BD2B")
            return
    raise FileNotFoundError("DejaVuSans fonts missing. Set BD2_FONT_DIR or install fonts-dejavu-core.")


S_BODY = None
S_SMALL = None
S_H1 = None
S_H2 = None
S_C = None
S_CODE = None


def styles():
    global S_BODY, S_SMALL, S_H1, S_H2, S_C, S_CODE
    S_BODY = ParagraphStyle("body", fontName="BD2", fontSize=9, leading=13.8, textColor=C_TEXT, spaceAfter=6)
    S_SMALL = ParagraphStyle("small", parent=S_BODY, fontSize=7.4, leading=10.6, spaceAfter=3)
    S_H1 = ParagraphStyle("h1", parent=S_BODY, fontName="BD2B", fontSize=14, leading=19,
                          textColor=C_NAVY, spaceBefore=12, spaceAfter=8, keepWithNext=True)
    S_H2 = ParagraphStyle("h2", parent=S_BODY, fontName="BD2B", fontSize=10.7, leading=14.8,
                          textColor=C_BLUE, spaceBefore=8, spaceAfter=5, keepWithNext=True)
    S_C = ParagraphStyle("center", parent=S_BODY, alignment=TA_CENTER)
    S_CODE = ParagraphStyle("code", fontName="BD2Mono", fontSize=7.0, leading=10,
                            backColor=C_PALE, leftIndent=5, rightIndent=5, spaceBefore=4, spaceAfter=8)


def fmt_inline(t):
    t = escape(str(t), {'"': '&quot;'})
    t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)
    t = re.sub(r"`([^`]+)`", r'<font name="BD2Mono" size="7.8">\1</font>', t)
    t = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'\1 (\2)', t)
    return t


def parsed_md(path, include_image=False):
    rows = []
    lines = path.read_text(encoding='utf-8').splitlines()
    output = []
    paragraph = []
    in_code = False
    code_lines = []
    inserted_image = False
    
    def flush():
        if paragraph:
            txt = " ".join(x.strip() for x in paragraph).strip()
            if txt:
                output.append(Paragraph(fmt_inline(txt), S_BODY))
            paragraph.clear()

    def flush_table():
        nonlocal rows
        if not rows:
            return
        if len(rows) > 1 and all(re.fullmatch(r"[:\- ]+", v) for v in rows[1]):
            rows.pop(1)
        n = len(rows[0])
        usable = 170 * mm
        if n == 3:
            fractions = [.22, .35, .43]
        elif n == 2:
            fractions = [.34, .66]
        else:
            fractions = [1/n] * n
        data = [[Paragraph(fmt_inline(cell), S_SMALL) for cell in row] for row in rows]
        header_style = ParagraphStyle("head", parent=S_SMALL, fontName="BD2B", textColor=colors.white)
        data[0] = [Paragraph(fmt_inline(cell), header_style) for cell in rows[0]]
        t = Table(data, colWidths=[usable*x for x in fractions], hAlign="LEFT", repeatRows=1)
        t.setStyle(TableStyle([
            ("VALIGN", (0,0), (-1,-1), "TOP"), ("BACKGROUND", (0,0), (-1,0), C_NAVY),
            ("TEXTCOLOR", (0,0), (-1,0), colors.white),
            ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, C_PALE]),
            ("LINEBELOW", (0,-1), (-1,-1), .6, C_BLUE),
            ("LEFTPADDING", (0,0), (-1,-1), 6), ("RIGHTPADDING", (0,0), (-1,-1), 6),
            ("TOPPADDING", (0,0), (-1,-1), 6), ("BOTTOMPADDING", (0,0), (-1,-1), 5),
        ]))
        output.append(t)
        output.append(Spacer(1, 3*mm))
        rows = []

    for line in lines:
        if line.startswith('```'):
            flush();flush_table()
            if in_code:
                # Wrap long terminal/command lines, no invented output.
                value = '\n'.join(textwrap.shorten(l, width=96, placeholder=' ...') if len(l)>96 else l for l in code_lines)
                output.append(Preformatted(value or ' ', S_CODE, maxLineLength=96, splitChars=' /'))
                in_code = False;code_lines=[]
            else:
                in_code=True
            continue
        if in_code:
            code_lines.append(line)
            continue
        if line.startswith('|') and line.endswith('|'):
            flush()
            rows.append([x.strip() for x in line.strip('|').split('|')])
            continue
        flush_table()
        if not line.strip():
            flush()
            continue
        if line.startswith('# '):
            flush()
            # Cover created separately; skip duplicate full-page document title.
            if output:
                output.append(Paragraph(fmt_inline(line[2:]), S_H1))
            continue
        if line.startswith('## '):
            flush()
            title = line[3:].strip()
            output.append(Paragraph(fmt_inline(title), S_H1))
            if include_image and not inserted_image and title.startswith('3. Туршилт'):
                img = DOCS / 'evidence/real_mock_ui.png'
                if img.exists():
                    output.append(Paragraph('Бодит ажиллуулалтын зураг — Linux /proc MOCK mode (kernel module биш)', S_SMALL))
                    output.append(Image(str(img), width=156*mm, height=122*mm, hAlign='CENTER'))
                    output.append(Spacer(1, 5*mm))
                    inserted_image=True
            continue
        if line.startswith('### '):
            flush();output.append(Paragraph(fmt_inline(line[4:]), S_H2));continue
        if re.match(r'^\d+\.\s', line) or line.startswith('- '):
            flush()
            output.append(Paragraph(fmt_inline('• ' + re.sub(r'^\d+\.\s|^-\s', '', line)), S_BODY))
            continue
        paragraph.append(line)
    flush();flush_table()
    return output


def doc_footer(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(C_BLUE)
    canvas.setLineWidth(.4)
    canvas.line(20*mm, 15*mm, 190*mm, 15*mm)
    canvas.setFont("BD2", 7)
    canvas.setFillColor(C_GREY)
    canvas.drawString(20*mm, 10*mm, "F.CSM302 · БД2 · Baseline 0cb46da · MOCK test != kernel proof")
    canvas.drawRightString(190*mm, 10*mm, str(doc.page))
    canvas.restoreState()


def make_document(filename, title, subtitle, markdown, with_image=False):
    out = DOCS / filename
    story = [Spacer(1, 34*mm), Paragraph('F.CSM302 ҮЙЛДЛИЙН СИСТЕМ · БИЕ ДААЛТ 2', S_C),
             Spacer(1, 10*mm),
             Paragraph(f'<font name="BD2B" size="21" color="#12243d">{fmt_inline(title)}</font>', S_C),
             Spacer(1, 6*mm), Paragraph(fmt_inline(subtitle), S_C), Spacer(1, 12*mm),
             Paragraph('Linux Kernel Module for Task Information', S_C),
             Spacer(1, 8*mm),
             Paragraph('Repository: ' + fmt_inline(REPO_URL), S_C),
             Paragraph('2026-11-21 · <b>Kernel VM regression: NOT VERIFIED</b>', S_C),
             Spacer(1, 10*mm),
             Paragraph('БД2 source package: Python backend + SVG UI + 21 mock tests + review responses', S_C),
             PageBreak()]
    story.extend(parsed_md(DOCS/markdown, include_image=with_image))
    SimpleDocTemplate(str(out), pagesize=A4, leftMargin=20*mm, rightMargin=20*mm,
                      topMargin=19*mm, bottomMargin=22*mm, title=title,
                      author="F.CSM302 Task Hierarchy Team").build(story, onFirstPage=doc_footer, onLaterPages=doc_footer)
    return out


def rounded_text(c, x, y, text, font='BD2', size=12, color=colors.white):
    c.setFont(font, size);c.setFillColor(color);c.drawString(x,y,text)


def make_poster(release_url=None):
    # A3 landscape: one readable page with actual screenshot and a QR.
    W, H = landscape(A3)
    out = DOCS/'BD2_Poster.pdf'
    c = __import__('reportlab').pdfgen.canvas.Canvas(str(out), pagesize=(W,H), pageCompression=1)
    c.setTitle('F.CSM302 BD2 Poster - Task Hierarchy')
    c.setFillColor(colors.white);c.rect(0,0,W,H,fill=1,stroke=0)
    c.setFillColor(C_NAVY);c.rect(0,H-72*mm,W,72*mm,fill=1,stroke=0)
    rounded_text(c,20*mm,H-22*mm,'TASK HIERARCHY', 'BD2B', 28)
    rounded_text(c,20*mm,H-35*mm,'Linux Kernel Module for Task Information', 'BD2', 15)
    rounded_text(c,20*mm,H-48*mm,'F.CSM302  •  Бие даалт 2  •  6 гишүүн', 'BD2', 12)
    rounded_text(c,20*mm,H-61*mm,'/proc/pid   →   Python API   →   SVG Process Tree', 'BD2Mono', 12)
    # Code and all six members are required by BD2 poster guide.
    rounded_text(c,231*mm,H-25*mm,'Код: II-4-2  (багшаар баталгаажуулах)', 'BD2B', 10)
    rounded_text(c,231*mm,H-35*mm,'Багийн гишүүд:', 'BD2B', 10)
    rounded_text(c,231*mm,H-44*mm,'Тэмүүжин B242270046  ·  Цогтбаяр B242270133',size=8.3)
    rounded_text(c,231*mm,H-53*mm,'Бямбасүрэн B241940082  ·  Ганболд B241910023',size=8.3)
    rounded_text(c,231*mm,H-62*mm,'Гантүшиг B231940130  ·  Гантулга B190910023',size=8.3)

    def box(x,y,w,h,title):
        c.setFillColor(C_PALE);c.roundRect(x,y,w,h,10*mm,fill=1,stroke=0)
        c.setFillColor(C_NAVY);c.setFont('BD2B',13);c.drawString(x+9*mm,y+h-15*mm,title)

    left, mid, right = 20*mm, 192*mm, 335*mm
    box(left,H-146*mm,162*mm,64*mm,'01  АСУУДАЛ')
    for j,line in enumerate(['Linux task_struct мэдээллийг', 'PID-аар kernel-ээс уншиж,', 'parent / child хэлбэрээр', 'бодитоор дүрслэх.']):
        rounded_text(c,left+10*mm,H-109*mm-j*9*mm,line,size=11,color=C_TEXT)
    box(left,H-220*mm,162*mm,65*mm,'02  ШИЙДЭЛ')
    for j,line in enumerate(['Kernel: ti_main.c + ti_walk.c', 'Service: strict Python parser', 'UI: responsive SVG process tree', 'Test: Linux /proc MOCK + VM plan']):
        rounded_text(c,left+10*mm,H-183*mm-j*9*mm,line,size=10.3,color=C_TEXT)
    box(left,H-272*mm,162*mm,42*mm,'03  REVIEW-ЭЭС САЙЖРУУЛСАН')
    for j,line in enumerate(['•  Input validation / BAD_OUTPUT', '•  Static path traversal хамгаалалт', '•  Demo group limit & cleanup']):
        rounded_text(c,left+9*mm,H-250*mm-j*8.5*mm,line,size=9.5,color=C_TEXT)
    # Screenshot on the right: actual app captured under Linux /proc mock.
    img = DOCS/'evidence/real_mock_ui.png'
    c.setFillColor(C_NAVY);c.setFont('BD2B',13);c.drawString(mid,H-90*mm,'04  БОДИТ UI SCREENSHOT')
    imgw, imgh = 193*mm, 145*mm
    c.drawImage(str(img),mid,H-95*mm-imgh,imgw,imgh,preserveAspectRatio=True,anchor='c',mask='auto')
    c.setFont('BD2',9);c.setFillColor(C_GREY)
    c.drawString(mid,H-244*mm,'Screenshot: running backend, Linux /proc-based MOCK (kernel биш)')
    # Metrics and QR lower band
    c.setFillColor(C_AMBER);c.roundRect(mid,H-275*mm,88*mm,18*mm,5*mm,fill=1,stroke=0)
    rounded_text(c,mid+7*mm,H-268*mm,'21 / 21  MOCK TEST PASS','BD2B',12,C_NAVY)
    link = release_url or REPO_URL
    qr = qrcode.QRCode(border=2,box_size=6,error_correction=qrcode.constants.ERROR_CORRECT_M)
    qr.add_data(link);qr.make(fit=True)
    import tempfile
    with tempfile.TemporaryDirectory() as temp:
        path = str(Path(temp)/'qr.png');qr.make_image(fill_color='#12243d',back_color='white').save(path)
        c.drawImage(path,340*mm,H-278*mm,35*mm,35*mm,mask='auto')
    c.setFillColor(C_TEXT);c.setFont('BD2B',9)
    c.drawString(377*mm,H-256*mm,'GitHub QR' if not release_url else 'Final Release QR')
    c.setFont('BD2',7.5)
    c.drawString(377*mm,H-265*mm,'REPO (release pending)' if not release_url else 'verified release URL')
    c.setStrokeColor(C_BLUE);c.line(20*mm,16*mm,W-20*mm,16*mm)
    c.setFillColor(C_GREY);c.setFont('BD2',8)
    c.drawString(20*mm,10*mm,'Kernel module regression / official peer-review PDF / final tag: NOT VERIFIED')
    c.save()
    return out


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--release-url',default=None,help='Use ONLY after published, verified GitHub Release exists')
    a=ap.parse_args()
    fonts();styles()
    result=[
        make_document('BD2_Final_Report.pdf','БД2 · ЭЦСИЙН ТАЙЛАН','Сайжруулалт, review responses, regression ба бодит нотолгоо','BD2_Final_Report.md',True),
        make_document('BD2_Manual.pdf','БД2 · АШИГЛАХ ЗААВАР','Dependency • Quick Start • Build / Run • Regression','BD2_Manual.md'),
        make_poster(a.release_url),
    ]
    for path in result:print(path.name,path.stat().st_size,'bytes')

if __name__=='__main__':main()
