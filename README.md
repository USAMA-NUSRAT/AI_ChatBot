# Simple Chatbot

- `backend/`: FastAPI. Uses Anthropic (Claude) first and falls back to Gemini if Claude fails.
- `frontend/`: React + Vite chat UI.

## 1. Backend

```powershell
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
# put your keys in backend\.env (ANTHROPIC_API_KEY, GEMINI_API_KEY)
uvicorn app.main:app --reload --port 8000
```

API docs: http://localhost:8000/docs

## 2. Frontend

```powershell
cd frontend
npm install
npm run dev
```

Open http://localhost:5173
