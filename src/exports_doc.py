"""Export générique d'un rapport en HTML, PDF, Word (.docx) et CSV (zip).

Un rapport est une liste de blocs :
    ("h1", "Titre")              ("h2", "Sous-titre")
    ("p", "Texte avec **gras**") ("ul", ["point 1", "point 2"])
    ("note", "Encadré")          ("table", DataFrame)          ("img", png_bytes, "légende")
Les mêmes blocs produisent les quatre formats : le contenu est identique partout.
"""
from __future__ import annotations

import base64
import html as H
import io
import re
import zipfile
from datetime import date

import pandas as pd

from src.rapports import RapportPDF

BLEU, ROUGE = "#00209F", "#D21034"


def _gras_html(t: str) -> str:
    return re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", H.escape(t))


def _sans_gras(t: str) -> str:
    return re.sub(r"\*\*(.+?)\*\*", r"\1", str(t))


# ------------------------------------------------------------------ HTML
def to_html(titre: str, sous_titre: str, blocs: list, sources: str = "", extra_html: str = "") -> str:
    corps = []
    for b in blocs:
        k = b[0]
        if k == "h1":
            corps.append(f"<h2>{H.escape(b[1])}</h2>")
        elif k == "h2":
            corps.append(f"<h3>{H.escape(b[1])}</h3>")
        elif k == "p":
            corps.append(f"<p>{_gras_html(b[1])}</p>")
        elif k == "note":
            corps.append(f"<div class='note'>{_gras_html(b[1])}</div>")
        elif k == "ul":
            corps.append("<ul>" + "".join(f"<li>{_gras_html(x)}</li>" for x in b[1]) + "</ul>")
        elif k == "table":
            df = b[1]
            corps.append("<div class='tw'>" + df.to_html(index=False, escape=True, border=0, classes="t", na_rep="") + "</div>")
        elif k == "img":
            cap = f"<figcaption>{H.escape(b[2])}</figcaption>" if len(b) > 2 and b[2] else ""
            corps.append(f"<figure><img alt='' src='data:image/png;base64,{base64.b64encode(b[1]).decode()}'/>{cap}</figure>")
        elif k == "html":
            corps.append(b[1])
    src = f"<footer>Sources : {H.escape(sources)}</footer>" if sources else ""
    return f"""<!doctype html><html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>{H.escape(titre)}</title>
<style>
:root{{--ink:#0b0b0b;--ink2:#52514e;--bg:#fcfcfb;--line:#e6e5e0;--card:#fff;--note:#f5f7ff}}
@media (prefers-color-scheme:dark){{:root{{--ink:#f0efec;--ink2:#c3c2b7;--bg:#141413;--line:#383835;--card:#1f1f1d;--note:#1b2140}}}}
*{{box-sizing:border-box}} body{{margin:0;background:var(--bg);color:var(--ink);font:16px/1.55 'Source Sans 3',Arial,sans-serif}}
.band{{height:6px;background:linear-gradient(90deg,{BLEU} 0 50%,{ROUGE} 50% 100%)}}
main{{max-width:1080px;margin:0 auto;padding:24px 16px 48px}}
h1{{font-family:Fraunces,Georgia,serif;font-size:2.1rem;margin:.6rem 0 .2rem;line-height:1.1}}
.sub{{color:var(--ink2);margin:0 0 1.4rem}} h2{{font-family:Fraunces,Georgia,serif;color:{BLEU};margin:2rem 0 .6rem;border-bottom:1px solid var(--line);padding-bottom:.3rem}}
@media (prefers-color-scheme:dark){{h2{{color:#9ec5f4}}}}
h3{{margin:1.3rem 0 .4rem}} .note{{background:var(--note);border-left:4px solid {BLEU};padding:.7rem 1rem;border-radius:0 10px 10px 0;margin:.6rem 0}}
.tw{{overflow-x:auto;margin:.5rem 0 1rem}} table.t{{border-collapse:collapse;width:100%;font-size:.88rem;background:var(--card)}}
table.t th{{background:{BLEU};color:#fff;text-align:left;padding:.45rem .5rem;position:sticky;top:0}}
table.t td{{border-bottom:1px solid var(--line);padding:.4rem .5rem;vertical-align:top}}
figure{{margin:1rem 0}} figure img{{max-width:100%;border:1px solid var(--line);border-radius:10px;background:#fff}}
figcaption{{color:var(--ink2);font-size:.85rem}} footer{{margin-top:2.5rem;color:var(--ink2);font-size:.82rem;border-top:1px solid var(--line);padding-top:.8rem}}
</style></head><body><div class="band"></div><main>
<div style="color:{ROUGE};font-weight:700;letter-spacing:.12em;font-size:.78rem;text-transform:uppercase">Ayiti Data Hub · {date.today():%d/%m/%Y}</div>
<h1>{H.escape(titre)}</h1><p class="sub">{H.escape(sous_titre)}</p>
{extra_html}{''.join(corps)}{src}</main></body></html>"""


