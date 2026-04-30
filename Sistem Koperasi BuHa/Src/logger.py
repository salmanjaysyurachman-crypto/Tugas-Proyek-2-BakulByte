import logging
import traceback
import os
from logging.handlers import RotatingFileHandler
from datetime import datetime
from functools import wraps

LOG_FILE        = "error_log.txt"
MAX_BYTES       = 5 * 1024 * 1024   # 5 MB sebelum file dirotasi
BACKUP_COUNT    = 3                  # simpan hingga 3 file lama
ADMIN_ID        = os.getenv("ADMIN_ID")

# ── Setup root logger ──────────────────────────────────────────
def setup_logging() -> logging.Logger:
    """
    Inisialisasi logging ke console DAN file error_log.txt.
    Panggil sekali saja di main() sebelum bot dijalankan.
    """
    fmt = logging.Formatter(
        fmt="[%(asctime)s] %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

        # ── Handler: Console (INFO ke atas) ───────────────────────
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(fmt)

        # ── Handler: File (WARNING ke atas, dengan rotasi) ────────
    file_handler = RotatingFileHandler(
        LOG_FILE,
        maxBytes=MAX_BYTES,
        backupCount=BACKUP_COUNT,
        encoding="utf-8"
    )
    file_handler.setLevel(logging.WARNING)
    file_handler.setFormatter(fmt)

       # ── Root logger ───────────────────────────────────────────
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(console_handler)
    root.addHandler(file_handler)

    return root

# ── Kirim notifikasi crash ke Admin Telegram ──────────────────
async def kirim_notif_crash(
    bot,
    exc: Exception,
    konteks: str = "tidak diketahui",
    user_id: str | int | None = None,
    extra: str = ""
) -> None:
    """
    Mengirim pesan error ke Admin Telegram.

    Args:
        bot      : objek telegram.Bot
        exc      : exception yang terjadi
        konteks  : nama fungsi / handler tempat error terjadi
        user_id  : ID user yang sedang berinteraksi (opsional)
        extra    : informasi tambahan bebas (opsional)
    """
    if not ADMIN_ID:
        logging.getLogger(__name__).warning(
            "ADMIN_ID tidak diset — notifikasi crash tidak dikirim."
        )
        return
    tb = traceback.format_exc()
    # Potong traceback agar tidak melampaui batas 4096 karakter Telegram
    if len(tb) > 900:
        tb = "..." + tb[-900:]

    waktu = datetime.now().strftime("%d %b %Y, %H:%M:%S")

    pesan = (
        "🚨 CRITICAL ERROR — BakulByte Bot\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🕐 Waktu   : {waktu}\n"
        f"📍 Konteks : {konteks}\n"
        f"👤 User ID : {user_id or 'N/A'}\n"
        f"❌ Error   : {type(exc).__name__}: {exc}\n"
    )
    if extra:
        pesan += f"ℹ️ Info    : {extra}\n"

    pesan += f"\n```\n{tb}\n```"

    try:
        await bot.send_message(
            chat_id=ADMIN_ID,
            text=pesan,
            parse_mode="Markdown"
        )
    except Exception as send_err:
        logging.getLogger(__name__).error(
            f"Gagal mengirim notifikasi crash ke Admin: {send_err}"
        ) # ── Decorator: otomatis tangkap & laporkan error di handler ───
def catch_and_report(konteks: str = ""):
    """
    Decorator untuk handler bot.
    Menangkap semua exception, mencatatnya ke log, dan
    mengirim notifikasi ke Admin — tanpa menghentikan bot.

    Pemakaian:
        @catch_and_report("nama_handler")
        async def handler(update, context): ...
    """
def decorator(func):
        @wraps(func)
        async def wrapper(update, context, *args, **kwargs):
            nama = konteks or func.__name__
            user_id = None
            try:
                if update and update.effective_user:
                    user_id = update.effective_user.id
                return await func(update, context, *args, **kwargs)
            except Exception as exc:
                logger = logging.getLogger(func.__module__)
                logger.error(
                    f"[{nama}] user_id={user_id} | "
                    f"{type(exc).__name__}: {exc}",
                    exc_info=True
                )
                await kirim_notif_crash(
                    bot=context.bot,
                    exc=exc,
                    konteks=nama,
                    user_id=user_id
                )
                # Beri tahu user bahwa ada masalah (bukan pesan teknis)
                try:
                    target = (
                        update.callback_query.message
                        if update.callback_query
                        else update.message
                    )
