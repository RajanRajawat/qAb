import os
from dotenv import load_dotenv
from utils.loggers import logger

load_dotenv()


load_jwt_secret_key = os.getenv('SECRET_VALUE')
load_groq_api = os.getenv("GROQ_API_KEY")
load_gemini_api = os.getenv("GOOGLE_API_KEY")
load_tavily_api  = os.getenv("TAVILY_API_KEY")
load_hf_api = os.getenv("HF_TOKEN")
