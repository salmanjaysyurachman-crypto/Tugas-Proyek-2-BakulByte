import os, logging
from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes, ConversationHandler
import database, admin, pembeli
from struk_pdf import buat_struk_pdf
from ai_cs import tanya_ai, reset_riwayat
from logger import setup_logging, kirim_notif_crash, catch_and_report

load_dotenv()
setup_logging()
logger = logging.getLogger(__name__)

TOKEN    = os.getenv("BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")
for key, val in [("BOT_TOKEN", TOKEN), ("ADMIN_ID", ADMIN_ID), ("GROQ_API_KEY", os.getenv("GROQ_API_KEY"))]:
    if not val: raise ValueError(f"{key} belum diset di file .env!")

(MENU_UTAMA, MENU_ADMIN, MENU_PEMBELI, 
 T_NAMA, T_HARGA, T_STOK, 
 E_ID, E_STOK, H_ID, KONFIRMASI_HAPUS,
 B_ID, B_QTY, KONFIRMASI_BELI, AI_CHAT) = range(14)

def ikb(*rows): return InlineKeyboardMarkup([[InlineKeyboardButton(t, callback_data=d) for t, d in row] for row in rows])
BACK_HOME   = ikb([("🔙 Kembali", "back_home")])
KB_WELCOME  = ikb([("🛒 Lihat Barang","menu_lihat"),("👤 Mode Admin","menu_admin")],
                   [("🛍 Beli Barang","menu_beli"),  ("🤖 Tanya AI","menu_ai")],
                   [("📞 Kontak","menu_kontak"),      ("ℹ️ Tentang Kami","menu_tentang")],
                   [("🕐 Jam Operasional","menu_jam")])
KB_PEMBELI  = ikb([("🛒 Lihat Barang","pb_lihat"),("🛍 Beli Barang","pb_beli")],
                   [("🤖 Tanya AI","pb_ai"),        ("🔙 Menu Utama","back_home")])
KB_KERANJANG= ikb([("➕ Tambah Barang Lagi","kb_tambah"),("💳 Selesai & Bayar","kb_bayar")])
KB_AI       = ikb([("🔄 Reset Obrolan","ai_reset"),("🔙 Menu Utama","back_home")])
KB_ADMIN    = ReplyKeyboardMarkup([['Tambah Barang','Edit Stok'],['Hapus Barang','Lihat Barang'],
                                    ['Laporan Harian','Laporan Bulanan'],['Kembali']], resize_keyboard=True)

WELCOME_TEXT = (
    "✨ *Selamat Datang di Koperasi BakulByte!* ✨\n\n"
    "🏪 Koperasi serba ada dengan harga bersahabat!\n"
    "🛒 Berbagai pilihan produk tersedia\n"
    "💰 Harga terjangkau untuk semua kalangan\n"
    "📄 Struk PDF otomatis setiap transaksi\n"
    "🤖 Asisten AI siap membantu 24 jam\n\n"
    "Silakan pilih menu di bawah ini 👇"
)
AI_INTRO_TEXT = (
    "🤖 *BakulBot AI - Customer Service*\n\n"
    "Halo! Saya siap membantu menjawab pertanyaan seputar produk, harga, stok, dan informasi koperasi.\n\n"
    "Silakan ketik pertanyaanmu!\n"
    "_Contoh: \"Ada mie instan tidak? Berapa harganya?\"_\n\n"
    "Ketik /start untuk kembali ke menu utama."
)

def fmt_produk(items, mode="lihat"):
    if not items: return "🏪 Stok sedang kosong."
    header = "🛒 *BARANG TERSEDIA*" if mode == "lihat" else "📋 *DAFTAR BARANG*"
    baris = "\n".join(
        f"🆔 {i['id']} | {i['nama']} | Rp{i['harga']:,.0f} | Stok: {i['stok']}" for i in items
    )
    return f"{header}\n\n{baris}"

async def kirim_welcome(target, context):
    context.user_data.clear()
    await target.reply_text(WELCOME_TEXT, reply_markup=KB_WELCOME, parse_mode='Markdown')

