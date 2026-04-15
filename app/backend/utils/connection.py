from pymongo import MongoClient

def validate_mongo(uri):
    try:
        client = MongoClient(uri, serverSelectionTimeoutMS=3000)
        client.server_info()
        return True
    except:
        return False
    


import psycopg2

def validate_postgres(uri):
    try:
        conn = psycopg2.connect(uri)
        conn.close()
        return True
    except:
        return False