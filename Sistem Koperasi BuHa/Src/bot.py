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


# --- FUNGSI ENTRY POINT ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🏪 **Selamat Datang di Koperasi BakulByte!**\nSilakan pilih role Anda:",
        reply_markup=get_main_keyboard(),
        parse_mode='Markdown'
    )
    return MENU_UTAMA

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