def get_produk_by_id(item_id):
    conn = database.get_db()
    item = conn.execute("SELECT * FROM produk WHERE id = ?", (item_id,)).fetchone()
    conn.close()
    return item

@catch_and_report("start")
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target = update.callback_query.message if update.callback_query else update.message
    await kirim_welcome(target, context)
    return MENU_UTAMA

@catch_and_report("ai_command")
async def ai_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if not context.args:
        await update.message.reply_text(
            "🤖 *BakulBot AI*\n\n• `/ai <pertanyaan>` — tanya seputar produk\n• `/ai reset` — mulai percakapan baru",
            parse_mode='Markdown'
        )
        return
    pesan = " ".join(context.args)
    if pesan.lower() == "reset":
        reset_riwayat(user_id)
        await update.message.reply_text("🔄 Riwayat obrolan AI direset!")
        return
    await update.message.chat.send_action("typing")
    balasan = tanya_ai(user_id, pesan)
    await update.message.reply_text(f"🤖 *BakulBot AI:*\n\n{balasan}", parse_mode='Markdown', reply_markup=KB_AI)


async def test_error(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Command khusus Admin untuk menguji sistem logging & notifikasi crash.
    Hanya bisa dijalankan oleh Admin (berdasarkan ADMIN_ID di .env).

    Cara pakai:
        /test_error             → simulasi ZeroDivisionError
        /test_error db          → simulasi error database
        /test_error value       → simulasi ValueError
    """
    user_id = str(update.effective_user.id)

    if user_id != ADMIN_ID:
        await update.message.reply_text("❌ Perintah ini khusus Admin.")
        return
    
    jenis = context.args[0].lower() if context.args else "zero"

    await update.message.reply_text(
        f"🧪 *Menjalankan simulasi error: `{jenis}`*\n"
        f"Cek `error_log.txt` dan notifikasi Telegram Admin...",
        parse_mode="Markdown"
    )

    try:
        if jenis == "db":
            conn = database.get_db()
            conn.execute("SELECT * FROM tabel_tidak_ada")
        elif jenis == "value":
            int("ini_bukan_angka")
        else:
            _ = 1 / 0

    except Exception as exc:
        logger.error(
            f"[test_error/{jenis}] Simulasi error oleh Admin (user_id={user_id}): "
            f"{type(exc).__name__}: {exc}",
            exc_info=True
        )
        await kirim_notif_crash(
            bot=context.bot,
            exc=exc,
            konteks=f"test_error/{jenis}",
            user_id=user_id,
            extra=f"Ini adalah simulasi — bukan error nyata. Jenis: {jenis}"
        )
        await update.message.reply_text(
            "✅ *Simulasi selesai!*\n\n"
            "Hasil yang diharapkan:\n"
            "• File `error_log.txt` sudah diperbarui\n"
            "• Notifikasi crash sudah dikirim ke Admin\n\n"
            f"Error yang disimulasikan: `{type(exc).__name__}: {exc}`",
            parse_mode="Markdown"
        )
MENU_TEKS = {
    "menu_kontak": (
        "📞 *Hubungi Kami*\n\n"
        "📱 WhatsApp: +62 858-6149-3082\n"
        "📧 Email: KoperasiBuHa@koperasi.id\n"
        "📍 Alamat: Jl. Sulawesi No. 1, Pemalang\n\n_Kami siap membantu Anda!_"
    ),
    "menu_tentang": (
        "ℹ️ *Tentang Koperasi BuHa*\n\n"
        "Koperasi BuHa adalah koperasi digital untuk kebutuhan sehari-hari.\n\n"
        "🎯 *Visi:* Koperasi modern yang inklusif dan terpercaya.\n"
        "💡 *Misi:* Layanan belanja yang mudah, cepat, dan transparan.\n\n"
        "_Bersama BakulByte, belanja jadi lebih mudah!_ 🚀"
    ),
    "menu_jam": (
        "🕐 *Jam Operasional*\n\n"
        "Senin - Jumat : 08.00 - 17.00 WIB\n"
        "Sabtu         : 08.00 - 13.00 WIB\n"
        "Minggu        : Tutup\n\n_Bot tetap aktif 24 jam!_ ⚡"
    ),
}

@catch_and_report("inline_menu_handler")
async def inline_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query   = update.callback_query
    await query.answer()
    data    = query.data
    user_id = str(update.effective_user.id)

    if data == "menu_lihat":
        msg = fmt_produk(pembeli.get_semua_barang())
        await query.message.reply_text(msg, parse_mode='Markdown', reply_markup=BACK_HOME)

    elif data == "menu_beli":
        items = pembeli.get_semua_barang()
        if not items:
            await query.message.reply_text("🏪 Stok sedang kosong.")
            return MENU_UTAMA
        context.user_data['keranjang'] = {}
        msg = fmt_produk(items, "beli") + "\n\nMasukkan *ID Barang* yang ingin dibeli:"
        await query.message.reply_text(msg, parse_mode='Markdown')
        return B_ID

    elif data == "menu_admin":
        if user_id != ADMIN_ID:
            await query.message.reply_text("❌ Akses Ditolak!")
            return MENU_UTAMA
        await query.message.reply_text("🛠 *Mode Admin Aktif*\nSelamat datang, Admin!",
                                        reply_markup=KB_ADMIN, parse_mode='Markdown')
        return MENU_ADMIN

    elif data == "menu_ai":
        await query.message.reply_text(AI_INTRO_TEXT, parse_mode='Markdown', reply_markup=KB_AI)
        return AI_CHAT

    elif data in MENU_TEKS:
        await query.message.reply_text(MENU_TEKS[data], parse_mode='Markdown', reply_markup=BACK_HOME)

    elif data == "back_home":
        await kirim_welcome(query.message, context)

    return MENU_UTAMA

@catch_and_report("ai_chat_handler")
async def ai_chat_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.chat.send_action("typing")
    balasan = tanya_ai(str(update.effective_user.id), update.message.text)
    await update.message.reply_text(f"🤖 *BakulBot AI:*\n\n{balasan}", parse_mode='Markdown', reply_markup=KB_AI)
    return AI_CHAT

@catch_and_report("ai_inline_handler")
async def ai_inline_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "ai_reset":
        reset_riwayat(str(update.effective_user.id))
        await query.message.reply_text("🔄 Riwayat obrolan direset!", reply_markup=KB_AI)
        return AI_CHAT
    await kirim_welcome(query.message, context)
    return MENU_UTAMA

# ── Pembeli ───────────────────────────────────────────────────
@catch_and_report("inline_pembeli_handler")
async def inline_pembeli_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data  = query.data

    if data == "pb_lihat":
        msg = fmt_produk(pembeli.get_semua_barang())
        back_kb = ikb([("🔙 Kembali", "pb_back")])
        await query.message.reply_text(msg, parse_mode='Markdown', reply_markup=back_kb)

    elif data == "pb_beli":
        items = pembeli.get_semua_barang()
        if not items:
            await query.message.reply_text("🏪 Stok sedang kosong.")
            return MENU_PEMBELI
        context.user_data['keranjang'] = {}
        msg = fmt_produk(items, "beli") + "\n\nMasukkan *ID Barang* yang ingin dibeli:"
        await query.message.reply_text(msg, parse_mode='Markdown')
        return B_ID

    elif data == "pb_ai":
        await query.message.reply_text(AI_INTRO_TEXT, parse_mode='Markdown', reply_markup=KB_AI)
        return AI_CHAT

    elif data in ("pb_back", "back_home"):
        await kirim_welcome(query.message, context)
        return MENU_UTAMA

    return MENU_PEMBELI

@catch_and_report("inline_keranjang_handler")
async def inline_keranjang_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "kb_tambah":
        items = pembeli.get_semua_barang()
        if not items:
            await query.message.reply_text("🏪 Stok sudah habis semua.")
            return KONFIRMASI_BELI
        msg = fmt_produk(items, "beli") + "\n\nMasukkan *ID Barang* selanjutnya:"
        await query.message.reply_text(msg, parse_mode='Markdown')
        return B_ID

    elif query.data == "kb_bayar":
        status_msg = await query.message.reply_text("⏳ Sedang memproses transaksi...")
        user = update.effective_user
        total_str, ringkasan, items_data = pembeli.proses_transaksi(
            user.id, context.user_data.get('keranjang', {})
        )
        context.user_data['keranjang'] = {}

        if total_str == "0" and not items_data:
            await status_msg.delete()
            await query.message.reply_text(
                "❌ Transaksi gagal! Mungkin stok habis.\nSilakan coba lagi.",
                reply_markup=KB_PEMBELI
            )
            return MENU_PEMBELI

        await status_msg.delete()
        await query.message.reply_text(
            f"🧾 *STRUK BAKULBYTE*\n━━━━━━━━━━━━━━━━━━\n{ringkasan}\n━━━━━━━━━━━━━━━━━━\n💰 *TOTAL: Rp{total_str}*",
            parse_mode='Markdown', reply_markup=KB_PEMBELI
        )

        if items_data:
            try:
                pdf_path = buat_struk_pdf(
                    user_name=user.full_name or user.first_name,
                    user_id=user.id, items=items_data,
                    total=float(total_str.replace(",", ""))
                )
                with open(pdf_path, 'rb') as f:
                    await query.message.reply_document(document=f, filename="Struk_BakulByte.pdf",
                                                        caption="📄 Struk PDF kamu sudah siap!")
            except Exception as e:
                logger.error(f"Gagal kirim PDF: {e}", exc_info=True)
            finally:
                try: os.remove(pdf_path)
                except OSError: pass

    return MENU_PEMBELI

# ── Admin Features ────────────────────────────────────────────
@catch_and_report("admin_features")
async def admin_features(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == 'Tambah Barang':
        await update.message.reply_text("Masukkan NAMA barang baru:", reply_markup=ReplyKeyboardRemove())
        return T_NAMA
    elif text == 'Edit Stok':
        await update.message.reply_text("Masukkan ID Barang yang stoknya ingin diedit:", reply_markup=ReplyKeyboardRemove())
        return E_ID
    elif text == 'Hapus Barang':
        await update.message.reply_text("Masukkan ID Barang yang akan DIHAPUS:", reply_markup=ReplyKeyboardRemove())
        return H_ID
    elif text == 'Lihat Barang':
        conn = database.get_db()
        items = conn.execute("SELECT * FROM produk").fetchall()
        conn.close()
        msg = ("📦 *STOK GUDANG (SEMUA PRODUK)*\n\n" +
               "\n".join(f"ID: {i['id']} | {i['nama']} | Stok: {i['stok']} | Rp{i['harga']:,.0f}" for i in items)
               if items else "Gudang kosong.")
        await update.message.reply_text(msg, parse_mode='Markdown')
        return MENU_ADMIN
    elif 'Laporan' in text:
        mode = 'harian' if 'Harian' in text else 'bulanan'
        file_path = None
        try:
            file_path = admin.export_laporan(mode)
            with open(file_path, 'rb') as f:
                await update.message.reply_document(document=f, caption=f"📊 Laporan {mode.capitalize()} BakulByte")
        except Exception as e:
            logger.error(f"Gagal export laporan: {e}", exc_info=True)
            await update.message.reply_text("❌ Gagal membuat laporan.")
        finally:
            if file_path:
                try: os.remove(file_path)
                except OSError: pass
        return MENU_ADMIN
    elif text == 'Kembali':
        await update.message.reply_text(WELCOME_TEXT, reply_markup=KB_WELCOME, parse_mode='Markdown')
        return MENU_UTAMA

    return MENU_ADMIN

@catch_and_report("get_t_nama")
async def get_t_nama(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['t_nama'] = update.message.text.strip()
    await update.message.reply_text(f"Harga untuk *{context.user_data['t_nama']}*? (contoh: 5000)", parse_mode='Markdown')
    return T_HARGA

@catch_and_report("get_t_harga")
async def get_t_harga(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        harga = float(update.message.text.replace(',', '.'))
        if harga <= 0: raise ValueError
        context.user_data['t_harga'] = harga
        await update.message.reply_text("Jumlah stok awal?")
        return T_STOK
    except ValueError:
        await update.message.reply_text("❌ Harga tidak valid! Masukkan angka positif:")
        return T_HARGA

@catch_and_report("get_t_stok_final")
async def get_t_stok_final(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        stok = int(update.message.text)
        if stok < 0: raise ValueError
        admin.tambah_barang(context.user_data['t_nama'], context.user_data['t_harga'], stok)
        await update.message.reply_text(f"✅ *{context.user_data['t_nama']}* berhasil ditambahkan!",
                                         reply_markup=KB_ADMIN, parse_mode='Markdown')
    except ValueError:
        await update.message.reply_text("❌ Stok tidak valid! Masukkan angka bulat positif:")
        return T_STOK
    except Exception as e:
        logger.error(f"Gagal tambah barang: {e}", exc_info=True)
        await update.message.reply_text("❌ Gagal menyimpan.", reply_markup=KB_ADMIN)
    return MENU_ADMIN

# ── Admin: Edit Stok ──────────────────────────────────────────
@catch_and_report("get_e_id")
async def get_e_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        item_id = int(update.message.text)
        item = get_produk_by_id(item_id)
        if not item:
            await update.message.reply_text("❌ ID tidak ditemukan!", reply_markup=KB_ADMIN)
            return MENU_ADMIN
        context.user_data['e_id']   = item_id
        context.user_data['e_nama'] = item['nama']
        await update.message.reply_text(
            f"Produk: *{item['nama']}* | Stok saat ini: *{item['stok']}*\n\nTambah stok berapa?",
            parse_mode='Markdown'
        )
        return E_STOK
    except ValueError:
        await update.message.reply_text("❌ Masukkan angka!", reply_markup=KB_ADMIN)
        return MENU_ADMIN

@catch_and_report("get_e_stok_final")
async def get_e_stok_final(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        tambahan = int(update.message.text)
        admin.edit_stok(context.user_data['e_id'], tambahan)
        await update.message.reply_text(
            f"✅ Stok *{context.user_data['e_nama']}* ditambah *{tambahan}*!",
            reply_markup=KB_ADMIN, parse_mode='Markdown'
        )
    except ValueError:
        await update.message.reply_text("❌ Masukkan angka bulat!", reply_markup=KB_ADMIN)
        return E_STOK
    except Exception as e:
        logger.error(f"Gagal edit stok: {e}", exc_info=True)
        await update.message.reply_text("❌ Gagal mengupdate stok.", reply_markup=KB_ADMIN)
    return MENU_ADMIN

@catch_and_report("get_h_id")
async def get_h_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        item_id = int(update.message.text)
        item = get_produk_by_id(item_id)
        if not item:
            await update.message.reply_text("❌ ID tidak ditemukan!", reply_markup=KB_ADMIN)
            return MENU_ADMIN
        context.user_data['h_id']   = item_id
        context.user_data['h_nama'] = item['nama']
        await update.message.reply_text(
            f"⚠️ Yakin ingin menghapus *{item['nama']}*?", parse_mode='Markdown',
            reply_markup=ReplyKeyboardMarkup([['Ya, Hapus', 'Batal']], resize_keyboard=True)
        )
        return KONFIRMASI_HAPUS
    except ValueError:
        await update.message.reply_text("❌ Masukkan angka!", reply_markup=KB_ADMIN)
        return MENU_ADMIN

@catch_and_report("eksekusi_hapus")
async def eksekusi_hapus(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == 'Ya, Hapus':
        try:
            admin.hapus_barang(context.user_data['h_id'])
            await update.message.reply_text(f"🗑 *{context.user_data['h_nama']}* berhasil dihapus.",
                                             reply_markup=KB_ADMIN, parse_mode='Markdown')
        except Exception as e:
            logger.error(f"Gagal hapus: {e}", exc_info=True)
            await update.message.reply_text("❌ Gagal menghapus.", reply_markup=KB_ADMIN)
    else:
        await update.message.reply_text("❌ Penghapusan dibatalkan.", reply_markup=KB_ADMIN)
    return MENU_ADMIN

# ── Pembeli: Proses Belanja ───────────────────────────────────
@catch_and_report("get_b_id")
async def get_b_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        item_id = int(update.message.text)
        items   = pembeli.get_semua_barang()
        item    = next((i for i in items if i['id'] == item_id), None)
        if not item:
            await update.message.reply_text("❌ ID tidak ditemukan atau stok habis! Masukkan ID yang valid:")
            return B_ID
        context.user_data.update({'current_id': item_id, 'current_nama': item['nama'], 'current_stok': item['stok']})
        await update.message.reply_text(
            f"✅ *{item['nama']}*\nHarga: Rp{item['harga']:,.0f} | Stok tersedia: {item['stok']}\n\nBeli berapa?",
            parse_mode='Markdown'
        )
        return B_QTY
    except ValueError:
        await update.message.reply_text("❌ Masukkan angka ID yang valid!")
        return B_ID

@catch_and_report("get_b_qty")
async def get_b_qty(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        qty           = int(update.message.text)
        stok_tersedia = context.user_data.get('current_stok', 0)
        item_id       = int(context.user_data['current_id'])
        qty_lama      = context.user_data.get('keranjang', {}).get(item_id, 0)
        qty_total     = qty_lama + qty

        if qty <= 0:
            await update.message.reply_text("❌ Jumlah harus lebih dari 0!")
            return B_QTY
        if qty > stok_tersedia:
            await update.message.reply_text(f"❌ Stok tidak cukup! Maksimal *{stok_tersedia}* unit.", parse_mode='Markdown')
            return B_QTY
        if qty_total > stok_tersedia:
            await update.message.reply_text(
                f"❌ Total jadi {qty_total}, tapi stok hanya {stok_tersedia}!\n"
                f"Sudah ada {qty_lama} di keranjang. Tambah maks {stok_tersedia - qty_lama} lagi.",
                parse_mode='Markdown'
            )
            return B_QTY

        context.user_data['keranjang'][item_id] = qty_total
        pesan = f"✅ *{context.user_data['current_nama']}* x{qty} masuk keranjang!"
        if qty_lama > 0: pesan += f"\n_(total di keranjang: {qty_total})_"
        await update.message.reply_text(pesan, parse_mode='Markdown', reply_markup=KB_KERANJANG)
        return KONFIRMASI_BELI

    except ValueError:
        await update.message.reply_text("❌ Masukkan angka!")
        return B_QTY

# ── Main ──────────────────────────────────────────────────────
def main():
    database.init_db()
    logger.info("🚀 BakulByte Bot dimulai...")

    app = Application.builder().token(TOKEN).build()
    TXT = filters.TEXT & ~filters.COMMAND

    conv = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            MENU_UTAMA:       [CallbackQueryHandler(inline_menu_handler)],
            MENU_ADMIN:       [MessageHandler(TXT, admin_features)],
            T_NAMA:           [MessageHandler(TXT, get_t_nama)],
            T_HARGA:          [MessageHandler(TXT, get_t_harga)],
            T_STOK:           [MessageHandler(TXT, get_t_stok_final)],
            E_ID:             [MessageHandler(TXT, get_e_id)],
            E_STOK:           [MessageHandler(TXT, get_e_stok_final)],
            H_ID:             [MessageHandler(TXT, get_h_id)],
            KONFIRMASI_HAPUS: [MessageHandler(TXT, eksekusi_hapus)],
            MENU_PEMBELI:     [CallbackQueryHandler(inline_pembeli_handler)],
            B_ID:             [MessageHandler(TXT, get_b_id)],
            B_QTY:            [MessageHandler(TXT, get_b_qty)],
            KONFIRMASI_BELI:  [CallbackQueryHandler(inline_keranjang_handler)],
            AI_CHAT:          [MessageHandler(TXT, ai_chat_handler), CallbackQueryHandler(ai_inline_handler)],
        },
        fallbacks=[CommandHandler('start', start)],
        allow_reentry=True,
    )

    app.add_handler(conv)
    app.add_handler(CommandHandler('ai', ai_command))
    # [BARU] Command simulasi error — khusus Admin
    app.add_handler(CommandHandler('test_error', test_error))

    logger.info("✅ Semua handler terdaftar. Bot siap menerima pesan.")
    print("🚀 Bot BakulByte + AI (Groq) Berjalan...")
    app.run_polling()

if __name__ == '__main__':
    main()

