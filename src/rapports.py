"""Génération de rapports PDF (fpdf2) et d'images PNG (matplotlib) sur tous les aspects de la plateforme.

Les graphiques sont dessinés avec matplotlib (fonctionne partout, sans navigateur), avec la même palette
que la plateforme. Chaque section renvoie : titre, liste de paragraphes, liste de figures (PNG en octets).
"""
from __future__ import annotations

import io
import os
import re
from datetime import date

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from fpdf import FPDF  # noqa: E402
from matplotlib.collections import PolyCollection  # noqa: E402

from src.ui import SERIES  # noqa: E402

FONT_DIR = os.path.join(matplotlib.get_data_path(), "fonts", "ttf")
BLEU, ROUGE, INK, INK2, GRID = "#00209F", "#D21034", "#0b0b0b", "#52514e", "#e6e5e0"

plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "axes.edgecolor": GRID, "axes.spines.top": False,
                     "axes.spines.right": False, "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6,
                     "axes.axisbelow": True, "axes.titleweight": "bold", "axes.titlesize": 12,
                     "axes.titlelocation": "left", "xtick.color": INK2, "ytick.color": INK2,
                     "axes.prop_cycle": matplotlib.cycler(color=SERIES)})


def _png(fig) -> bytes:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=170, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return buf.getvalue()


def _sans_gras(t: str) -> str:
    return re.sub(r"\*\*(.+?)\*\*", r"\1", t)


def fmt_fr(x, dec=0):
    if x is None or x != x:
        return "–"
    if abs(x) >= 1e9:
        s = f"{x / 1e9:,.1f} Md"
    elif abs(x) >= 1e6:
        s = f"{x / 1e6:,.2f} M"
    else:
        s = f"{x:,.{dec}f}"
    return s.replace(",", " ").replace(".", ",")


# ------------------------------------------------------------------ figures
def fig_carte(geo: dict, valeurs: dict[str, float] | None = None, titre: str = "", cmap: str = "Blues",
              points: pd.DataFrame | None = None, label: str = "") -> bytes:
    fig, ax = plt.subplots(figsize=(8, 5.6))
    polys, vals = [], []
    for f in geo["features"]:
        g = f["geometry"]
        parts = g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]
        for p in parts:
            polys.append(np.array(p[0]))
            vals.append(valeurs.get(f["id"], np.nan) if valeurs else 0.5)
    v = np.array(vals, dtype=float)
    pc = PolyCollection(polys, edgecolor="white", linewidth=0.4)
    if valeurs:
        pc.set_array(np.ma.masked_invalid(v))
        pc.set_cmap(plt.get_cmap(cmap).copy())
        pc.get_cmap().set_bad("#eeeeee")
    else:
        pc.set_facecolor("#cde2fb")
    ax.add_collection(pc)
    if valeurs:
        cb = fig.colorbar(pc, ax=ax, shrink=0.6, pad=0.01)
        cb.set_label(label, color=INK2)
        cb.outline.set_visible(False)
    if points is not None and len(points):
        for i, (cat, s) in enumerate(points.groupby("categorie")):
            ax.scatter(s.lon, s.lat, s=40, color=SERIES[(i + 1) % 8], edgecolor="white", linewidth=1, label=cat, zorder=3)
        ax.legend(loc="lower left", frameon=True, fontsize=8)
    ax.set_xlim(-74.55, -71.6)
    ax.set_ylim(17.95, 20.15)
    ax.set_aspect(1.05)
    ax.axis("off")
    ax.set_title(titre)
    return _png(fig)


def fig_ligne(series: dict[str, pd.DataFrame], titre: str, unite: str = "", recents: pd.DataFrame | None = None) -> bytes:
    fig, ax = plt.subplots(figsize=(8, 3.6))
    for i, (lab, s) in enumerate(series.items()):
        ax.plot(s.annee, s.valeur, lw=2, color=SERIES[i % 8], label=lab)
    if recents is not None and len(recents):
        ax.plot(recents.annee, recents.valeur, "o--", color=SERIES[1], lw=1.5, ms=6, label="Récent / FMI")
    ax.set_title(titre)
    ax.set_ylabel(unite, color=INK2)
    if len(series) > 1 or recents is not None:
        ax.legend(frameon=False, fontsize=8, loc="best")
    ax.grid(axis="x", visible=False)
    return _png(fig)


def fig_barres(lab: list, val: list, titre: str, unite: str = "", couleur: str = SERIES[0], highlight: str | None = None) -> bytes:
    d = sorted(zip(val, lab))
    fig, ax = plt.subplots(figsize=(8, max(2.6, 0.32 * len(d) + 1)))
    cols = [SERIES[1] if (highlight and l == highlight) else couleur for _, l in d]
    ax.barh([l for _, l in d], [v for v, _ in d], color=cols, height=0.65)
    for i, (v, _) in enumerate(d):
        ax.text(v, i, " " + fmt_fr(v, 1 if v < 100 else 0), va="center", fontsize=8, color=INK2)
    ax.set_title(titre)
    ax.set_xlabel(unite, color=INK2)
    ax.grid(axis="y", visible=False)
    return _png(fig)


