# Deployment

## Temporary: Ngrok

```powershell
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
ngrok http 8000
```

Use the HTTPS ngrok URL in Flutter without a trailing slash.

## Environment Variables

- `OLLAMA_CHAT_MODEL=qwen2.5:7b`
- `OLLAMA_EMBED_MODEL=nomic-embed-text`
- `OLLAMA_CHAT_URL=http://localhost:11434/api/chat`
- `OLLAMA_EMBED_URL=http://localhost:11434/api/embeddings`
- `OLLAMA_TAGS_URL=http://localhost:11434/api/tags`
- `RAG_DEBUG=false`
- `LMO7AMI_API_KEY=optional-secret`
- `LMO7AMI_CORS_ORIGINS=*`

## VPS Roadmap

1. Ubuntu VPS.
2. Install Docker and Docker Compose.
3. Run FastAPI in a container.
4. Run Ollama with persistent model storage.
5. Mount ChromaDB as a persistent volume.
6. Put Nginx in front of FastAPI.
7. Enable HTTPS with Cloudflare or Let's Encrypt.
8. Configure API key and rate limiting.
9. Ship logs to files or a small log service.

## Model Installation

```bash
ollama pull nomic-embed-text
ollama pull qwen2.5:7b
```

## Troubleshooting

- `/health` works but `/chat` fails: check Ollama and ChromaDB.
- `/models` says model missing: run `ollama pull <model>`.
- Flutter timeout: check ngrok URL and phone internet.
- Empty retrieval: run `python ingest.py` and re-test.
