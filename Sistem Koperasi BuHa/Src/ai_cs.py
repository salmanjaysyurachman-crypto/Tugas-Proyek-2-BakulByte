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
