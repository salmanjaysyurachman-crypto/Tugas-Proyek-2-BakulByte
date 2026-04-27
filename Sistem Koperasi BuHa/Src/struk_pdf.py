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

    def _draw_info_row(c: canvas.Canvas, y, label, value, page_w):
    """Baris info dua kolom (label kiri, value kanan)."""
    margin = 8 * mm
    c.setFont("Helvetica", 7)
    c.setFillColor(ABU_MUDA)
    c.drawString(margin, y, label)
    c.setFillColor(ABU_GELAP)
    c.drawRightString(page_w - margin, y, value)


def _draw_divider(c: canvas.Canvas, y, page_w, dashed=False):
    margin = 8 * mm
    c.setStrokeColor(colors.HexColor("#DDDDDD"))
    c.setLineWidth(0.5)
    if dashed:
        c.setDash(2, 3)
    else:
        c.setDash()
    c.line(margin, y, page_w - margin, y)
    c.setDash()


def _draw_item_row(c: canvas.Canvas, y, nama, qty, harga_satuan, subtotal, page_w):
    margin = 8 * mm
    col_qty   = 22 * mm
    col_harga = 50 * mm

    c.setFont("Helvetica-Bold", 7.5)
    c.setFillColor(ABU_GELAP)
    c.drawString(margin, y, nama[:28])  # truncate panjang

    y2 = y - 4 * mm
    c.setFont("Helvetica", 7)
    c.setFillColor(ABU_MUDA)
    c.drawString(margin, y2, f"x{qty}")
    c.drawString(margin + col_qty, y2, f"@ Rp{harga_satuan:,.0f}")
    c.setFillColor(HIJAU_TUA)
    c.setFont("Helvetica-Bold", 7.5)
    c.drawRightString(page_w - margin, y2, f"Rp{subtotal:,.0f}")

    return y2 - 5 * mm   # kembalikan posisi Y berikutnya


def _draw_total_box(c: canvas.Canvas, y, total, page_w):
    margin = 8 * mm
    box_h  = 11 * mm

    # Kotak total
    c.setFillColor(HIJAU_TUA)
    c.roundRect(margin, y - box_h, page_w - 2*margin, box_h, 3*mm, fill=1, stroke=0)

    mid_y = y - box_h / 2 - 1.5*mm
    c.setFillColor(PUTIH)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(margin + 4*mm, mid_y, "TOTAL PEMBAYARAN")
    c.setFont("Helvetica-Bold", 10)
    c.drawRightString(page_w - margin - 4*mm, mid_y, f"Rp{total:,.0f}")

    return y - box_h - 4*mm

def _draw_footer(c: canvas.Canvas, y, page_w, no_struk):
    margin = 8 * mm

    # No struk
    c.setFont("Helvetica", 6.5)
    c.setFillColor(ABU_MUDA)
    c.drawCentredString(page_w / 2, y, f"No. Struk: {no_struk}")

    y -= 4 * mm
    # Garis dekoratif
    c.setStrokeColor(KUNING_AKSEN)
    c.setLineWidth(1.5)
    c.line(margin, y, page_w - margin, y)

    y -= 5 * mm
    c.setFont("Helvetica-Bold", 7.5)
    c.setFillColor(HIJAU_TUA)
    c.drawCentredString(page_w / 2, y, "Terima kasih sudah berbelanja!")

    y -= 4 * mm
    c.setFont("Helvetica", 6.5)
    c.setFillColor(ABU_MUDA)
    c.drawCentredString(page_w / 2, y, "Barang yang sudah dibeli tidak dapat dikembalikan.")


# ─────────────────────────────────────────────────────────────
def buat_struk_pdf(
    user_name: str,
    user_id: int | str,
    items: list[dict],   # [{"nama": str, "qty": int, "harga": float, "subtotal": float}]
    total: float,
    output_path: str = None,
) -> str:
    """
    Membuat struk PDF keren untuk transaksi.

    Args:
        user_name   : Nama pembeli (dari Telegram)
        user_id     : ID Telegram pembeli
        items       : List item yang dibeli
        total       : Total harga
        output_path : Path file output (opsional, auto-generate jika None)

    Returns:
        Path file PDF yang dihasilkan.
    """

    if output_path is None:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = f"struk_{user_id}_{ts}.pdf"

    now = datetime.now()
    no_struk = f"BB-{now.strftime('%Y%m%d%H%M%S')}-{str(user_id)[-4:]}"
    tgl_str  = now.strftime("%d %B %Y, %H:%M")

    c = canvas.Canvas(output_path, pagesize=A6)
    c.setTitle("Struk Belanja BakulByte")

    # ── Header ───────────────────────────────────────────────
    _draw_header(c, PAGE_W, PAGE_H)

    # ── Info transaksi ────────────────────────────────────────
    y = PAGE_H - 42 * mm
    _draw_info_row(c, y, "Pembeli",  user_name,  PAGE_W)
    y -= 4.5 * mm
    _draw_info_row(c, y, "Tanggal",  tgl_str,    PAGE_W)
    y -= 4.5 * mm
    _draw_info_row(c, y, "Kasir",    "BakulBot", PAGE_W)

    y -= 3 * mm
    _draw_divider(c, y, PAGE_W)

    # ── Label kolom ──────────────────────────────────────────
    y -= 5 * mm
    margin = 8 * mm
    c.setFont("Helvetica-Bold", 7)
    c.setFillColor(HIJAU_TUA)
    c.drawString(margin, y, "ITEM")
    c.drawRightString(PAGE_W - margin, y, "SUBTOTAL")
    y -= 3 * mm
    _draw_divider(c, y, PAGE_W, dashed=True)
    y -= 5 * mm

    # ── Baris item ───────────────────────────────────────────
    for item in items:
        y = _draw_item_row(
            c, y,
            item["nama"], item["qty"],
            item["harga"], item["subtotal"],
            PAGE_W
        )
        # Cek sisa ruang
        if y < 35 * mm:
            # (Untuk struk panjang, bisa tambah halaman — skip untuk sekarang)
            break

    y -= 2 * mm
    _draw_divider(c, y, PAGE_W)
    y -= 6 * mm

    # ── Kotak Total ──────────────────────────────────────────
    y = _draw_total_box(c, y, total, PAGE_W)

    # ── Footer ───────────────────────────────────────────────
    _draw_footer(c, y - 2*mm, PAGE_W, no_struk)

    c.save()
    return output_path