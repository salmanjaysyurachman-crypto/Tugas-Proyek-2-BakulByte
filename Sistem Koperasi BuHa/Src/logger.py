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