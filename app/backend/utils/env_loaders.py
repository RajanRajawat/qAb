

#~ Env Loaders                                          
#: Todo:                                                
#! Bugs:                                                
#- Notes:                                               




import os
from dotenv import load_dotenv
from utils.loggers import logger


load_dotenv()


def load_jwt_secret_key():
    secret_key = os.getenv('SECRET_VALUE')
    if not secret_key:
        logger.error(f"JWT secret key not found in .env file")
        return None
    logger.info(f"JWT secret key loaded successfully")
    return secret_key

def load_groq_api():
    api = os.getenv("GROQ_API_KEY")
    if not api:
        logger.error("GROQ API key not found in .env file")
        raise ValueError("Missing GROQ_API_KEY in .env")
    logger.info("GROQ API key loaded successfully")
    return api

def load_gemini_api():
    api = os.getenv("GOOGLE_API_KEY")
    if not api:
        logger.error("GOOGLE API key not found in .env file")
        raise ValueError("Missing GOOGLE_API_KEY in .env")
    logger.info("GOOGLE API key loaded successfully")
    return api


def load_tavily_api():
    api = os.getenv("TAVILY_API_KEY")
    if not api:
        logger.error("Tavily API key not found in .env file")
        raise ValueError("Missing TAVILY_API_KEY in .env")
    logger.info("Tavily API key loaded successfully")
    return api




