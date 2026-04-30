import os
import logging
from groq import Groq
from dotenv import load_dotenv
from database import get_db
from datetime import datetime

load_dotenv()

logger = logging.getLogger(__name__)
GROQ_MODEL = "llama-3.3-70b-versatile"
_client: Groq | None = None

def get_client() -> Groq:
    global _client
    if _client is None:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY belum diset di file .env!")
        _client = Groq(api_key=api_key)
    return _client

riwayat_chat: dict[str, list] = {}

MAX_HISTORY = 10  


def get_konteks_produk() -> str:
    """Ambil semua produk dari database dan format sebagai teks untuk system prompt."""
    try:
        conn = get_db()
        produk = conn.execute("SELECT id, nama, harga, stok FROM produk").fetchall()
        conn.close()

        if not produk:
            return "Saat ini tidak ada produk yang tersedia di koperasi."
        
        baris = []
        for p in produk:
            status = "✅ Tersedia" if p["stok"] > 0 else "❌ Habis"
            baris.append(
                f"- ID {p['id']} | {p['nama']} | Rp{p['harga']:,.0f} | Stok: {p['stok']} | {status}"
            )
        return "\n".join(baris)

    except Exception as e:
        logger.error(f"Gagal ambil produk untuk AI: {e}")
        return "Data produk sedang tidak dapat diakses."
    
def get_riwayat_transaksi_user(user_id: str, limit: int = 5) -> str:
    """Ambil riwayat transaksi user terakhir untuk konteks personal."""
    try:
        conn = get_db()
        transaksi = conn.execute(
            "SELECT items, total_harga, tanggal FROM transaksi WHERE user_id = ? ORDER BY id DESC LIMIT ?",
            (user_id, limit)
        ).fetchall()
        conn.close()

        if not transaksi:
            return "Pengguna ini belum pernah bertransaksi."

        baris = []
        for t in transaksi:
            baris.append(f"- [{t['tanggal']}] Total: Rp{t['total_harga']:,.0f} | Item: {t['items'][:80]}...")
        return "\n".join(baris)

    except Exception as e:
        logger.error(f"Gagal ambil riwayat transaksi: {e}")
        return "Riwayat transaksi tidak dapat diakses."

def build_system_prompt(user_id: str) -> str:
    """Bangun system prompt dengan data real-time dari database."""
    produk_terkini   = get_konteks_produk()
    riwayat          = get_riwayat_transaksi_user(user_id)
    tanggal_sekarang = datetime.now().strftime("%A, %d %B %Y pukul %H:%M WIB")

    return f"""Kamu adalah **BakulBot AI**, asisten customer service profesional dari **Koperasi BakulByte** — koperasi digital yang melayani kebutuhan sehari-hari.

## Kepribadian & Gaya Bicara
- Ramah, sopan, dan hangat seperti pelayan toko yang berpengalaman
- Gunakan bahasa Indonesia yang natural, tidak kaku
- Boleh sesekali menggunakan sapaan "Kak" untuk kesan akrab
- Singkat dan to the point — tidak bertele-tele
- Jika tidak tahu atau data tidak tersedia, jujur mengakui dan arahkan ke admin

## Tanggal & Waktu Sekarang
{tanggal_sekarang}

## Data Produk Real-Time (WAJIB dijadikan acuan jawaban)
Berikut adalah daftar produk koperasi saat ini:
{produk_terkini}

## Riwayat Belanja Pengguna Ini
{riwayat}

## Aturan Penting
1. **HANYA jawab berdasarkan data produk di atas.** Jangan mengarang produk, harga, atau stok yang tidak ada di daftar.
2. Jika pengguna tanya produk yang tidak ada di daftar → sampaikan bahwa produk tersebut belum tersedia, tawarkan produk yang relevan jika ada.
3. Jika pengguna tanya stok yang **habis** → sampaikan dengan sopan dan sarankan alternatif jika ada.
4. Untuk pembelian, arahkan pengguna menggunakan tombol menu bot (ketik /start).
5. Jangan membahas topik di luar koperasi (politik, hiburan, dll) — alihkan dengan sopan.
6. Jika ada pertanyaan komplain atau masalah serius → arahkan ke admin: WhatsApp +62 812-3456-7890.