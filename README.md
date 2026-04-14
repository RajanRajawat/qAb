
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