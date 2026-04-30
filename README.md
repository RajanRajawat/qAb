# qAb - Quick Agent Builder

qAb is a full-stack app for creating practical AI agents with optional document RAG, read-only database access, and tool integrations.

The backend is built with FastAPI. The frontend is a plain HTML/CSS/JavaScript single-page app served directly by the backend.

## Features

- User registration and login with JWT auth
- Agent creation, update, delete, detail, and chat
- Groq and Google Gemini model support
- Knowledge Bases with `.txt` and `.pdf` uploads
- MongoDB Atlas Vector Search and PostgreSQL PGVector support
- Linked MongoDB and PostgreSQL databases
- Read-only Data Queries over selected tables or collections
- Tavily web search tool
- Gmail integration through Google OAuth
- Browser chat UI with session-scoped memory
- Chat request timeout handling on frontend and backend

## Tech Stack

Backend:

- FastAPI
- Motor and PyMongo
- MongoDB
- LangChain and LangGraph
- Groq
- Google Gemini
- Hugging Face embeddings
- MongoDB Atlas Vector Search
- PostgreSQL / PGVector

Frontend:

- HTML
- CSS
- Vanilla JavaScript modules

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
  report/
README.md
```

## How It Works

1. A user registers and logs in.
2. The user can link a MongoDB or PostgreSQL database.
3. The user can create a Knowledge Base and upload files for RAG.
4. The user can create a Data Query that exposes only selected DB tables or collections.
5. The user can connect tools such as Gmail.
6. The user creates an agent with a provider, model, instructions, optional KB, optional Data Query, and optional tools.
7. The user chats with the agent in the built-in UI.

Chat memory is currently stored in browser `sessionStorage`. It is sent to the backend with each chat request and is not persisted in MongoDB.

## Current LLM Support

| Provider | Model |
| --- | --- |
| `groq` | `llama-3.3-70b-versatile` |
| `gemini` | `gemini-2.5-flash` |

Provider/model compatibility is validated when agents are created and updated.

## Environment Variables

Create a `.env` file in the repo root.

Required:

```env
SECRET_VALUE=replace_with_a_long_random_secret
MONGO_URI=mongodb+srv://username:password@cluster.mongodb.net/?appName=YourApp
```

Optional, depending on features:

```env
GROQ_API_KEY=your_groq_key
GOOGLE_API_KEY=your_google_ai_key
TAVILY_API_KEY=your_tavily_key
HF_TOKEN=your_huggingface_token
GOOGLE_CLIENT_ID=your_google_oauth_client_id
GOOGLE_CLIENT_SECRET=your_google_oauth_client_secret
```

Variable meaning:

- `SECRET_VALUE`: JWT signing secret
- `MONGO_URI`: primary MongoDB connection for qAb metadata and default vector storage
- `GROQ_API_KEY`: required for Groq agents
- `GOOGLE_API_KEY`: required for Gemini agents
- `TAVILY_API_KEY`: required for web search
- `HF_TOKEN`: required for embeddings and Knowledge Base search
- `GOOGLE_CLIENT_ID`: required for Gmail OAuth
- `GOOGLE_CLIENT_SECRET`: required for Gmail OAuth

Do not commit real `.env` files or production credentials.

## Installation

From the repo root:

```powershell
cd app/backend
python -m venv .venv
```

Activate the environment.

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

## Run

From `app/backend`:

```bash
uvicorn main:app --reload
```

Open:

- UI: `http://localhost:8000/`
- Health check: `http://localhost:8000/health`

No separate frontend server is required.

## API Route Groups

- `/auth`
- `/agent`
- `/chat`
- `/knowledge-base`
- `/custom-db`
- `/data-query`
- `/tools`
- `/health`

Most endpoints return this response shape:

```json
{
  "success": true,
  "status": 200,
  "data": {},
  "message": "Success"
}
```

## Agent Chat Timeout

Agent chat requests are protected on both sides:

- frontend abort timeout: 120 seconds
- backend execution timeout: 120 seconds
- timeout message: `Request timed out`

The chat send button is disabled while a response is pending to prevent duplicate messages.

## Data Query Safety

Data Queries are designed to expose only selected database sources to agents.

PostgreSQL guardrails:

- only `SELECT` or `WITH` queries are allowed
- dangerous write/schema keywords are blocked
- referenced tables must stay inside the selected Data Query scope

MongoDB guardrails:

- supported operations are `find` and `aggregate`
- `find` result limits are capped
- aggregate pipelines block cross-collection, write, and server-code operators:
  - `$lookup`
  - `$unionWith`
  - `$graphLookup`
  - `$out`
  - `$merge`
  - `$function`
  - `$accumulator`

## MongoDB Notes

If you link MongoDB for Data Query access, include a database name in the URI:

```text
mongodb+srv://username:password@cluster.mongodb.net/YourDatabaseName?appName=YourApp
```

The default app metadata database is:

- `qab`

The default vector collection is:

- `qab.embeddings`

## MongoDB Atlas Vector Search

The expected Atlas Vector Search index name is:

- `vector_index`

Example index:

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

## PostgreSQL / Supabase Notes

Enable pgvector:

```sql
create extension if not exists vector with schema extensions;
```

Example connection strings:

```text
postgresql://postgres:password@host:5432/postgres
postgresql+psycopg2://postgres:password@host:5432/postgres
```

The backend normalizes SQLAlchemy-style driver suffixes when needed.

## Gmail OAuth Notes

For local development, the Google OAuth callback should point to:

```text
http://localhost:8000/tools/google/callback
```

Make sure the OAuth consent screen includes the Gmail scopes required by the app.

## Reports

Detailed project documentation lives in:

- `other/report/architecture.txt`
- `other/report/flow.txt`
- `other/report/endpoints.txt`
- `other/report/models.txt`
- `other/report/frontend.txt`
- `other/report/dq.txt`
- `other/report/bugs.txt`
- `other/report/suggestions.txt`
- `other/report/comments.txt`

The bugs and suggestions reports label each item as frontend, backend, or full stack.

## Security Notes

Before deploying publicly:

- rotate any credentials that were ever committed, shared, or used in screenshots
- restrict CORS origins
- encrypt external DB connection strings
- encrypt Gmail OAuth tokens
- add MongoDB unique indexes
- add startup validation for required environment variables
- add automated tests for auth, agent updates, Data Query safety, and cleanup flows

## Troubleshooting

App starts but login/API calls fail:

- verify `.env` exists at the repo root
- verify `SECRET_VALUE` is set
- verify `MONGO_URI` is valid
- run the server from `app/backend`

Knowledge Base upload works but search fails:

- verify `HF_TOKEN` is set
- verify the vector index exists
- verify vector dimensions are 384
- verify the selected KB database is reachable

Mongo Data Query inspection fails:

- verify the linked Mongo URI includes a database name
- verify the database user can list/read collections

Gmail connect fails:

- verify `GOOGLE_CLIENT_ID`
- verify `GOOGLE_CLIENT_SECRET`
- verify the callback URL is registered in Google Cloud
- verify Gmail scopes are configured on the OAuth consent screen

Frontend changes do not appear:

- hard refresh the browser
- check the cache-busting query strings in `index.html` and `app.js`

## Development Notes

- Backend logs are written to `app/backend/qab_logs.txt` when running from `app/backend`.
- A root-level `qab_logs.txt` may also be created depending on the working directory.
- Knowledge Base file embedding runs in a FastAPI background task.
- The frontend and backend are deployed together from the FastAPI app.
- This repo currently does not include a LICENSE file. Add one before publishing if needed.
