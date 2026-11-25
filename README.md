# VoiceLead AI — Autonomous AI Sales Voice Assistant

**VoiceLead AI** is a full-stack autonomous AI sales voice agent built for real-time customer consultations, lead qualification, RAG-powered course Q&A, and 1-on-1 counseling appointment booking.

---

## Core Capabilities

- **Live Voice Consultation (STT + TTS)**: Real-time browser speech recognition (`SpeechRecognition`) and synchronized voice playback (`SpeechSynthesis`) with multilingual support.
- **Customer Details Onboarding**: Dedicated right-side Customer Details Dashboard requiring Full Name and Gmail Address before initiating a personalized AI voice session.
- **Contextual AI Responses (Groq / Gemini + RAG)**: Combines **FAISS** vector search (`all-MiniLM-L6-v2`) with **Groq (`llama-3.3-70b-versatile`)** / **Gemini** to answer course, fee, syllabus, and placement questions using conversation history.
- **Lead Qualification & CRM**: Automatic 0–100 lead scoring (**Hot**, **Warm**, **Cold**), sentiment analysis, and contact extraction.
- **Appointment Scheduling**: Conflict-free 1-on-1 counseling slot booking with persistent storage (`MongoDB` or automatic `local_db.json` fallback).
- **Executive Overview Dashboard**: Live KPIs, 7-day activity charts, course interest breakdown, and recent qualified leads.

---

## Tech Stack

| Layer | Technology |
| :--- | :--- |
| **Frontend** | React, Vite, Tailwind CSS, Lucide Icons |
| **Backend** | Python, FastAPI, Uvicorn |
| **AI & RAG** | Groq (`llama-3.3-70b-versatile`), Google Gemini, FAISS, Sentence Transformers (`all-MiniLM-L6-v2`) |
| **Database** | MongoDB (with persistent local JSON fallback) |
| **Voice** | Web Speech API (`SpeechRecognition` & `SpeechSynthesis`) |

---

## Quick Start

### 1. Backend
```bash
cd backend
pip install -r requirements.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### 2. Frontend
```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173/** in your browser.
