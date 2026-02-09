# AI Construction Variation Assistant 🏗️🤖

An intelligent platform designed for Quantity Surveyors and Project Managers to automate the evaluation of construction variations (claims). The system uses **Groq-powered AI (Qwen-32B)** to assess cost and time impacts with professional precision.

## 🌟 Key Features

- **AI-Driven Reasoning**: Specialized Construction Intelligence using the Groq API and Qwen-32B model to interpret messy project data.
- **Hybrid File Support**:
  - **Excel BOQs**: Aggressive multi-sheet parsing for complex Bills of Quantities.
  - **CSV Rate Breakdowns**: Automated extraction of Material, Labor, and Equipment costs.
  - **CSV Schedules**: Critical Path Method (CPM) analysis for Extension of Time (EOT) claims.
- **FIDIC 12.3 Logic**: Implements standard international construction contract principles to determine new rates (Star Rates) vs. contract rates.
- **Professional PDF Generation**: Automated creation of structured variation proposals ready for submittal.
- **Smart Context Search**: TF-IDF based similarity search to ensure the AI never loses context, even in long conversations.

## 🛠️ Tech Stack

- **Backend**: Python 3.10+, FastAPI, SQLAlchemy (SQLite), Pandas, NetworkX (CPM analysis), ReportLab (PDFs).
- **Frontend**: React, Vite, TypeScript, Axios, Tailwind CSS (optional).
- **AI Engine**: Groq API (Qwen-32B Reasoning Model).

## 🚀 Getting Started

### 1. Prerequisites

- Python 3.10 or higher
- Node.js & npm (for frontend)
- Groq API Key

### 2. Environment Configuration

Create a `.env` file in the project root:

```env
GROQ_API_KEY=your_groq_api_key_here
```

### 3. Backend Setup

```bash
cd backend
pip install -r requirements.txt
python main.py
```

_The API will run at `http://localhost:8000`_

### 4. Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

_The UI will run at `http://localhost:5173`_

## 📖 How to Use

1. **Upload Files**: Start by uploading your Project BOQ (Excel), Rate Breakdown (CSV), and Schedule (CSV).
2. **Chat with the Assistant**:
   - Ask: _"What is the cost impact if we change Guard Stones to 200 units?"_
   - Ask: _"What is the EOT if the CEB Poles task is delayed by 15 days?"_
3. **Generate Proposal**: Once satisfied with the analysis, the system identifies the intent and prepares a **Variation Proposal PDF**.

## 📄 License

This project is developed for dissertation research on "Change Management in Construction using Machine Learning."

---

_Developed by Sajeewa_
