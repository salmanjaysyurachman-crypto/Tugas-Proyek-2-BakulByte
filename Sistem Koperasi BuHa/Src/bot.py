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