def fig_developpement(ind: pd.DataFrame) -> bytes:
    from src.developpement import COULEURS_DIM, DIMENSIONS
    fig, ax = plt.subplots(figsize=(8, 3.8))
    for d in DIMENSIONS:
        if d in ind:
            ax.plot(ind.annee, ind[d], lw=1.3, alpha=0.8, color=COULEURS_DIM[d], label=d)
    ax.plot(ind.annee, ind["Indice global"], lw=3, color=INK, label="Indice global")
    ax.axhspan(66, 100, color="#0ca30c", alpha=0.05)
    ax.axhspan(0, 33, color="#d03b3b", alpha=0.04)
    ax.set_ylim(0, 102)
    ax.set_title("Trajectoire de développement (0 = pire année, 100 = meilleure depuis 1990)")
    ax.legend(frameon=False, fontsize=7, ncol=4, loc="upper center", bbox_to_anchor=(0.5, -0.1))
    return _png(fig)


def infographie(chiffres: list[tuple[str, str, str]], titre: str, sous_titre: str = "") -> bytes:
    """Image de synthèse (format réseaux sociaux 1600x900) : grandes valeurs + libellés."""
    fig = plt.figure(figsize=(16, 9))
    fig.patch.set_facecolor("white")
    ax = fig.add_axes([0, 0, 1, 1])
    ax.axis("off")
    ax.add_patch(plt.Rectangle((0, 0.955), 0.5, 0.045, color=BLEU, transform=ax.transAxes))
    ax.add_patch(plt.Rectangle((0.5, 0.955), 0.5, 0.045, color=ROUGE, transform=ax.transAxes))
    ax.text(0.04, 0.86, titre, fontsize=34, fontweight="bold", color=INK, transform=ax.transAxes)
    ax.text(0.04, 0.80, sous_titre, fontsize=16, color=INK2, transform=ax.transAxes)
    n = len(chiffres)
    cols = 3
    for i, (lab, val, sub) in enumerate(chiffres):
        r, c = divmod(i, cols)
        x, y = 0.04 + c * 0.32, 0.62 - r * 0.27
        ax.add_patch(plt.Rectangle((x, y - 0.12), 0.29, 0.21, fill=False, ec=GRID, lw=1.5, transform=ax.transAxes))
        ax.add_patch(plt.Rectangle((x, y + 0.085), 0.29, 0.007, color=BLEU if i % 2 == 0 else ROUGE, transform=ax.transAxes))
        ax.text(x + 0.015, y + 0.04, lab.upper(), fontsize=12, color=INK2, fontweight="bold", transform=ax.transAxes)
        ax.text(x + 0.015, y - 0.045, val, fontsize=30, color=INK, fontweight="bold", transform=ax.transAxes)
        ax.text(x + 0.015, y - 0.1, sub, fontsize=11, color="#8a8984", transform=ax.transAxes)
    ax.text(0.04, 0.03, f"Ayiti Data Hub · {date.today():%d/%m/%Y} · sources : CNIGS, HDX, Banque mondiale, FMI, IPC, OIM, MENFP",
            fontsize=11, color="#8a8984", transform=ax.transAxes)
    return _png(fig)


