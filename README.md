
# QAB

Create Agent with Ease!

vector_index_qab



{
  "fields": [
    {
      "type": "vector",
      "path": "embedding",
      "numDimensions": 384,
      "similarity": "cosine"
    },
    {
      "type": "filter",
      "path": "owner_id"
    }
  ]
}


postgresql+psycopg2://postgres.bnzahq................supabase.com:5432/postgres


{
  "fields": [
    {
      "numDimensions": 384,
      "path": "embedding",
      "similarity": "cosine",
      "type": "vector"
    },
    {
      "path": "owner_id",
      "type": "filter"
    },
    {
      "path": "knowledge_base_id",
      "type": "filter"
    }
  ]
}













