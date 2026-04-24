# qAb

qAb stands for **Quick Agent Builder**.

It is a full-stack app for building practical AI agents with:

- user auth
- agent creation and management
- knowledge bases for RAG
- linked MongoDB / PostgreSQL databases
- read-only data queries
- tool connections like Gmail and web search
- a built-in browser chat UI

The backend is **FastAPI**, the frontend is **plain HTML/CSS/JavaScript**, and the frontend is served directly by the backend.

## What qAb Can Do

- register and log in users
- create agents using Groq or Gemini models
- attach a knowledge base to an agent
- upload `.txt` and `.pdf` files for RAG
- connect custom MongoDB and PostgreSQL databases
- create read-only data queries from selected tables or collections
- connect Gmail through Google OAuth
- use built-in web search through Tavily
- chat with agents from the built-in UI

## Tech Stack

### Backend

- FastAPI
- Motor / PyMongo
- LangChain
- LangGraph
- Groq
- Google Gemini
- Hugging Face embeddings
- MongoDB Atlas Vector Search
- PGVector / PostgreSQL

### Frontend

- HTML
- CSS
- vanilla JavaScript

## Project Structure

```text
app/
  backend/
    main.py
    requirements.txt
    database/
      db.py
      models.py
    src/
      agent.py
      custom_db.py
      data_query.py
      knowledge_base.py
      login.py
      register.py
      runner.py
      tool_config.py
      tools.py
    utils/
      agent_helpers.py
      connection.py
      data_query_helpers.py
      env_loaders.py
      general.py
      knowledge_base_helpers.py
      loggers.py
      response.py
      runner_helpers.py
      security.py
      tool_helpers.py
      users.py
  frontend/
    index.html
    app.js
    api.js
    style.css
    media/
other/
  images/
  report/
```

## How the App Works

### Main backend entry

- `app/backend/main.py`

This file:

- creates the FastAPI app
- mounts the frontend static files
- registers all route modules
- adds global validation / HTTP / unhandled exception handlers

### Main frontend entry

- `app/frontend/index.html`
- `app/frontend/app.js`
- `app/frontend/api.js`

The frontend is a single-page app with hash-based routing.

## Core Features

### 1. Agents

Agents are configured with:

- name
- description
- role
- instructions
- LLM provider
- LLM model
- temperature
- optional knowledge base
- optional data query
- optional tools

Current provider / model combinations exposed in the app:

- `groq` -> `llama-3.1-8b-instant`
- `gemini` -> `gemini-2.5-flash`

### 2. Knowledge Bases

Knowledge bases let you upload:

- `.txt`
- `.pdf`

Each KB stores:

- metadata in the app Mongo database
- embeddings in either:
  - the default Mongo vector store, or
  - a linked custom Mongo / PostgreSQL database

Current embedding model options:

- `sentence-transformers/all-MiniLM-L6-v2`
- `sentence-transformers/paraphrase-MiniLM-L3-v2`

### 3. Custom Databases

Users can link:

- MongoDB
- PostgreSQL / Supabase

These linked databases are used for:

- knowledge base vector storage
- data query inspection and read-only access

### 4. Data Queries

Data Queries let you:

- inspect a linked database
- select only the tables / collections an agent should see
- describe sources and columns
- give the agent safe read-only structured access

### 5. Tools

Current tool catalog in the app:

- `web_search`
- `gmail`

`web_search` is available through Tavily.

`gmail` is connected through Google OAuth and supports:

- `GMAIL_FETCH_EMAILS`
- `GMAIL_REPLY_TO_THREAD`
- `GMAIL_SEND_EMAIL`

### 6. Agent Chat

Agent chat is available in the built-in UI.

Important:

- chat memory is **session-based**
- it is stored in the browser `sessionStorage`
- it is **not** persisted to MongoDB anymore

That means:

- refresh keeps it in the same browser session
- logout clears it
- closing the tab/session clears it

## Runtime Storage

### App Mongo database

The app always needs a primary MongoDB connection through `MONGO_URI`.

Current internal Mongo database / collection usage:

- database: `qab`
- default vector collection: `qab.embeddings`

Mongo stores:

- users
- agents
- custom DB metadata
- knowledge base metadata
- data query metadata
- tool connections

### Custom Mongo vector store

When a KB uses a linked Mongo database for vectors, embeddings are written to:

- database: `qab_test`
- collection: `embeddings`

### PostgreSQL vector store

When a KB uses PostgreSQL / Supabase for vectors, embeddings are handled through PGVector / LangChain integration.

## Environment Variables

Create a `.env` file at the repo root.

### Required for the app to start correctly

```env
SECRET_VALUE=replace_with_a_long_random_secret
MONGO_URI=mongodb+srv://username:password@cluster.mongodb.net/?appName=YourApp
```

### Required depending on the features you use

```env
GROQ_API_KEY=your_groq_key
GOOGLE_API_KEY=your_google_ai_key
TAVILY_API_KEY=your_tavily_key
HF_TOKEN=your_huggingface_token
GOOGLE_CLIENT_ID=your_google_oauth_client_id
GOOGLE_CLIENT_SECRET=your_google_oauth_client_secret
```

