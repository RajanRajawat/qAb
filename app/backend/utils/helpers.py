
import logging, os, bcrypt, jwt, datetime
from dotenv import load_dotenv
from pydantic import EmailStr
from database.db import users_collection
from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jwt import ExpiredSignatureError, InvalidTokenError


security = HTTPBearer()
load_dotenv()

    
#- Logger
logging.basicConfig(
    filename="qab_logs.txt",
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

def get_logger(name: str):
    return logging.getLogger(name) 

logger = get_logger(__name__)


#- Env Loaders


def load_jwt_secret_key():
    secret_key = os.getenv('SECRET_VALUE')
    if not secret_key:
        logger.error(f"JWT secret key not found in .env file")
        return None
    logger.info(f"JWT secret key loaded successfully")
    return secret_key



#- String Operations
def strip_string(s: str):
    if isinstance(s, str):
        return s.strip()
    return s



#- JWT Password
def hash_password(password: str) -> str:
    logger.info(f"Password hashing started")
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    logger.info(f"Password verification started")
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))


SECRET_KEY = load_jwt_secret_key()
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


#- Email

MAIL_USERNAME=os.getenv("MAIL_USERNAME")
if not MAIL_USERNAME:
    raise RuntimeError("MAIL_USERNAME is not set in environment variables.")
MAIL_FROM=os.getenv("MAIL_FROM")
if not MAIL_FROM:
    raise RuntimeError("MAIL_FROM is not set in environment variables.")
GMAIL_APP_PWD=os.getenv("GMAIL_APP_PWD")
if not GMAIL_APP_PWD:
    raise RuntimeError("GMAIL_APP_PWD is not set in environment variables.")

conf = ConnectionConfig(
    MAIL_USERNAME=MAIL_USERNAME,
    MAIL_PASSWORD=GMAIL_APP_PWD,
    MAIL_FROM=MAIL_FROM,
    MAIL_PORT=587,
    MAIL_SERVER="smtp.gmail.com",
    MAIL_STARTTLS=True,
    MAIL_SSL_TLS=False,
    USE_CREDENTIALS=True
)

async def send_email(subject: str, email_to, body: str, attachments=None):
    if isinstance(email_to, str):
        recipients = [email_to.strip()] if email_to.strip() else []
    else:
        recipients = [str(email).strip() for email in email_to if str(email).strip()]

    if not recipients:
        logger.warning(f"Skipped email send for subject '{subject}' because recipient list was empty.")
        return False

    message = MessageSchema(
        subject=subject,
        recipients=recipients,
        body=body,
        attachments=attachments or [],
        subtype=MessageType.html
    )

    try:
        fm = FastMail(conf)
        await fm.send_message(message)

        logger.info(f"Email sent successfully to: {message.recipients} | Subject: {message.subject}")
        return True

    except Exception as e:
        logger.error(f"Failed to send email to {message.recipients} | Error: {str(e)}")
        return False



#- User
async def get_user_by_email(email: EmailStr):
    logger.info(f"Fetching user by email: {email}")
    user_data = await users_collection.find_one({'email': email})
    if user_data:
        logger.info(f"User found for email: {email}")
        return user_data
    else:
        logger.warning(f"User not found for email: {email}")
        return False


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        logger.info(f"Current user token validation started")
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=["HS256"])
        logger.info(f"Current user token validated successfully for {payload['email']}")
        return payload
    except ExpiredSignatureError:
        logger.warning(f"Current user token validation failed because token expired")
        raise HTTPException(status_code=401, detail={"message": "Token has expired, please login again."})
    except InvalidTokenError:
        logger.warning(f"Current user token validation failed because token was invalid")
        raise HTTPException(status_code=401, detail={"message": "Invalid token."})
    

















    
