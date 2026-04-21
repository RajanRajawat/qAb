from pymongo import MongoClient
import psycopg2

def validate_mongo(uri):
    try:
        client = MongoClient(uri, serverSelectionTimeoutMS=3000)
        client.server_info()
        return True
    except:
        return False
    
def validate_postgres(uri):
    try:
        # Standardize URI for psycopg2: strip SQLAlchemy driver suffix if present
        # (e.g. 'postgresql+psycopg2://' -> 'postgresql://')
        if "://" in uri:
            scheme, rest = uri.split("://", 1)
            if "+" in scheme:
                uri = f"{scheme.split('+')[0]}://{rest}"
        
        conn = psycopg2.connect(uri)
        conn.close()
        return True
    except:
        return False