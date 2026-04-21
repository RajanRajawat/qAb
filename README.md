# QAB

QAB is a full-stack Quick Agent Builder. It lets you:

- register and log in from a browser UI
- create agents backed by Groq or Gemini
- attach a Knowledge Base to an agent for RAG
- link custom MongoDB or PostgreSQL/Supabase databases for vector storage
- create Data Queries from linked databases so agents can read selected tables or collections
- run chat sessions against agents from the built-in frontend

The frontend is served directly by the FastAPI backend, so one backend process runs the whole app.

## Table of Contents

1. Project Structure
2. What You Need Before Running
3. Environment Variables
4. Installation
5. How to Run the Project
6. First-Time Setup Flow
7. Custom DB Setup
8. MongoDB Atlas Vector Search Setup
9. PostgreSQL / Supabase Setup
10. Knowledge Base Notes
11. Data Query Notes
12. Tooling Notes
13. Troubleshooting
14. Security Notes

## Project Structure

```text
app/
  backend/
    main.py
    requirements.txt
    database/
    src/
    utils/
  frontend/
    index.html
    app.js
    style.css
```

Important backend modules:

- `app/backend/main.py`: FastAPI entrypoint
- `app/backend/database/db.py`: MongoDB app database and default vector store connections
- `app/backend/src/knowledge_base.py`: Knowledge Base routes
- `app/backend/src/custom_db.py`: linked database routes
- `app/backend/src/data_query.py`: Data Query routes
- `app/backend/src/runner.py`: chat execution routes
- `app/backend/src/tools.py`: agent tool registry

## What You Need Before Running

Install the following on your machine:

- Python 3.11 recommended
- pip
- access to a MongoDB database for the app's primary storage
- at least one LLM API key:
  - `GROQ_API_KEY`, or
  - `GOOGLE_API_KEY`
- `HF_TOKEN` for embeddings if you want Knowledge Base features
- `TAVILY_API_KEY` if you want the web search tool

Optional but strongly recommended for custom vector storage:

- MongoDB Atlas cluster if you want custom MongoDB vector storage
- PostgreSQL or Supabase if you want PGVector-backed storage

## Environment Variables

Create a `.env` file at the repo root.

Minimum variables used by the current codebase:

```env
SECRET_VALUE=replace_with_a_long_random_secret
MONGO_URI=mongodb+srv://username:password@cluster.mongodb.net/?appName=YourApp

GROQ_API_KEY=your_groq_key
GOOGLE_API_KEY=your_google_ai_key
TAVILY_API_KEY=your_tavily_key
HF_TOKEN=your_huggingface_token
```

Variable meaning:

- `SECRET_VALUE`: JWT signing secret
- `MONGO_URI`: base Mongo connection used by the app for users, agents, KB metadata, Data Queries, chat history, and the default vector collection
- `GROQ_API_KEY`: needed if you use Groq models
- `GOOGLE_API_KEY`: needed if you use Gemini models
- `TAVILY_API_KEY`: needed if agents use the web search tool
- `HF_TOKEN`: needed for document embeddings and Knowledge Base vector search

Notes:

- the backend stores its core application data in Mongo database `qab`
- the default vector collection is `qab.embeddings`
- if you do not use Gemini, the Google key can stay unset
- if you do not use web search, the Tavily key can stay unset
- if you do not use Knowledge Bases, the Hugging Face token can stay unset

## Installation

From the repo root:

```bash
cd app/backend
python -m venv .venv
```

Activate the virtual environment.

Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

macOS / Linux:

```bash
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

## How to Run the Project

From `app/backend`:

```bash
uvicorn main:app --reload
```

The application will be available at:

- App UI: `http://localhost:8000/`
- Health check: `http://localhost:8000/health`

Because the frontend is mounted as static files by FastAPI, you do not need a separate frontend server.

## First-Time Setup Flow

Once the app is running:

1. Open `http://localhost:8000/`
2. Register a user
3. Log in
4. Link a custom database if needed
5. Create a Knowledge Base if you want document-based RAG
6. Create a Data Query if you want an agent to read selected DB tables or collections
7. Create an agent
8. Attach:
   - a Knowledge Base, and/or
   - a Data Query, and/or
   - the web search tool
9. Open chat and test the agent

## Custom DB Setup

The app supports linking:

- MongoDB
- PostgreSQL

These linked databases are used for two different features:

1. Knowledge Base vector storage
2. Data Query source inspection and read-only agent access

### Important Difference Between the App Database and Linked Databases

The app always needs `MONGO_URI` in `.env` for its own internal storage.

Linked databases are separate user-managed databases added from the UI under `Databases`.

