# VoxSales AI – Autonomous AI Sales Voice Agent

[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat-square&logo=FastAPI&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React_19-Vite-61DAFB?style=flat-square&logo=react&logoColor=black)](https://react.dev)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-38B2AC?style=flat-square&logo=tailwind-css&logoColor=white)](https://tailwindcss.com)
[![FAISS](https://img.shields.io/badge/FAISS-Meta_Vector_Search-0081FB?style=flat-square)](https://github.com/facebookresearch/faiss)
[![Sentence Transformers](https://img.shields.io/badge/Sentence_Transformers-all--MiniLM--L6--v2-orange?style=flat-square)](https://www.sbert.net)
[![MongoDB](https://img.shields.io/badge/MongoDB-8.x-green?style=flat-square&logo=mongodb&logoColor=white)](https://www.mongodb.com)

**VoxSales AI** is an autonomous AI-powered sales voice assistant designed for an online education platform (Fortivex Education). The assistant converses with prospective students, answers course queries accurately using **RAG (FAISS + Sentence Transformers)**, qualifies leads through a transparent rule-based scoring engine, extracts contact details with consent, and books 1-on-1 counseling appointments into **MongoDB** with strict concurrency and duplicate-prevention controls.

---

## Technical Evaluation Highlights (College Placement MVP)

- **End-to-End Functional Architecture**: Voice STT (Web Speech API) -> FastAPI -> RAG FAISS Vector Search -> Gemini Context Generation -> Dynamic Lead Scoring -> Real-time MongoDB Persistence -> Browser TTS Audio Voice Response.
- **Zero Mock / Hardcoded Data**: Dashboard KPIs, activity charts, lead tables, and appointment calendars are queried in real time from live MongoDB collections.
- **Transparent Rule-Based Lead Scoring**: Clear 0–100 rubric categorizing leads into **Hot (≥ 70)**, **Warm (40–69)**, and **Cold (< 40)** based on contact details, course specificity, buying signals, and scheduled counseling.
- **Duplicate Booking Prevention**: Atomic MongoDB queries guarantee that two prospects cannot book the same counseling slot simultaneously (returns HTTP 409 Conflict).
- **Graceful High-Reliability Fallback**: If a Gemini API key is not configured or network quota is exhausted during evaluation, an intelligent local counselor engine takes over seamlessly—guaranteeing 100% uptime and demonstration readiness.

---

## Technology Stack

| Layer | Technology | Purpose |
| :--- | :--- | :--- |
| **Frontend** | React 19 + Vite + Tailwind CSS | SaaS dashboard, interactive audio wave, transcripts |
| **Icons & Styling** | Lucide React | Modern SaaS typography and responsive components |
| **Backend** | Python 3.14 + FastAPI + Uvicorn | High-performance asynchronous REST API |
| **Vector RAG** | Sentence Transformers (`all-MiniLM-L6-v2`) + FAISS | Dense vector cosine similarity search over course syllabus |
| **Database** | MongoDB 8.x (`voxsales_db`) | Collections: `leads`, `conversations`, `appointments`, `slots` |
| **Speech-to-Text (STT)** | Browser Web Speech API (`SpeechRecognition`) | Zero-latency client-side microphone transcription |
| **Text-to-Speech (TTS)** | Browser SpeechSynthesis API | Natural voice audio generation with mute/interrupt control |
| **AI LLM** | Google Gemini API (`gemini-2.5-flash`) | Contextual conversational generation & sales consultation |

---

## System Architecture

```mermaid
flowchart TD
    User([Prospective Student]) -->|Voice / Text| UI[React + Vite Frontend]
    
    subgraph Client_Browser [Client Browser]
        UI -->|Mic Stream| STT[Web Speech API STT]
        STT -->|Transcribed Text| UI
        TTS[SpeechSynthesis API] -->|Voice Output| User
    end

    UI -->|HTTP POST /api/agent/interact| API[FastAPI Backend Server]
    
    subgraph Backend_Engine [FastAPI Backend Service]
        API --> RAG[RAG Pipeline]
        RAG -->|Vector Embeddings| ST[SentenceTransformers all-MiniLM-L6-v2]
        ST -->|Dense Vector Query| FAISS[(FAISS IndexFlatIP)]
        FAISS -->|Top-3 Course Chunks| RAG
        
        RAG --> AI_Engine[Gemini AI / Intelligent Counselor]
        AI_Engine --> Scorer[Rule-Based Lead Scorer]
        Scorer --> DB_Layer[(MongoDB Database)]
    end

    DB_Layer -->|Persist Lead & Transcript| LeadsCol[Collections: leads, conversations]
    DB_Layer -->|Atomic Slot Claim| ApptsCol[Collections: slots, appointments]
    
    API -->|Assistant Reply + RAG Sources + Lead Metrics| UI
    UI -->|Speak Text| TTS
```

---

## 5 Application Pages Overview

1. **Dashboard (`/`)**:
   - Executive overview of Total Leads, Hot Leads, Conversations, and Appointments.
   - Conversation & Lead activity timeline chart (last 7 days from MongoDB).
   - Academic course interest breakdown bars.
   - Recent qualified leads table with sentiment and direct booking shortcuts.
2. **Voice Agent (`/agent`)**:
   - Interactive microphone button with pulsing audio visualizer.
   - Live Speech-to-Text transcription and SpeechSynthesis audio reply.
   - Real-time **Prospect Qualification Panel** (name, phone, email, course, rule score, category).
   - **Retrieved RAG Sources Drawer**: displays matched course chunks and cosine similarity scores.
   - Fallback text chat input with quick-ask suggestion pills.
3. **Lead Management (`/leads`)**:
   - Comprehensive candidate table with search, category filtering (Hot/Warm/Cold), and course filtering.
   - Detailed candidate modal to edit notes, adjust qualification category, and review timelines.
   - Manual candidate lead creation form.
4. **Appointments (`/appointments`)**:
   - Available counseling slots calendar grouped by date across 6 daily windows.
   - Booked vs Open slot visual indicators.
   - Immediate confirmation with duplicate-booking rejection.
   - Confirmed bookings table with candidate details and timestamps.
5. **Knowledge Base (`/knowledge`)**:
   - Interactive **FAISS Cosine Similarity Simulator**: type any query to see vector search latency (ms), retrieved chunks, and scores.
   - Complete curricula, pricing, EMI options, and placement policies for:
     - Python Programming & Automation
     - Java Enterprise & Microservices
     - Full Stack Web Development (MERN + Next.js 14)
     - AI, Machine Learning & LLM Specialist
     - DSA & System Design Masterclass

---

## Quick Setup & Execution

### Prerequisites
- Node.js (v18+) & npm
- Python (v3.10+)
- MongoDB Community Server running on `127.0.0.1:27017`

### 1. Start MongoDB
Ensure MongoDB is running locally:
```powershell
mongod --dbpath "backend\data\db" --bind_ip 127.0.0.1 --port 27017
```

### 2. Backend Setup
```powershell
cd backend
pip install -r requirements.txt
# (Optional) Add your Gemini API key to backend\.env
# GEMINI_API_KEY=your_key_here
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
Backend API will be live at `http://127.0.0.1:8000` with Swagger Docs at `http://127.0.0.1:8000/docs`.

### 3. Frontend Setup
```powershell
cd frontend
npm install
npm run dev
```
Frontend application will be live at `http://localhost:5173`.

### 4. Run Automated End-to-End Verification Test
We have included a comprehensive test script that verifies all 11 evaluation requirements:
```powershell
$env:PYTHONPATH="backend"
python backend\test_e2e.py
```
Expected output: `>>> ALL 11 END-TO-END TEST CASES PASSED WITH 100% SUCCESS! <<<`

---

## One-Click Launchers (Windows)
- Double-click `run_demo.bat` to launch MongoDB, FastAPI backend, and React frontend simultaneously.
- Or use `start_backend.bat` and `start_frontend.bat` individually.