# ------------------------------------------------------------------ PDF
class RapportPDF(FPDF):
    def __init__(self, titre: str):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.titre_rapport = titre
        self.add_font("DV", "", os.path.join(FONT_DIR, "DejaVuSans.ttf"))
        self.add_font("DV", "B", os.path.join(FONT_DIR, "DejaVuSans-Bold.ttf"))
        self.add_font("DV", "I", os.path.join(FONT_DIR, "DejaVuSans-Oblique.ttf"))
        self.set_auto_page_break(True, margin=16)
        self.set_margins(16, 16, 16)

    def multi_cell(self, *args, **kwargs):  # retour à la marge gauche après chaque bloc de texte
        kwargs.setdefault("new_x", "LMARGIN")
        kwargs.setdefault("new_y", "NEXT")
        return super().multi_cell(*args, **kwargs)

    def header(self):
        if self.page_no() == 1:
            return
        self.set_fill_color(0, 32, 159)
        self.rect(0, 0, 105, 3, "F")
        self.set_fill_color(210, 16, 52)
        self.rect(105, 0, 105, 3, "F")
        self.set_font("DV", "", 8)
        self.set_text_color(138, 137, 132)
        self.set_y(7)
        self.cell(0, 5, f"Ayiti Data Hub — {self.titre_rapport}", align="L")
        self.ln(8)

    def footer(self):
        self.set_y(-12)
        self.set_font("DV", "", 8)
        self.set_text_color(138, 137, 132)
        self.cell(0, 6, f"Page {self.page_no()} · généré le {date.today():%d/%m/%Y}", align="R")

    def couverture(self, sous_titre: str, image: bytes | None = None, photo: str | None = None):
        self.add_page()
        if photo and os.path.exists(photo):
            self.image(photo, x=0, y=0, w=210, h=120)
        self.set_fill_color(0, 32, 159)
        self.rect(0, 120, 105, 4, "F")
        self.set_fill_color(210, 16, 52)
        self.rect(105, 120, 105, 4, "F")
        self.set_y(132)
        self.set_font("DV", "B", 26)
        self.set_text_color(11, 11, 11)
        self.multi_cell(0, 12, self.titre_rapport)
        self.set_font("DV", "", 13)
        self.set_text_color(82, 81, 78)
        self.multi_cell(0, 7, sous_titre)
        self.ln(4)
        if image:
            self.image(io.BytesIO(image), x=30, w=150)
        self.set_y(-30)
        self.set_font("DV", "", 9)
        self.multi_cell(0, 5, f"Ayiti Data Hub · {date.today():%d %B %Y} · Données : CNIGS, HDX/OCHA, Banque mondiale, FMI, "
                              "IPC, OIM, MENFP, OpenStreetMap, UNESCO, médias haïtiens.")

    def section(self, titre: str):
        self.add_page()
        self.set_font("DV", "B", 17)
        self.set_text_color(0, 32, 159)
        self.multi_cell(0, 9, titre)
        self.set_draw_color(230, 229, 224)
        self.line(16, self.get_y() + 1, 194, self.get_y() + 1)
        self.ln(5)

    def paragraphe(self, txt: str, puce: bool = False):
        self.set_font("DV", "", 10)
        self.set_text_color(40, 40, 40)
        txt = _sans_gras(txt)
        self.set_x(self.l_margin)
        if puce:
            self.set_x(20)
            self.multi_cell(174, 5.4, "• " + txt)
        else:
            self.multi_cell(0, 5.4, txt)
        self.ln(1.2)

    def chiffres(self, items: list[tuple[str, str]]):
        w = (210 - 32) / 3
        self.set_text_color(11, 11, 11)
        for i, (lab, val) in enumerate(items):
            if i % 3 == 0:
                y = self.get_y()
                if y > 255:
                    self.add_page()
                    y = self.get_y()
            x = 16 + (i % 3) * w
            self.set_xy(x, y)
            self.set_draw_color(230, 229, 224)
            self.rect(x, y, w - 3, 20)
            self.set_xy(x + 2, y + 2)
            self.set_font("DV", "", 7.5)
            self.set_text_color(82, 81, 78)
            self.cell(w - 6, 4, lab.upper())
            self.set_xy(x + 2, y + 8)
            self.set_font("DV", "B", 14)
            self.set_text_color(11, 11, 11)
            self.cell(w - 6, 8, val)
            if i % 3 == 2 or i == len(items) - 1:
                self.set_y(y + 23)
        self.ln(2)

    def figure(self, png: bytes, legende: str = "", largeur: float = 178):
        from PIL import Image
        im = Image.open(io.BytesIO(png))
        h = largeur * im.height / im.width
        if self.get_y() + h > 280:
            self.add_page()
        self.image(io.BytesIO(png), x=(210 - largeur) / 2, w=largeur)
        self.set_x(self.l_margin)
        if legende:
            self.set_font("DV", "I", 8)
            self.set_text_color(138, 137, 132)
            self.multi_cell(0, 4, legende)
        self.ln(3)

    def tableau(self, df: pd.DataFrame, largeurs: list[float] | None = None, max_lignes: int = 30):
        df = df.head(max_lignes)
        largeurs = largeurs or [178 / len(df.columns)] * len(df.columns)
        self.set_font("DV", "B", 8)
        self.set_fill_color(243, 244, 248)
        self.set_text_color(11, 11, 11)
        for c, w in zip(df.columns, largeurs):
            self.cell(w, 6, str(c)[:40], border=0, fill=True)
        self.ln()
        self.set_font("DV", "", 8)
        for _, r in df.iterrows():
            if self.get_y() > 275:
                self.add_page()
            for v, w in zip(r.values, largeurs):
                if isinstance(v, (int, float, np.number)) and not isinstance(v, bool) and v == v:
                    if float(v).is_integer() and 1900 <= v <= 2100:
                        s = str(int(v))  # année
                    else:
                        s = fmt_fr(v, 0 if float(v).is_integer() else 1)
                else:
                    s = str(v)
                self.cell(w, 5.5, s[: int(w / 1.6)], border="B")
            self.ln()
        self.ln(3)

    def lien(self, texte: str, url: str):
        self.set_font("DV", "", 9)
        self.set_text_color(0, 32, 159)
        self.set_x(self.l_margin)
        self.multi_cell(0, 5, texte, link=url)
        self.set_text_color(40, 40, 40)
