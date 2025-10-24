# AI Startup Analyst Backend

FastAPI backend that orchestrates the AI startup analyst workflow described in the
specification. The implementation keeps the architecture modular so that Google
Cloud services (Firestore, Storage, Document AI, Gemini) can be wired in where
available.

## Features

- Upload PDFs/audio/video pitch materials and create a new deal entry.
- Generate memo drafts using configurable weightings with regeneration support.
- Persist deal state in Firestore or in-memory storage when Firestore is not
  available.
- Store memo DOCX artefacts and original uploads in Google Cloud Storage.
- Download generated documents and original pitch decks.
- Manage founder outreach invites and persist founder chat transcripts.

## Project structure

```
app/
├── api/               # FastAPI routes
├── dependencies.py    # Dependency wiring (Firestore/Storage/etc.)
├── main.py            # FastAPI application factory
├── models/            # Pydantic representations of deal documents
└── services/          # Domain services (storage, memo generation, etc.)
```

## Getting started

1. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

   > Optional: install the additional Google Cloud libraries (`google-cloud-firestore`,
   > `google-cloud-documentai`, `google-cloud-aiplatform`) when you are ready to
   > connect to production infrastructure.

2. **Configure environment**

   Copy the provided `.env` file and adjust the values to match your deployment
   environment (project IDs, bucket names, invite URLs, etc.). The application
   automatically loads the `.env` file on startup.

   ```dotenv
   APP_ENV=development
   API_TITLE="AI Startup Analyst"
   DEBUG=False
   GCP_PROJECT_ID=hackathon-472304
   GCP_LOCATION=us-central1
   GCS_BUCKET_NAME=investment_memo_ai
   GOOGLE_API_KEY=AIzaSyCG_RaIGoBFlAMH89c_97LUpvVGOlbiO-w
   GOOGLE_SEARCH_ENGINE_ID=27a87949557e54a04
   ```

   Replace any project-specific secrets (service account paths, Document AI
   processor IDs, invite base URLs, etc.) before running the backend.

3. **Run the server**

   ```bash
   uvicorn app.main:app --reload
   ```

   The service exposes the documented endpoints such as `POST /upload`,
   `POST /generate_memo/{deal_id}`, and `GET /deals`.

4. **Configure Google Cloud (optional)**

   - Ensure `GOOGLE_APPLICATION_CREDENTIALS` is set, the respective APIs are
     enabled, and the configured storage bucket exists.
   - Replace the heuristic memo generation logic inside
     `app/services/memo_generator.py` with calls to Gemini 2.5 via Vertex AI.

## Testing the workflow

1. Upload a sample PDF (or any file) via `POST /upload` to create a new deal.
2. Regenerate the memo with different weightings using
   `POST /generate_memo/{deal_id}`.
3. Fetch the memo using `GET /deals/{deal_id}` or download the artefacts using
   the dedicated download endpoints.
4. Issue a founder invite via `POST /deals/{deal_id}/founder_invite` and append
   chat transcripts with `POST /deals/{deal_id}/founder_chat`.

The service responses follow the Firestore document schema shared in the
original requirements to ease downstream integration.

