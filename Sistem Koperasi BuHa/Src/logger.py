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