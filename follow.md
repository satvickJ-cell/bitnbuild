Objective:
Build the backend architecture for a Civic Transparency Agentic AI. The agent will read a municipal budget PDF, extract specific ward drainage allocation data, deterministically evaluate that data against hardcoded civic rules, and autonomously draft a legal Right to Information (RTI) application if a violation is detected.

Role & Scope:
You are acting as the backend orchestration agent.

IN SCOPE: Writing Python scripts to handle PDF ingestion via the Gemini Files API, extracting structured JSON, executing deterministic logic comparisons (basic arithmetic if/else statements), generating the final text output via the Gemini API, and exposing this pipeline via a lightweight local FastAPI backend.

OUT OF SCOPE: Do NOT build the frontend HTML/CSS/React files (the UI will be generated externally via Google Stitch). Do NOT set up a vector database, RAG pipeline, or external cloud database (we are using plain JSON files for storage). Do NOT use complex multi-agent frameworks like CrewAI; use native API calls.

Tech Stack:

Language/Framework: Python (FastAPI).

AI Engine: google-genai SDK using Gemini 1.5 Pro.

Dependencies: fastapi, uvicorn, pydantic, python-multipart.

Data & Variables:
You will need to write the code to create and manage the following local files:

rules.json: A hardcoded file containing deterministic thresholds. Include dummy data for now: {"min_drain_budget_per_km": 150000, "historical_ward_avg": 3400000, "min_commercial_road_width_m": 12}.

rti_template.txt: A text file containing a generic RTI Act 2005 template with placeholder tags: [WARD_NUMBER], [BUDGET_HEAD], and [DISCREPANCY_DETAILS].

schema: Define a Pydantic schema for the LLM extraction: {ward_number: int, budget_head: str, amount_this_year: float, amount_last_year: float, drain_length_km: float, zone_new: str, stated_road_width: float}.

API Keys & Persistence:

The system will use a single GEMINI_API_KEY stored in a .env file.

Data persistence is limited to local file reads/writes (JSON/TXT). Do not configure PostgreSQL, SQLite, or MongoDB.

Execution Steps (Generate the code sequentially):

Step 1: Write extractor.py utilizing the Gemini Files API to upload a PDF and extract the data strictly matching the Pydantic schema defined above using Structured Outputs.

Step 2: Write evaluator.py that ingests the extracted JSON, reads rules.json, and performs deterministic arithmetic comparisons. It must return a Python dictionary: {"flag_triggered": bool, "plain_english_reason": str}.

Step 3: Write action_agent.py that takes the plain_english_reason, reads rti_template.txt, and makes a prompt call to Gemini to fill in the template placeholders accurately.

Step 4: Write main.py using FastAPI to expose a single endpoint (e.g., /process_pdf) that accepts a file upload, orchestrates Steps 1 through 3, and returns a JSON payload containing the validation logs and the final drafted RTI text. Ensure CORS is enabled so the forthcoming frontend can connect to it.

Please generate the code for these four steps now.