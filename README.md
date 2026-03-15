<div align="center">
  <h1>🛡️ Finsurance</h1>
  <p><strong>Empowering smarter insurance decisions with AI.</strong></p>
</div>

<br />

## 📖 Overview
**Finsurance** is an AI-powered insights platform designed to analyze insurance contracts and medical/care bills. By leveraging intelligent autonomous agents, it audits your current policy usage against alternative contracts to dynamically recommend the best policy fit based on price preferences, coverage quality, and real-world utilization.

---

## ✨ Features
- **📄 Smart Document Analytics**: Extracts and understands complex unstructured insurance contracts (via RAG and vectorstores).
- **🧾 Intelligent Bill Auditing**: Parses insurance bills and extracts key utilization signals automatically.
- **⚖️ Policy Judge System**: Matches your usage against an extensive database of policies to score, rank, and recommend the best alternatives with detailed breakdowns.
- **⚡ Modern Full-Stack**: Blazing fast FastAPI AI backend integrated with an elegant Next.js and Tailwind CSS frontend.

---

## 🛠️ Tech Stack
- **Frontend**: [Next.js](https://nextjs.org/) (React, Tailwind CSS)
- **Backend**: [FastAPI](https://fastapi.tiangolo.com/) (Python)
- **AI / Data**: Agentic architecture, RAG (Retrieval-Augmented Generation), ChromaDB for vector storage.

---

## 🚀 Getting Started

### 1. Clone the Repository
```bash
git clone https://github.com/eddie081202/policy_pulse.git
cd policy_pulse
```

### 2. Backend Setup
Make sure you have Python installed.
```bash
# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows use: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the FastAPI server
.venv/bin/uvicorn backend.main:app --reload --port 8000
```
*The API will be available at `http://localhost:8000/docs`.*

### 3. Frontend Setup
Make sure you have Node.js installed.
```bash
# Navigate to the frontend directory
cd frontend

# Install Node packages
npm install

# Run the development server
npm run dev
```
*The web app will be running at `http://localhost:3000`.*

---

## 📂 Project Structure
```text
finsurance/
├── agent_auditor/       # AI logic for scoring and recommending policies
├── agent_doc_reader/    # AI logic for extracting insurance contracts
├── agent_reading_bills/ # AI logic for reading and extracting bill data
├── backend/             # FastAPI backend routes and core application
├── frontend/            # Next.js React user interface
├── data/                # Vector databases (ChromaDB) and sample documents
└── tests/               # API tests and service contract validations
```

---
