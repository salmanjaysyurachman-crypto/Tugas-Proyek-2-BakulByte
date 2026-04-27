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
 E_ID, E_STOK, H_ID, KONFIRMASI HAPUS,
 B_ID, B_QTY, KONFIRMASI_BELI) = range(14)

ef ikb(*rows): return InlineKeyboardMarkup([[InlineKeyboardButton(t, callback_data=d) for t, d in row] for row in rows])
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

async def menu_utama_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pilihan = update.message.text
    user_id = str(update.effective_user.id)

    if pilihan == 'Admin':
        if user_id != ADMIN_ID:
            await update.message.reply_text("❌ Akses Ditolak! ID Anda tidak terdaftar.")
            return MENU_UTAMA
        await update.message.reply_text("🛠 **Mode Admin Aktif**", reply_markup=get_admin_keyboard(), parse_mode='Markdown')
        return MENU_ADMIN
    
    elif pilihan == 'Pembeli':
        await update.message.reply_text(f"👋 Halo {update.effective_user.first_name}!", reply_markup=get_pembeli_keyboard(), parse_mode='Markdown')
        return MENU_PEMBELI
    
    elif pilihan == 'Keluar':
        await update.message.reply_text("Sampai jumpa!", reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END
    return MENU_UTAMA

# --- LOGIKA ADMIN ---
async def admin_features(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == 'Tambah Barang':
        await update.message.reply_text("Masukkan NAMA barang baru:", reply_markup=ReplyKeyboardRemove())
        return T_NAMA
    elif text == 'Edit Stok':
        await update.message.reply_text("Masukkan ID Barang:", reply_markup=ReplyKeyboardRemove())
        return E_ID
    elif text == 'Hapus Barang':
        await update.message.reply_text("Masukkan ID Barang yang akan DIHAPUS:", reply_markup=ReplyKeyboardRemove())
        return H_ID
    elif text == 'Lihat Barang':
        items = pembeli.get_semua_barang()
        msg = "📦 **STOK GUDANG**\n\n" + "\n".join([f"ID: {i['id']} | {i['nama']} | Stok: {i['stok']} | Rp{i['harga']:,.0f}" for i in items])
        await update.message.reply_text(msg if items else "Gudang kosong.", parse_mode='Markdown')
        return MENU_ADMIN
    elif 'Laporan' in text:
        mode = 'harian' if 'Harian' in text else 'bulanan'
        file_path = admin.export_laporan(mode)
        await update.message.reply_document(document=open(file_path, 'rb'), caption=f"Laporan {mode}")
        return MENU_ADMIN
    elif text == 'Kembali':
        return await start(update, context)
    return MENU_ADMIN

# Input Admin Callbacks
async def get_t_nama(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['t_nama'] = update.message.text
    await update.message.reply_text(f"Harga untuk {update.message.text}?")
    return T_HARGA

async def get_t_harga(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['t_harga'] = update.message.text
    await update.message.reply_text("Jumlah stok awal?")
    return T_STOK

async def get_t_stok_final(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        admin.tambah_barang(context.user_data['t_nama'], float(context.user_data['t_harga']), int(update.message.text))
        await update.message.reply_text("✅ Berhasil disimpan!", reply_markup=get_admin_keyboard())
    except:
        await update.message.reply_text("❌ Gagal! Pastikan input benar.", reply_markup=get_admin_keyboard())
    return MENU_ADMIN

async def get_e_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['e_id'] = update.message.text
    await update.message.reply_text("Tambah stok berapa?")
    return E_STOK

async def get_e_stok_final(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        admin.edit_stok(int(context.user_data['e_id']), int(update.message.text))
        await update.message.reply_text("✅ Stok diperbarui!", reply_markup=get_admin_keyboard())
    except:
        await update.message.reply_text("❌ Gagal.", reply_markup=get_admin_keyboard())
    return MENU_ADMIN

async def get_h_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        admin.hapus_barang(int(update.message.text))
        await update.message.reply_text("🗑 Barang dihapus.", reply_markup=get_admin_keyboard())
    except:
        await update.message.reply_text("❌ Gagal.", reply_markup=get_admin_keyboard())
    return MENU_ADMIN

# --- LOGIKA PEMBELI ---
async def pembeli_features(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == 'Lihat Barang':
        items = pembeli.get_semua_barang()
        msg = "🛒 **BARANG TERSEDIA**\n\n" + "\n".join([f"ID: {i['id']} | {i['nama']} | Rp{i['harga']:,.0f}" for i in items])
        await update.message.reply_text(msg if items else "Stok kosong.", parse_mode='Markdown')
        return MENU_PEMBELI
    elif text == 'Beli Barang':
        items = pembeli.get_semua_barang()
        if not items:
            await update.message.reply_text("Stok kosong.")
            return MENU_PEMBELI
        msg = "📋 **DAFTAR ID**\n\n" + "\n".join([f"🆔 {i['id']} - {i['nama']} (Rp{i['harga']:,.0f})" for i in items])
        msg += "\n\nMasukkan **ID Barang** yang ingin dibeli:"
        context.user_data['keranjang'] = {}
        await update.message.reply_text(msg, parse_mode='Markdown', reply_markup=ReplyKeyboardRemove())
        return B_ID
    elif text == 'Kembali':
        return await start(update, context)
    return MENU_PEMBELI

async def get_b_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['current_id'] = update.message.text
    await update.message.reply_text("Beli berapa?")
    return B_QTY

async def get_b_qty(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        item_id = int(context.user_data['current_id'])
        qty = int(update.message.text)
        context.user_data['keranjang'][item_id] = qty
        kb = ReplyKeyboardMarkup([['Tambah Barang Lagi', 'Selesai & Bayar']], resize_keyboard=True)
        await update.message.reply_text("Masuk keranjang!", reply_markup=kb)
        return KONFIRMASI_BELI
    except:
        await update.message.reply_text("Masukkan angka!")
        return B_QTY

async def konfirmasi_beli_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pilihan = update.message.text
    if pilihan == 'Tambah Barang Lagi':
        await update.message.reply_text("Masukkan ID Barang selanjutnya:", reply_markup=ReplyKeyboardRemove())
        return B_ID
    elif pilihan == 'Selesai & Bayar':
        status_msg = await update.message.reply_text("⏳ Sedang memproses struk...")
        total, ringkasan = pembeli.proses_transaksi(update.effective_user.id, context.user_data.get('keranjang', {}))
        struk = f"🧾 **STRUK BAKULBYTE**\n---\n{ringkasan}\n---\n💰 **TOTAL: Rp{total}**"
        await status_msg.delete()
        await update.message.reply_text(struk, parse_mode='Markdown', reply_markup=get_pembeli_keyboard())
        return MENU_PEMBELI
    return MENU_PEMBELI

# --- MAIN RUNNER ---
def main():
    database.init_db()
    app = Application.builder().token(TOKEN).build()
    
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            MENU_UTAMA: [MessageHandler(filters.TEXT & ~filters.COMMAND, menu_utama_handler)],
            MENU_ADMIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_features)],
            T_NAMA: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_t_nama)],
            T_HARGA: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_t_harga)],
            T_STOK: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_t_stok_final)],
            E_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_e_id)],
            E_STOK: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_e_stok_final)],
            H_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_h_id)],
            MENU_PEMBELI: [MessageHandler(filters.TEXT & ~filters.COMMAND, pembeli_features)],
            B_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_b_id)],
            B_QTY: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_b_qty)],
            KONFIRMASI_BELI: [MessageHandler(filters.TEXT & ~filters.COMMAND, konfirmasi_beli_handler)],
        },
        fallbacks=[CommandHandler('start', start)]
    )
    
    app.add_handler(conv_handler)
    print("🚀 Bot BakulByte Berjalan...")
    app.run_polling()

if __name__ == '__main__':
    main()