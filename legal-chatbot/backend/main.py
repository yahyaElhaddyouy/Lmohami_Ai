from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

from rag import ask_chatbot

app = FastAPI(
    title="Moroccan Labor Law AI",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    question: str


# class ChatResponse(BaseModel):
#     answer: str


@app.get("/")
def root():
    return {
        "status": "running",
        "ai": "Moroccan Labor Law Chatbot",
        "model": "qwen2.5:3b"
    }


@app.post("/chat")
def chat(request: ChatRequest):
    answer, sources = ask_chatbot(request.question, return_sources=True)

    return {
        "answer": answer,
        "sources": [
            {
                "number": source.number,
                "page": source.page
            }
            for source in sources
        ]
    }