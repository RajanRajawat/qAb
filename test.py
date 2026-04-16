


#~ #SupaBase Connection String Testing!
# import psycopg2
# conn = psycopg2.connect("postgresql+psycopg2://postgres.bnzahqrwkxkxiritxueq:pwd@aws-1-ap-southeast-2.pooler.supabase.com:5432/postgres")
# cur = conn.cursor()
# cur.execute("SELECT extname FROM pg_extension WHERE extname = 'vector';")
# print(cur.fetchone())  # Should print ('vector',)


from langchain_postgres.vectorstores import PGVector
from langchain_huggingface import HuggingFaceEmbeddings

connection_string = "postgresql+psycopg2://postgres.bnzahqrwkxkxiritxueq:pwd@aws-1-ap-southeast-2.pooler.supabase.com:5432/postgres"

embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

store = PGVector(
    embeddings=embeddings,
    collection_name="embeddings",
    connection=connection_string,
    use_jsonb=True,
)
print("✅ Connected successfully!")