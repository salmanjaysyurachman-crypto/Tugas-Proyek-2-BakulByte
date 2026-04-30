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

## Kemampuanmu
- Cek ketersediaan & harga produk
- Rekomendasikan produk berdasarkan kebutuhan pengguna
- Jelaskan cara bertransaksi di bot
- Bantu pengguna menemukan produk yang cocok dengan budget
- Informasikan jam operasional: Senin–Jumat 08.00–17.00, Sabtu 08.00–13.00"""

def tanya_ai(user_id: str, pesan_user: str) -> str:
    """
    Kirim pesan ke AI dengan konteks database dan riwayat percakapan.

    Args:
        user_id    : ID Telegram pengguna (sebagai string)
        pesan_user : Pesan yang dikirim pengguna

    Returns:
        Respons teks dari AI
    """
    if user_id not in riwayat_chat:
        riwayat_chat[user_id] = []

    riwayat_chat[user_id].append({
        "role": "user",
        "content": pesan_user
    })

    # Batasi riwayat agar tidak terlalu panjang
    if len(riwayat_chat[user_id]) > MAX_HISTORY * 2:
        riwayat_chat[user_id] = riwayat_chat[user_id][-(MAX_HISTORY * 2):]

    try:
        system_prompt = build_system_prompt(user_id)

        messages_with_system = [
            {"role": "system", "content": system_prompt}
        ] + riwayat_chat[user_id]

        # get_client() baru membuat Groq() di sini, setelah .env pasti sudah terbaca
        response = get_client().chat.completions.create(
            model=GROQ_MODEL,
            messages=messages_with_system,
            max_tokens=512,
            temperature=0.7,
        )

        balasan = response.choices[0].message.content

        riwayat_chat[user_id].append({
            "role": "assistant",
            "content": balasan
        })

        return balasan

    except Exception as e:
        err = str(e).lower()
        if "connection" in err or "network" in err:
            logger.error(f"Koneksi ke Groq gagal: {e}")
            return "Maaf Kak, layanan AI sedang tidak dapat dijangkau. Coba lagi sebentar lagi ya."
        elif "rate" in err or "quota" in err or "429" in err:
            logger.error(f"Rate limit Groq: {e}")
            return "Maaf Kak, layanan AI sedang sibuk. Coba lagi dalam beberapa menit ya."
        elif "401" in err or ("invalid" in err and "key" in err):
            logger.error(f"API key Groq tidak valid: {e}")
            return "Maaf Kak, terjadi masalah konfigurasi. Hubungi admin ya."
        else:
            logger.error(f"Error tidak terduga di tanya_ai: {e}")
            return "Maaf Kak, ada kendala teknis. Coba lagi ya!"


def reset_riwayat(user_id: str) -> None:
    """Hapus riwayat percakapan user (untuk command /ai reset)."""
    if user_id in riwayat_chat:
        del riwayat_chat[user_id]