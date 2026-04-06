import os
import logging
from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Application, CommandHandler, MessageHandler, 
    filters, ContextTypes, ConversationHandler
)

# Import modul internal
import database, admin, pembeli

# Setup Logging agar kita bisa lihat error di terminal
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', 
    level=logging.INFO
)

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")

# Definisi States
(MENU_UTAMA, MENU_ADMIN, MENU_PEMBELI, 
 T_NAMA, T_HARGA, T_STOK, 
 E_ID, E_STOK, 
 H_ID,
 B_ID, B_QTY, KONFIRMASI_BELI) = range(12)

# --- KEYBOARD HELPERS ---
def get_main_keyboard():
    return ReplyKeyboardMarkup([['Admin', 'Pembeli'], ['Keluar']], resize_keyboard=True)

def get_admin_keyboard():
    return ReplyKeyboardMarkup([
        ['Tambah Barang', 'Edit Stok'],
        ['Hapus Barang', 'Lihat Barang'],
        ['Laporan Harian', 'Laporan Bulanan'],
        ['Kembali']
    ], resize_keyboard=True)

def get_pembeli_keyboard():
    return ReplyKeyboardMarkup([['Lihat Barang', 'Beli Barang'], ['Kembali']], resize_keyboard=True)

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