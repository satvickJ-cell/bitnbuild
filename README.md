# CivicPulse AI 🏛️⚡

> Autonomous Municipal Budget Auditor & Statutory Legal Action Engine

CivicPulse AI ingests complex, unstructured municipal budget circulars (PDFs), applies deterministic engineering and budget baselines to detect critical local under-allocations, and autonomously drafts legally binding Right to Information (RTI) applications under Section 6(1) of the RTI Act 2005.

---

## 🛠️ Architecture & Pipeline
1. **Multimodal Extraction (`extractor.py`):** Ingests raw municipal PDF circulars via the Gemini API (`gemini-2.0-flash`) and extracts structured ward data (allocations, YoY figures, drain lengths).
2. **Deterministic Evaluator (`evaluator.py`):** Runs arithmetic verification against statutory benchmarks (Karnataka Municipal Corporations Act SWD norms) with zero LLM hallucination.
3. **Action Agent (`action_agent.py`):** Autonomously drafts an official Form A RTI application citing specific municipal budget codes (Head P-3112).
4. **Interactive Dashboard (`frontend/index.html`):** Dark-mode civic intelligence interface displaying real-time metrics, audit verdicts, and PDF export.

---

## 🚀 Quickstart Guide

### Prerequisites
- Python 3.10+
- Google Gemini API Key

### 1. Clone & Setup Environment
```bash
git clone https://github.com/<your-username>/civicpulse-ai.git
cd civicpulse-ai
python -m venv .venv
# On Windows:
.\.venv\Scripts\activate
# On Linux/macOS:
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure Environment Variables
Create a `.env` file in the root directory:
```env
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-2.0-flash
```

### 3. Run the Backend API
```bash
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```
Interactive API docs are available at `http://127.0.0.1:8000/docs`.

### 4. Launch the Frontend
Open `frontend/index.html` in any modern web browser or serve it using any local static file server.