### Valid MongoDB Connection URI

For MongoDB, use a real connection string such as:

```text
mongodb+srv://username:password@cluster.mongodb.net/YourDatabaseName?appName=YourApp
```

or

```text
mongodb://username:password@host:27017/YourDatabaseName
```

Important:

- If you want to use MongoDB for Data Query, the URI must include a database name.
- Example:
  - valid: `mongodb+srv://user:pass@cluster.mongodb.net/Ecom_Prod?appName=MyApp`
  - not good for Data Query: `mongodb+srv://user:pass@cluster.mongodb.net/?appName=MyApp`

Why this matters:

- the backend inspects Mongo collections from the database name embedded in the URI
- without that database name, Mongo Data Query cannot know which DB to browse

### Valid PostgreSQL / Supabase Connection URI

Examples:

```text
postgresql://postgres:password@host:5432/postgres
```

```text
postgres://postgres:password@host:5432/postgres
```

```text
postgresql+psycopg2://postgres:password@host:5432/postgres
```

The backend normalizes SQLAlchemy-style driver suffixes, so `postgresql+psycopg2://...` is accepted.

### What Happens When You Link a MongoDB Custom DB

For custom Mongo Knowledge Base storage, the backend writes embeddings into:

```text
qab_test.embeddings
```

inside the linked Mongo cluster.

That means your linked Mongo DB must allow:

- creating or using database `qab_test`
- creating or using collection `embeddings`
- vector search on that collection

## MongoDB Atlas Vector Search Setup

If you use MongoDB Atlas for vector storage, create a vector search index on the collection used for embeddings.

Current backend expectation:

- database: `qab_test` for linked Mongo custom vector storage
- collection: `embeddings`
- index name: `vector_index`

For the default built-in Mongo vector store used by the app itself:

- database: `qab`
- collection: `embeddings`
- index name: `vector_index`

### Atlas Vector Search JSON

Use this JSON in the Atlas Search / Vector Search index editor:

```json
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
    },
    {
      "type": "filter",
      "path": "knowledge_base_id"
    }
  ]
}
```

### Why `384` Dimensions

The current embedding models configured in the backend are:

- `sentence-transformers/all-MiniLM-L6-v2`
- `sentence-transformers/paraphrase-MiniLM-L3-v2`

Both are used as 384-dimensional embeddings in this project.

## PostgreSQL / Supabase Setup

If you want to use PostgreSQL or Supabase for vector storage, you need `pgvector`.

### Required SQL

Run this first:

```sql
create extension if not exists vector with schema extensions;
```

If your environment expects the extension without schema qualification, also verify what your Postgres provider supports.

### Supabase Notes

Supabase works as long as:

- the connection string is valid
- the user can create and write to the required tables
- the vector extension is enabled

Use a connection string like:

```text
postgresql+psycopg2://postgres:password@your-project.pooler.supabase.com:5432/postgres
```

or a direct Postgres URL if you prefer.

### PGVector Notes for This Project

The backend uses `langchain-postgres` and manages embedding storage through PGVector integration.

For Postgres-backed Knowledge Bases:

- embeddings are written through `PGVector.from_documents(...)`
- similarity search is done through `PGVector(...)`

You do not need to manually create the LangChain tables before first use if the DB user has the right permissions, but the vector extension must exist.

## Knowledge Base Notes

Knowledge Bases support:

- `.txt`
- `.pdf`

Flow:

1. Create a Knowledge Base
2. Choose:
   - default Mongo vector store, or
   - a linked custom DB
3. Upload files
4. The backend chunks and embeds them in a background task
5. Agents can then use that KB during chat

### Embedding Models Available in the UI

- `sentence-transformers/all-MiniLM-L6-v2`
- `sentence-transformers/paraphrase-MiniLM-L3-v2`

### Default Storage Behavior

If you choose the default DB for a Knowledge Base:

- KB metadata is stored in app Mongo database `qab`
- embeddings are stored in `qab.embeddings`

## Data Query Notes

Data Query gives an agent read-only access to selected tables or collections from a linked DB.

Flow:

1. Link a database
2. Open `Data Queries`
3. Create a Data Query
4. Select a linked DB
5. Load tables or collections
6. Select only the sources you want the agent to access
7. Add source descriptions and column or field descriptions
8. Attach the Data Query to an agent

### MongoDB Data Query Requirements

- the linked Mongo URI must include the database name
- the agent only reads the selected collections
- the tool expects a Mongo query payload

Accepted Mongo payload patterns are now more forgiving:

- valid JSON
- fenced JSON blocks
- Python-style dict syntax that can be safely parsed

