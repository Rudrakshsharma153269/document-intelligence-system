## Document Intelligence System

A full-stack RAG-powered Enterprise Document Intelligence System.

- **Backend**: FastAPI, LangChain, FAISS, HuggingFace Inference API (embeddings), Groq LLM, JWT auth
- **Frontend**: React, Vite, TailwindCSS, Axios

### Backend Setup

1. Navigate to the backend folder:
   - `cd backend`
2. Create and activate a virtual environment (recommended).
3. Install dependencies:
   - `pip install -r requirements.txt`
4. Configure `.env`:
   ```
   HUGGINGFACE_API_KEY=<your_huggingface_token>
   GROQ_API_KEY=<your_groq_api_key>
   EMBEDDING_MODEL_NAME=sentence-transformers/all-MiniLM-L6-v2
   SECRET_KEY=<random_secret_string>
   DOCUMENTS_PATH=./documents
   VECTOR_STORE_PATH=./vector_store
   BACKEND_CORS_ORIGINS=http://localhost:3000,http://localhost:5173
   ```
   - HuggingFace token: https://huggingface.co/settings/tokens
   - Groq API key (free): https://console.groq.com
5. Run the API:
   - `python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`

### Frontend Setup

1. Navigate to the frontend folder:
   - `cd frontend`
2. Install dependencies:
   - `npm install`
3. Run the dev server:
   - `npm run dev`
4. Open `http://localhost:5173`

### Basic Flow

- Register or log in to obtain a JWT.
- Upload PDFs — the backend extracts text, chunks it, embeds via HuggingFace API, and stores in a per-user FAISS index.
- Ask questions in the chat UI — the backend retrieves relevant chunks and calls Groq (`llama-3.1-8b-instant`) to generate answers with page references.
- The upload panel shows the total number of documents uploaded.
