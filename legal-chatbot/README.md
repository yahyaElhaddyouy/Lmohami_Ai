# Lmo7ami AI

Lmo7ami AI is a Moroccan labor-law assistant that answers questions about the Moroccan Code du Travail in Moroccan Darija.

## Stack

- FastAPI backend
- ChromaDB vector database
- Ollama local models
- RAG over `backend/data/code_travail_maroc.pdf`
- Flutter mobile app
- Ngrok for temporary public access

## Local Backend

```powershell
cd backend
venv\Scripts\activate
ollama serve
python ingest.py
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Useful endpoints:

- `GET /health`
- `GET /models`
- `POST /chat`

## Mobile App

```powershell
cd mobile
flutter clean
flutter pub get
flutter run
```

Set the API URL in `mobile/lib/config/api_config.dart`. The base URL must not end with `/`; the app appends `/chat`.

## Trust

```powershell
cd backend
python evaluate_trust.py --report trust_report.json
python stress_questions.py --minutes 10
```

The assistant must remain source-based, avoid legal guarantees, and refuse when the available source is weak.
