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
