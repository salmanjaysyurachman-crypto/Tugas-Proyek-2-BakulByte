from reportlab.lib.pagesizes import A6
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from datetime import datetime
import io

# ── Palet Warna ──────────────────────────────────────────────
HIJAU_TUA   = colors.HexColor("#1B4332")
HIJAU_MUDA  = colors.HexColor("#52B788")
KREM        = colors.HexColor("#F8F4E3")
ABU_GELAP   = colors.HexColor("#2D2D2D")
ABU_MUDA    = colors.HexColor("#9E9E9E")
PUTIH       = colors.white
KUNING_AKSEN= colors.HexColor("#FFD166")

PAGE_W, PAGE_H = A6  # 105 x 148 mm

def _draw_header(c: canvas.Canvas, page_w, page_h):
    """Blok header hijau dengan nama toko & ikon."""
    header_h = 38 * mm

    # Background header
    c.setFillColor(HIJAU_TUA)
    c.roundRect(0, page_h - header_h, page_w, header_h, 0, fill=1, stroke=0)

    # Aksen strip tipis kuning di bawah header
    c.setFillColor(KUNING_AKSEN)
    c.rect(0, page_h - header_h - 1.5*mm, page_w, 1.5*mm, fill=1, stroke=0)

    # Ikon toko (emoji-like dengan lingkaran)
    cx, cy = page_w / 2, page_h - 12 * mm
    c.setFillColor(HIJAU_MUDA)
    c.circle(cx, cy, 7 * mm, fill=1, stroke=0)
    c.setFillColor(PUTIH)
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(cx, cy - 2*mm, "BB")

    # Nama toko
    c.setFillColor(PUTIH)
    c.setFont("Helvetica-Bold", 13)
    c.drawCentredString(page_w / 2, page_h - 24 * mm, "KOPERASI BUHA")

    # Tagline
    c.setFillColor(HIJAU_MUDA)
    c.setFont("Helvetica-Oblique", 7)
    c.drawCentredString(page_w / 2, page_h - 29 * mm, "Belanja mudah, harga bersahabat")