# ------------------------------------------------------------------ PDF
class _PDF(RapportPDF):
    def titre_niv(self, t: str, taille: int = 15, couleur=(0, 32, 159)):
        if self.get_y() > 250:
            self.add_page()
        self.ln(3)
        self.set_font("DV", "B", taille)
        self.set_text_color(*couleur)
        self.multi_cell(0, taille * 0.5, t)
        self.ln(1.5)

    def texte(self, t: str, puce: bool = False):
        self.set_font("DV", "", 9.5)
        self.set_text_color(40, 40, 40)
        t = _sans_gras(t)
        if puce:
            self.set_x(20)
            self.multi_cell(174, 5, "• " + t)
        else:
            self.multi_cell(0, 5, t)
        self.ln(1)

    def tableau(self, df: pd.DataFrame):
        df = df.fillna("").astype(str)
        n = len(df.columns)
        taille = 8 if n <= 4 else 7 if n <= 6 else 6
        self.set_font("DV", "", taille)
        self.set_text_color(30, 30, 30)
        self.set_fill_color(255, 255, 255)
        self.set_draw_color(220, 220, 215)
        larg = [max(14, min(60, df[c].str.len().clip(upper=120).mean() + len(c) * 0.4)) for c in df.columns]
        tot = sum(larg)
        larg = [w / tot * 178 for w in larg]
        with self.table(col_widths=larg, text_align="LEFT", line_height=taille * 0.48, first_row_as_headings=True,
                        headings_style=__import__("fpdf").fonts.FontFace(emphasis="BOLD", color=(255, 255, 255), fill_color=(0, 32, 159)),
                        borders_layout="HORIZONTAL_LINES", cell_fill_color=(245, 247, 255), cell_fill_mode="ROWS") as tb:
            tb.row(list(df.columns))
            for r in df.itertuples(index=False):
                tb.row([str(x)[:400] for x in r])
        self.ln(3)


def to_pdf(titre: str, sous_titre: str, blocs: list, sources: str = "", couverture_img: bytes | None = None) -> bytes:
    pdf = _PDF(titre)
    pdf.couverture(sous_titre, image=couverture_img)
    pdf.add_page()
    for b in blocs:
        k = b[0]
        if k == "h1":
            pdf.titre_niv(b[1], 15)
        elif k == "h2":
            pdf.titre_niv(b[1], 11.5, (11, 11, 11))
        elif k in ("p", "note"):
            pdf.texte(b[1])
        elif k == "ul":
            for x in b[1]:
                pdf.texte(x, puce=True)
        elif k == "table":
            pdf.tableau(b[1])
        elif k == "img":
            if pdf.get_y() > 170:
                pdf.add_page()
            pdf.image(io.BytesIO(b[1]), x=16, w=178)
            if len(b) > 2 and b[2]:
                pdf.set_font("DV", "I", 8)
                pdf.set_text_color(120, 120, 120)
                pdf.multi_cell(0, 4, b[2])
            pdf.ln(2)
    if sources:
        pdf.ln(4)
        pdf.set_font("DV", "", 8)
        pdf.set_text_color(120, 120, 120)
        pdf.multi_cell(0, 4, "Sources : " + sources)
    return bytes(pdf.output())


