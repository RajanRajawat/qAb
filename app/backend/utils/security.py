

from utils.loggers import logger
import os, bcrypt, jwt, datetime
from utils.env_loaders import load_jwt_secret_key



def hash_password(password: str) -> str:
    logger.info(f"Password hashing started")
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    logger.info(f"Password verification started")
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

SECRET_KEY = str(load_jwt_secret_key)
def generate_token(user_data, token_type: str, time):
    logger.info(f"{token_type.capitalize()} token generation started for {user_data['email']}")
    payload = {
        '_id': str(user_data['_id']),  
        'name': user_data['name'],
        'email': user_data['email'],
        'token_type': token_type,
        'exp': (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=time))
    }
    logger.info(f"{token_type.capitalize()} token generated successfully for {user_data['email']}")
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")

#: Create one function to encrypt DB strings, also decrypt!
