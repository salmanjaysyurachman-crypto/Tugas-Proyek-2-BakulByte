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

def get_client() -> Groq:
    global _client
    if _client is None:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY belum diset di file .env!")
        _client = Groq(api_key=api_key)
    return _client
