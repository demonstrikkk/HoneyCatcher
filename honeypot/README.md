# Agentic Honey-Pot System

A production-grade, distributed system designed to detect scams, engage malicious actors via autonomous AI agents, and extract actionable intelligence.

## 🚀 Features

- **Automated Scam Detection**: Hybrid rule-based & LLM analysis (Groq) to identify malicious intent.
- **Agentic Engagement**: LangGraph-driven autonomous agents that waste scammers' time while mimicking human behavior.
- **Intelligence Extraction**: Real-time extraction of bank accounts, UPI IDs, and phishing links.
- **Stealth Mode**: Designed to never reveal its automated nature to the scammer.
- **Official Integration**: Automatic reporting to the GUVI central tracking endpoint.

## 🛠️ Tech Stack

- **Frontend**: React, Vite, TailwindCSS, Shadcn/UI, Framer Motion
- **Backend**: Python, FastAPI, Async MongoDB (Motor)
- **AI/ML**: LangChain, LangGraph, Groq API (Primary), Gemini API (Fallback)
- **Database**: MongoDB

## 🔧 Setup & Installation

### Prerequisites
- Python 3.10+
- Node.js 18+
- MongoDB
- API Keys: Groq, Google Gemini

### Backend Setup

1. Navigate to the backend directory:
   ```bash
   cd honeypot/backend
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Create a `.env` file with the following:
   ```env
   # API Keys
   GROQ_API_KEY=your_groq_key
   GEMINI_API_KEY=your_gemini_key
   
   # Database
   MONGO_URI=mongodb://localhost:27017
   DB_NAME=honeypot_db

   # Security
   API_SECRET_KEY=your_secret_key_for_clients
   ```
4. Run the server:
   ```bash
   uvicorn main:app --reload
   ```

### Frontend Setup

1. Navigate to the frontend directory:
   ```bash
   cd honeypot/frontend
   ```
2. Install dependencies:
   ```bash
   npm install
   ```
3. Run the development server:
   ```bash
   npm run dev
   ```

## 🔄 Lifecycle

1. **Ingestion**: Message arrives via `/api/message`.
2. **Detection**: System scores the message for scam intent.
3. **Activation**: If confirmed scam, the Agent wakes up.
4. **Engagement**: Agent replies, maintaining a persona.
5. **Extraction**: Background workers parse messages for intel.
6. **Termination**: Loop ends based on rules/timeouts; Report sent to GUVI.

## ⚠️ Disclaimer

This system is designed for authorized cybersecurity research and defense. Do not use for harassment.
