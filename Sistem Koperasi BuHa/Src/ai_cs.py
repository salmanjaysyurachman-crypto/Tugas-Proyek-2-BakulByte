import os
import logging
from groq import Groq
from dotenv import load_dotenv
from database import get_db
from datetime import datetime

load_dotenv()