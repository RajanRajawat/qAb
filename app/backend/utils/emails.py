

import os
from dotenv import load_dotenv
from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType
from utils.loggers import logger
from pydantic import SecretStr, NameEmail


load_dotenv()



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
    MAIL_PASSWORD=SecretStr(GMAIL_APP_PWD),
    MAIL_FROM=MAIL_FROM,
    MAIL_PORT=587,
    MAIL_SERVER="smtp.gmail.com",
    MAIL_STARTTLS=True,
    MAIL_SSL_TLS=False,
    USE_CREDENTIALS=True
)

async def send_email(subject: str, email_to, body: str, attachments=None):
    if isinstance(email_to, str):
        recipients = ([email_to.strip()] if email_to.strip() else [])
    else:
        recipients = [str(email).strip() for email in email_to if str(email).strip()]

    if not recipients:
        logger.warning(f"Skipped email send for subject '{subject}' because recipient list was empty.")
        return False

    message = MessageSchema(
        subject=subject,
        recipients=recipients, # type: ignore #!fix later
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











