from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
import shutil
from pathlib import Path
import logging

from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_ollama import OllamaLLM

# -----------------------
# Setup
# -----------------------
# Configure logging to file and console
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("backend.log"),  # <- log file
        logging.StreamHandler()              # <- console output
    ]
)

logger = logging.getLogger(__name__)

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

# -----------------------
# Embeddings, LLM, DB placeholder
# -----------------------
embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
llm = OllamaLLM(model="llama3")
db = None  # Will be created per PDF

# -----------------------
# Manual chat memory per PDF
# -----------------------
chat_memory = {}  # {"file.pdf": [{"role":"user","text":"..."}, {"role":"ai","text":"..."}]}

# -----------------------
# Upload PDF
# -----------------------
@app.post("/upload_pdf")
async def upload_pdf(file: UploadFile = File(...)):
    try:
        file_path = UPLOAD_DIR / file.filename
        with open(file_path, "wb") as f:
            shutil.copyfileobj(file.file, f)
        logger.info(f"Uploaded PDF: {file.filename}")
        return {"filename": file.filename}
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        return {"error": str(e)}

# -----------------------
# Ask question
# -----------------------
@app.post("/ask")
async def ask_question(question: str = Form(...), pdf_filename: str = Form(...)):
    from langchain_community.document_loaders import PyPDFLoader
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    try:
        file_path = UPLOAD_DIR / pdf_filename
        if not file_path.exists():
            logger.warning(f"PDF not found: {pdf_filename}")
            return {"error": f"PDF '{pdf_filename}' not found. Please upload first."}

        # Load PDF
        loader = PyPDFLoader(file_path)
        docs = loader.load()

        # Chunk
        splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=150)
        chunks = splitter.split_documents(docs)

        # Create vector DB
        global db
        db = Chroma.from_documents(chunks, embedding=embeddings)

        # Retrieve top 3 chunks
        docs = db.similarity_search(question, k=3)
        context_text = "\n\n".join([d.page_content for d in docs])

        # Build prompt with manual chat memory
        history = chat_memory.get(pdf_filename, [])
        chat_history_text = "\n".join([f"{m['role']}: {m['text']}" for m in history])

        prompt = f"""
You are a helpful assistant. Keep in mind the chat history:
{chat_history_text}

Use the following context to answer the question:
{context_text}

Question: {question}
Answer in a clear and concise paragraph.
"""

        # Generate answer
        answer = llm.generate([prompt]).generations[0][0].text
        logger.info(f"Question answered for PDF: {pdf_filename}")

        # Update memory
        if pdf_filename not in chat_memory:
            chat_memory[pdf_filename] = []
        chat_memory[pdf_filename].append({"role": "user", "text": question})
        chat_memory[pdf_filename].append({"role": "ai", "text": answer})

        # Return answer + sources
        sources = [f"{d.metadata.get('source')} (page {d.metadata.get('page')})" for d in docs]
        return {"answer": answer, "sources": sources}

    except Exception as e:
        logger.error(f"Error in /ask: {e}")
        return {"error": str(e)}