# ------------------------------------------------------------------ Word
def to_docx(titre: str, sous_titre: str, blocs: list, sources: str = "") -> bytes:
    from docx import Document
    from docx.enum.section import WD_ORIENT  # noqa: F401
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    from docx.shared import Cm, Pt, RGBColor

    doc = Document()
    sec = doc.sections[0]
    sec.left_margin = sec.right_margin = Cm(1.8)
    st_ = doc.styles["Normal"]
    st_.font.name = "Calibri"
    st_.font.size = Pt(10.5)
    for niv, coul in (("Heading 1", RGBColor(0, 32, 159)), ("Heading 2", RGBColor(11, 11, 11)), ("Title", RGBColor(11, 11, 11))):
        doc.styles[niv].font.color.rgb = coul

    def runs(par, t):
        for i, morceau in enumerate(re.split(r"\*\*(.+?)\*\*", str(t))):
            if morceau:
                r = par.add_run(morceau)
                r.bold = i % 2 == 1

    doc.add_paragraph().add_run(f"AYITI DATA HUB · {date.today():%d/%m/%Y}").font.color.rgb = RGBColor(210, 16, 52)
    doc.add_heading(titre, 0)
    p = doc.add_paragraph(sous_titre)
    p.runs[0].italic = True
    for b in blocs:
        k = b[0]
        if k == "h1":
            doc.add_heading(b[1], 1)
        elif k == "h2":
            doc.add_heading(b[1], 2)
        elif k == "p":
            runs(doc.add_paragraph(), b[1])
        elif k == "note":
            par = doc.add_paragraph()
            runs(par, b[1])
            par.paragraph_format.left_indent = Cm(0.6)
            for r in par.runs:
                r.font.color.rgb = RGBColor(31, 42, 85)
        elif k == "ul":
            for x in b[1]:
                runs(doc.add_paragraph(style="List Bullet"), x)
        elif k == "table":
            df = b[1].fillna("").astype(str)
            t = doc.add_table(rows=1, cols=len(df.columns))
            t.style = "Light Grid Accent 1"
            for j, c in enumerate(df.columns):
                cell = t.rows[0].cells[j]
                cell.text = str(c)
                cell.paragraphs[0].runs[0].bold = True
                sh = OxmlElement("w:shd")
                sh.set(qn("w:fill"), "00209F")
                cell._tc.get_or_add_tcPr().append(sh)
                cell.paragraphs[0].runs[0].font.color.rgb = RGBColor(255, 255, 255)
            for r in df.itertuples(index=False):
                cells = t.add_row().cells
                for j, v in enumerate(r):
                    cells[j].text = str(v)
            for row in t.rows:
                for cell in row.cells:
                    for par in cell.paragraphs:
                        for run in par.runs:
                            run.font.size = Pt(8 if len(df.columns) > 4 else 9)
            doc.add_paragraph()
        elif k == "img":
            doc.add_picture(io.BytesIO(b[1]), width=Cm(17))
            if len(b) > 2 and b[2]:
                c = doc.add_paragraph(b[2])
                c.runs[0].italic = True
                c.runs[0].font.size = Pt(8.5)
    if sources:
        s = doc.add_paragraph("Sources : " + sources)
        s.runs[0].font.size = Pt(8.5)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


# ------------------------------------------------------------------ CSV (zip)
def to_csv_zip(tables: dict[str, pd.DataFrame]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for nom, df in tables.items():
            z.writestr(f"{nom}.csv", df.to_csv(index=False).encode("utf-8-sig"))
    return buf.getvalue()


# ------------------------------------------------------------------ Streamlit
def panneau_exports(cle: str, titre: str, sous_titre: str, fabrique, tables: dict[str, pd.DataFrame], sources: str = "",
                    couverture=None, extra_html: str = "") -> None:
    """Bouton « Préparer » puis 4 téléchargements (HTML, CSV, PDF, Word).

    `fabrique` est une fonction sans argument qui renvoie la liste de blocs (appelée seulement au clic,
    pour ne pas recalculer graphiques et PDF à chaque interaction).
    """
    import streamlit as st

    nom = re.sub(r"[^a-z0-9]+", "_", titre.lower().encode("ascii", "ignore").decode()).strip("_")[:50]
    etat = f"_exp_{cle}"
    if st.button("⚙️ Préparer les exports (HTML, CSV, PDF, Word)", key=f"btn_{cle}", type="primary"):
        with st.spinner("Génération des documents…"):
            blocs = fabrique()
            img = couverture() if callable(couverture) else couverture
            st.session_state[etat] = {
                "html": to_html(titre, sous_titre, blocs, sources, extra_html).encode("utf-8"),
                "pdf": to_pdf(titre, sous_titre, blocs, sources, img),
                "docx": to_docx(titre, sous_titre, blocs, sources),
                "csv": to_csv_zip(tables),
            }
    f = st.session_state.get(etat)
    if f:
        c1, c2, c3, c4 = st.columns(4)
        c1.download_button("🌐 HTML", f["html"], f"{nom}.html", "text/html", key=f"h_{cle}", use_container_width=True)
        c2.download_button("📊 CSV (zip)", f["csv"], f"{nom}_donnees.zip", "application/zip", key=f"c_{cle}", use_container_width=True)
        c3.download_button("📄 PDF", f["pdf"], f"{nom}.pdf", "application/pdf", key=f"p_{cle}", use_container_width=True)
        c4.download_button("📝 Word", f["docx"], f"{nom}.docx",
                           "application/vnd.openxmlformats-officedocument.wordprocessingml.document", key=f"w_{cle}",
                           use_container_width=True)
