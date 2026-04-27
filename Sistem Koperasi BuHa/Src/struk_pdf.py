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