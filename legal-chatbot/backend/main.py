import logging
import os
import time

import chromadb
import requests
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from rag import CHAT_MODEL, OLLAMA_CHAT_URL, ask_chatbot

API_KEY = os.getenv("LMO7AMI_API_KEY", "").strip()
OLLAMA_TAGS_URL = os.getenv("OLLAMA_TAGS_URL", "http://localhost:11434/api/tags")
CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv("LMO7AMI_CORS_ORIGINS", "*").split(",")
    if origin.strip()
]

logging.basicConfig(
    level=os.getenv("LMO7AMI_LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger("lmo7ami-api")

app = FastAPI(title="Moroccan Labor Law AI", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    question: str


def json_error(status_code: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error": code, "message": message},
    )


@app.middleware("http")
async def request_middleware(request: Request, call_next):
    started = time.perf_counter()

    if API_KEY and request.method != "OPTIONS" and request.url.path not in {"/", "/health"}:
        provided_key = request.headers.get("X-API-Key", "")
        if provided_key != API_KEY:
            return json_error(
                401,
                "UNAUTHORIZED",
                "API key is missing or invalid.",
            )

    try:
        response = await call_next(request)
    except Exception:
        logger.exception("Unhandled API error on %s %s", request.method, request.url.path)
        return json_error(
            500,
            "INTERNAL_ERROR",
            "وقع مشكل فالسيرفر. عاود جرّب من بعد.",
        )

    latency_ms = round((time.perf_counter() - started) * 1000, 2)
    response.headers["X-Process-Time-Ms"] = str(latency_ms)
    logger.info(
        "%s %s -> %s %.2fms",
        request.method,
        request.url.path,
        response.status_code,
        latency_ms,
    )
    return response


@app.get("/")
def root():
    return {
        "status": "running",
        "ai": "Moroccan Labor Law Chatbot",
        "model": CHAT_MODEL,
    }


@app.get("/health")
def health():
    return {
        "status": "ok",
        "api": "running",
        "model": CHAT_MODEL,
        "ollama_chat_url": OLLAMA_CHAT_URL,
    }


@app.get("/models")
def models():
    try:
        response = requests.get(OLLAMA_TAGS_URL, timeout=8)
        response.raise_for_status()
    except requests.exceptions.ConnectionError:
        return json_error(
            503,
            "OLLAMA_OFFLINE",
            "Ollama ما خدامش. شغل ollama serve وعاود جرّب.",
        )
    except requests.exceptions.Timeout:
        return json_error(
            504,
            "OLLAMA_TIMEOUT",
            "Ollama طول بزاف فالفحص. عاود جرّب.",
        )
    except requests.exceptions.HTTPError:
        return json_error(
            502,
            "OLLAMA_ERROR",
            "Ollama رجّع خطأ أثناء فحص الموديلات.",
        )

    raw_models = response.json().get("models", [])
    model_names = [model.get("name") for model in raw_models if model.get("name")]
    return {
        "active_model": CHAT_MODEL,
        "installed_models": model_names,
        "active_model_installed": CHAT_MODEL in model_names,
    }


@app.post("/chat")
def chat(request: ChatRequest):
    try:
        answer, sources = ask_chatbot(request.question, return_sources=True)
    except chromadb.errors.NotFoundError:
        return json_error(
            503,
            "KNOWLEDGE_BASE_MISSING",
            "قاعدة المعرفة ما لقاهاش السيرفر. خاص تشغيل ingest.py.",
        )
    except requests.exceptions.ConnectionError:
        return json_error(
            503,
            "OLLAMA_OFFLINE",
            "Ollama ما خدامش. شغل ollama serve وعاود جرّب.",
        )
    except requests.exceptions.Timeout:
        return json_error(
            504,
            "OLLAMA_TIMEOUT",
            "الموديل طول بزاف فالإجابة. عاود جرّب بعد شوية.",
        )
    except RuntimeError as exc:
        message = str(exc).lower()
        if "not found" in message or "model" in message:
            return json_error(
                503,
                "MODEL_NOT_FOUND",
                f"Ollama model is not installed. Please run: ollama pull {CHAT_MODEL}",
            )
        logger.exception("Chat runtime error")
        return json_error(
            502,
            "CHAT_MODEL_ERROR",
            "وقع مشكل فالموديل المحلي. عاود جرّب من بعد.",
        )

    return {
        "answer": answer,
        "sources": [
            {
                "number": source.number,
                "page": source.page,
                "category": source.category,
                "source": source.source,
                "source_type": source.source_type,
            }
            for source in sources
        ],
    }
