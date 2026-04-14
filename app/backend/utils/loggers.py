import logging

logging.basicConfig(
    filename="qab_logs.txt",
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )

def get_logger(name: str):
    return logging.getLogger(name) 

logger = get_logger(__name__)