### Meaning

- `SECRET_VALUE`: JWT signing secret
- `MONGO_URI`: primary Mongo connection for the app itself
- `GROQ_API_KEY`: needed for Groq-backed agents
- `GOOGLE_API_KEY`: needed for Gemini-backed agents
- `TAVILY_API_KEY`: needed for web search
- `HF_TOKEN`: needed for embeddings / KB vector search
- `GOOGLE_CLIENT_ID`: needed for Gmail OAuth
- `GOOGLE_CLIENT_SECRET`: needed for Gmail OAuth

## Installation

From the repo root:

```powershell
cd app/backend
python -m venv .venv
```

Activate the environment.

### Windows PowerShell

```powershell
.venv\Scripts\Activate.ps1
```

### macOS / Linux

```bash
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

## Run the App

From `app/backend`:

```bash
uvicorn main:app --reload
```

The app will be available at:

- UI: `http://localhost:8000/`
- Health check: `http://localhost:8000/health`

No separate frontend dev server is required.

## First-Time Flow

1. Start the backend
2. Open `http://localhost:8000/`
3. Register
4. Log in
5. Link a database if needed
6. Create a knowledge base if you want document RAG
7. Create a data query if you want read-only DB access
8. Create an agent
9. Attach KB / Data Query / tools as needed
10. Open chat and test it

## MongoDB Setup Notes

If you want MongoDB-based Data Query access, the linked Mongo URI must include a database name.

Example:

```text
mongodb+srv://username:password@cluster.mongodb.net/YourDatabaseName?appName=YourApp
```

If the database name is missing, Data Query inspection will not know which Mongo database to browse.

## MongoDB Atlas Vector Search Setup

For vector search, the app expects the index name:

- `vector_index`

Use this index JSON:

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

## PostgreSQL / Supabase Setup

Enable pgvector first:

```sql
create extension if not exists vector with schema extensions;
```

Use a valid PostgreSQL connection string, for example:

```text
postgresql://postgres:password@host:5432/postgres
```

or

```text
postgresql+psycopg2://postgres:password@host:5432/postgres
```

The backend normalizes SQLAlchemy-style suffixes when needed.

## API Route Groups

Main route groups:

- `/auth`
- `/agent`
- `/knowledge-base`
- `/custom-db`
- `/data-query`
- `/chat`
- `/tools`
- `/health`

## Response Format

The backend uses a shared response envelope:

### Success

```json
{
  "success": true,
  "status": 200,
  "data": {},
  "message": "Success"
}
```

### Error

```json
{
  "success": false,
  "status": 400,
  "data": null,
  "message": "Error"
}
```

Validation errors also use the same envelope, with validation details inside `data`.

## Notes About the Frontend

- the frontend is not React / Vue
- routing is hash-based
- `app.js` is the main controller
- `api.js` centralizes HTTP handling
- assets are served from `/static`

## Security Notes

This repo should not contain real production secrets.

If any real credentials were ever used in:

- Mongo URIs
- JWT secret
- Groq key
- Google API key
- Tavily key
- Hugging Face token
- Google OAuth credentials
- Supabase / Postgres URIs

rotate them.

Current production-hardening gaps worth keeping in mind:

- CORS is still open with `allow_origins=["*"]`
- linked external DB connection strings are not encrypted at rest
- database-level unique indexes should be added for stronger integrity

## Troubleshooting

### App starts but auth / API calls fail

Check:

- `.env` exists
- `SECRET_VALUE` is set
- `MONGO_URI` is valid
- backend is running from `app/backend`

### Knowledge base upload works but search fails

Check:

- `HF_TOKEN` is set
- the vector index exists
- the vector dimension is `384`
- the right DB was chosen for the KB

### Mongo Data Query inspection fails

Most common cause:

- linked Mongo URI does not include a database name

### Gmail connect flow fails

Check:

- `GOOGLE_CLIENT_ID`
- `GOOGLE_CLIENT_SECRET`
- callback URL matches the app URL
- Google OAuth consent and Gmail scopes are configured correctly

### Frontend changes do not appear

Do a hard refresh in the browser.

## Development Notes

- backend logs are written to `app/backend/qab_logs.txt`
- knowledge base file processing runs in a background task
- the frontend and backend are deployed together from the FastAPI app

## Quick Start Checklist

1. Create `.env`
2. Set `SECRET_VALUE`
3. Set `MONGO_URI`
4. Set at least one LLM key:
   - `GROQ_API_KEY` or `GOOGLE_API_KEY`
5. Set `HF_TOKEN` if using Knowledge Bases
6. Set `TAVILY_API_KEY` if using web search
7. Set Google OAuth vars if using Gmail
8. `cd app/backend`
9. create / activate virtual environment
10. `pip install -r requirements.txt`
11. `uvicorn main:app --reload`
12. open `http://localhost:8000/`