Example Mongo `find` payload:

```json
{
  "operation": "find",
  "filter": {},
  "projection": {
    "name": 1,
    "email": 1
  },
  "limit": 20
}
```

Example Mongo `aggregate` payload:

```json
{
  "operation": "aggregate",
  "pipeline": [
    { "$match": {} },
    { "$limit": 20 }
  ]
}
```

### PostgreSQL Data Query Rules

- only read-only SQL is allowed
- queries must start with `SELECT` or `WITH`
- write operations such as `INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `TRUNCATE`, `CREATE`, `GRANT`, `REVOKE` are blocked
- the query must reference only allowed tables from the Data Query configuration

## Tooling Notes

Current agent tool support in the UI/backend:

- `web_search`

The web search tool uses Tavily and reads:

```env
TAVILY_API_KEY=your_tavily_key
```

## Models Supported

Current LLM providers and models exposed by the backend:

- Groq
  - `llama-3.1-8b-instant`
- Gemini
  - `gemini-2.5-flash`

## How to Use the App End to End

### Option A: Default Mongo for KB

1. set `MONGO_URI`
2. start the app
3. register and log in
4. create a Knowledge Base with `Default DB`
5. upload files
6. create an agent
7. attach the Knowledge Base
8. chat with the agent

### Option B: Custom Mongo for KB and Data Query

1. prepare a MongoDB Atlas cluster
2. create vector search index `vector_index` on `qab_test.embeddings`
3. link Mongo from the UI using a URI that includes a database name
4. create a Knowledge Base using that linked DB
5. create a Data Query from the same linked DB if you want collection access
6. attach the KB and/or Data Query to an agent
7. chat with the agent

### Option C: PostgreSQL / Supabase for KB and Data Query

1. create or choose a Postgres database
2. enable `pgvector`
3. link the DB from the UI
4. create a Knowledge Base using that linked DB
5. create a Data Query from the same linked DB if you want table access
6. attach the KB and/or Data Query to an agent
7. chat with the agent

## Troubleshooting

### App opens but actions fail with auth or API errors

Check:

- `.env` values are present
- backend is running from `app/backend`
- browser is opening `http://localhost:8000/`

### MongoDB custom DB links successfully but Data Query fails

Most likely cause:

- the Mongo URI does not include a database name

Use:

```text
mongodb+srv://user:pass@cluster.mongodb.net/YourDatabaseName?appName=YourApp
```

### MongoDB vector search fails

Check:

- the collection really contains embeddings
- the Atlas index name is `vector_index`
- the index JSON includes filters for `owner_id` and `knowledge_base_id`
- the embedding dimension is `384`

### Supabase / Postgres KB storage fails

Check:

- `vector` extension is enabled
- the connection URI is valid
- the DB user has create/read/write permissions

### Agent chat crashes when using Mongo Data Query

This usually means the tool input was malformed.

The backend now tries to parse:

- plain JSON
- fenced JSON
- Python-style dict text

If it still fails, inspect the backend logs and compare the tool payload with the Mongo examples in this README.

### Frontend looks stale after changes

Do a hard refresh:

- Windows: `Ctrl + F5`

The frontend assets are cache-busted through versioned static paths.

## API Summary

Main route groups:

- `/auth`
- `/agent`
- `/knowledge-base`
- `/custom-db`
- `/data-query`
- `/chat`
- `/health`

## Security Notes

Do not commit real secrets to source control.

If this repo has ever contained live values for:

- MongoDB URIs
- JWT secret
- Groq keys
- Google keys
- Tavily keys
- Hugging Face tokens
- Supabase credentials

rotate them.

Recommended production improvements:

- restrict CORS to known frontend origins
- use a separate production `.env`
- use least-privilege DB users
- store secrets in a proper secrets manager
- remove any development credentials from tracked files

## Development Notes

- the frontend is plain static HTML/CSS/JS served by FastAPI
- the backend is FastAPI plus MongoDB, LangChain, Hugging Face embeddings, and optional PGVector
- Knowledge Base file processing runs in the background
- background email notifications have been removed from the current codebase

## Quick Start Checklist

1. Create `.env`
2. Set `SECRET_VALUE`
3. Set `MONGO_URI`
4. Set at least one LLM key:
   - `GROQ_API_KEY` or `GOOGLE_API_KEY`
5. Set `HF_TOKEN` if using Knowledge Bases
6. Set `TAVILY_API_KEY` if using web search
7. `cd app/backend`
8. create and activate a virtual environment
9. `pip install -r requirements.txt`
10. `uvicorn main:app --reload`
11. open `http://localhost:8000/`

