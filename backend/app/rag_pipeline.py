from typing import List, Tuple
import os
import requests
import numpy as np

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain.embeddings.base import Embeddings
from pypdf import PdfReader

from huggingface_hub import InferenceClient


class HuggingFaceAPIEmbeddings(Embeddings):
    """Custom embeddings using HuggingFace InferenceClient."""
    
    def __init__(self, api_key: str, model_name: str):
        from huggingface_hub import InferenceClient
        self.client = InferenceClient(token=api_key)
        self.model_name = model_name
    
    def _call_api(self, text: str) -> List[float]:
        """Call the HuggingFace API and return embeddings."""
        try:
            result = self.client.feature_extraction(text[:512], model=self.model_name, provider="hf-inference")
            # Convert numpy array or similar to list
            if hasattr(result, 'tolist'):
                embedding = result.tolist()
            elif isinstance(result, list):
                embedding = result
            else:
                embedding = list(result)
            return embedding
        except Exception as e:
            raise Exception(f"HuggingFace API error: {str(e)}")
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed a list of documents."""
        embeddings = []
        total = len(texts)
        for i, text in enumerate(texts):
            if i % 10 == 0:
                print(f"Embedding progress: {i}/{total}")
            embedding = self._call_api(text)
            embeddings.append(embedding)
        print(f"Embedding complete: {total}/{total}")
        return embeddings
    
    def embed_query(self, text: str) -> List[float]:
        """Embed a single query."""
        return self._call_api(text)


class RAGPipeline:
    """
    Simple RAG pipeline that:
    - loads PDFs and extracts text + page numbers
    - splits into chunks
    - embeds chunks with sentence-transformers
    - stores in a FAISS index per user
    - retrieves relevant chunks for a query
    - calls an LLM on HuggingFace with the retrieved context
    """

    def __init__(self):
        embedding_model_name = os.getenv(
            "EMBEDDING_MODEL_NAME", "sentence-transformers/all-MiniLM-L6-v2"
        )
        self.documents_path = os.getenv("DOCUMENTS_PATH", "./documents")
        self.vector_store_path = os.getenv("VECTOR_STORE_PATH", "./vector_store")
        os.makedirs(self.documents_path, exist_ok=True)
        os.makedirs(self.vector_store_path, exist_ok=True)

        # Embeddings: Use HuggingFace Inference API (no local Torch/DLLs needed)
        hf_token = os.getenv("HUGGINGFACE_API_KEY")
        if not hf_token:
            raise RuntimeError(
                "HUGGINGFACE_API_KEY is required. Please set it in your .env file."
            )
        print("Using HuggingFace Inference API embeddings")
        self.embeddings = HuggingFaceAPIEmbeddings(
            api_key=hf_token,
            model_name=embedding_model_name,
        )
        
        # Test the embeddings
        try:
            test_embedding = self.embeddings.embed_query("test")
            print(f"Embeddings working! Dimension: {len(test_embedding)}")
        except Exception as e:
            print(f"Warning: Embeddings test failed: {e}")

        # Groq client for LLM
        self.groq_api_key = os.getenv("GROQ_API_KEY")
        if not self.groq_api_key:
            raise RuntimeError("GROQ_API_KEY is required. Please set it in your .env file.")

        # text splitter config for chunking documents
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=800,
            chunk_overlap=150,
            length_function=len,
        )

    # ---------- PDF INGESTION ----------
    def _load_pdf(self, file_path: str) -> List[Tuple[str, int]]:
        """
        Load a PDF and return a list of (page_text, page_number).
        """
        reader = PdfReader(file_path)
        pages = []
        for i, page in enumerate(reader.pages):
            text = page.extract_text() or ""
            pages.append((text, i + 1))
        return pages

    def _chunk_with_metadata(self, pages: List[Tuple[str, int]], doc_id: str) -> List[dict]:
        """
        Split pages into smaller chunks and attach metadata.
        """
        chunks_meta: List[dict] = []
        for text, page_number in pages:
            if not text.strip():
                continue
            for chunk in self.text_splitter.split_text(text):
                chunks_meta.append(
                    {
                        "text": chunk,
                        "metadata": {
                            "page": page_number,
                            "doc_id": doc_id,
                        },
                    }
                )
        return chunks_meta

    def _get_user_index_path(self, user_id: int) -> str:
        return os.path.join(self.vector_store_path, f"user_{user_id}_faiss")

    def _load_vector_store(self, user_id: int) -> FAISS | None:
        """
        Load the FAISS index for a user if it exists.
        """
        index_path = self._get_user_index_path(user_id)
        if not os.path.isdir(index_path):
            return None
        return FAISS.load_local(index_path, self.embeddings, allow_dangerous_deserialization=True)

    def _save_vector_store(self, user_id: int, vs: FAISS) -> None:
        index_path = self._get_user_index_path(user_id)
        vs.save_local(index_path)

    def ingest_document(self, user_id: int, doc_path: str, doc_id: str) -> None:
        """
        Ingest a single PDF into the user's FAISS index.
        """
        print(f"Loading PDF: {doc_path}")
        pages = self._load_pdf(doc_path)
        print(f"Loaded {len(pages)} pages")
        
        chunks_meta = self._chunk_with_metadata(pages, doc_id=doc_id)
        print(f"Created {len(chunks_meta)} chunks")

        texts = [c["text"] for c in chunks_meta]
        metadatas = [c["metadata"] for c in chunks_meta]

        print("Starting embedding process...")
        existing_vs = self._load_vector_store(user_id)
        if existing_vs:
            existing_vs.add_texts(texts=texts, metadatas=metadatas)
            self._save_vector_store(user_id, existing_vs)
        else:
            vs = FAISS.from_texts(texts=texts, embedding=self.embeddings, metadatas=metadatas)
            self._save_vector_store(user_id, vs)
        print("Document ingestion complete!")

    # ---------- QUERY / RETRIEVAL ----------
    def retrieve(self, user_id: int, query: str, k: int = 5) -> List[dict]:
        """
        Retrieve top-k relevant chunks for the given query.
        """
        vs = self._load_vector_store(user_id)
        if not vs:
            return []
        docs = vs.similarity_search(query, k=k)
        results = []
        for d in docs:
            meta = d.metadata or {}
            results.append(
                {
                    "text": d.page_content,
                    "page": meta.get("page"),
                    "doc_id": meta.get("doc_id"),
                }
            )
        return results

    # ---------- LLM CALL WITH RAG ----------
    def generate_answer(self, query: str, context_chunks: List[dict], chat_history: List[dict] | None = None) -> str:
        """
        Call the HF model with instructions + retrieved context + simple chat history.
        """
        context_texts = []
        for c in context_chunks:
            prefix = f"(Page {c.get('page')}) " if c.get("page") else ""
            context_texts.append(f"{prefix}{c['text']}")
        context = "\n\n".join(context_texts)

        history_str = ""
        if chat_history:
            formatted_turns = []
            for turn in chat_history[-5:]:
                role = turn.get("role", "user")
                content = turn.get("content", "")
                formatted_turns.append(f"{role}: {content}")
            history_str = "\n".join(formatted_turns)

        system_prompt = (
            "You are an AI assistant answering questions about uploaded enterprise documents. "
            "Use ONLY the provided context to answer. If the answer is not in the context, say you don't know."
        )

        prompt = f"""{system_prompt}

Context:
{context}

Chat history:
{history_str}

User question: {query}

Answer clearly and concisely. Also mention which pages you used where relevant."""

        try:
            import requests
            # Truncate context to avoid token limit
            context = context[:3000]
            headers = {"Authorization": f"Bearer {self.groq_api_key}", "Content-Type": "application/json"}
            payload = {
                "model": "llama-3.1-8b-instant",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {query}"}
                ],
                "max_tokens": 512,
                "temperature": 0.2,
            }
            resp = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=30)
            if not resp.ok:
                return f"Error generating response: {resp.status_code} - {resp.text}"
            return resp.json()["choices"][0]["message"]["content"]
        except Exception as e:
            return f"Error generating response: {str(e)}"

