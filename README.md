# ML Construction Variation Evaluation System 🏗️🤖

A professional FIDIC-compliant platform for automated construction variation assessment with Machine Learning predictions, OCR processing, and comprehensive QS validation.

## 🌟 Key Features

### Core Capabilities

- **FIDIC Workflow**: Guided evaluation for 6 variation types (Quantity, Quality, Position, Omission, Additional Work, Sequence/Timing)
- **AI-Powered Chatbot**: Groq API with Qwen-32B for intelligent conversation and data extraction
- **Session Management**: Multi-variation conversations with full context retention
- **PDF OCR Processing**: Automatic rate extraction from scanned documents using Tesseract
- **CPM Analysis**: Full Critical Path Method with ES/EF/LS/LF/Float calculations
- **QS Validation**: Automated checks for double counting, omissions, delay propagation, and rate reasonableness
- **Professional PDF Output**: Comprehensive variation proposals with cost breakdowns, EOT analysis, and validation results

### Technical Features

- **Hybrid File Support**:
  - Excel/CSV BOQs with multi-sheet parsing
  - PDF/Excel/CSV Rate Breakdowns with OCR
  - Excel/CSV/XML Master Programs with CPM
- **FIDIC 12.3 Logic**: Star rate determination with BSR/HSR/Quotation support
- **ML Predictions**: Cost and time impact forecasting
- **Smart Context Search**: TF-IDF similarity for BOQ item matching

## 🛠️ Tech Stack

### Backend

- **Framework**: Python 3.10+, FastAPI
- **Storage**: JSON-based file system (No separate DB required)
- **Data Processing**: Pandas, NumPy
- **CPM Analysis**: NetworkX
- **OCR**: Tesseract, pdf2image, Pillow
- **AI Engine**: Groq API (Qwen-32B)

### Frontend

- **Framework**: React 18, Vite
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **HTTP Client**: Axios

## 🐳 Quick Start with Docker (Recommended for other laptops)

The easiest way to run this application on any laptop is using Docker. This automatically handles all dependencies like Python, Node.js, and Tesseract OCR.

### 1. Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running.

### 2. Setup

1. Create a `.env` file in the project root with your API key:
   ```env
   GROQ_API_KEY=your_groq_api_key_here
   ```
2. Run the following command in the project root:
   ```bash
   docker-compose up --build
   ```

### 3. Access

- **Frontend UI**: http://localhost:5173
- **Backend API**: http://localhost:8000

---

## 🚀 Manual Setup (Development)

### Prerequisites

- Python 3.10 or higher
- Node.js 18+ & npm
- Groq API Key ([Get one here](https://console.groq.com))
- **Tesseract OCR** (for PDF processing)

### Tesseract OCR Installation

**Windows:**

1. Download installer: https://github.com/UB-Mannheim/tesseract/wiki
2. Install to default location: `C:\Program Files\Tesseract-OCR`
3. Add to system PATH or the application will auto-detect

**Linux/macOS:** install via `apt-get` or `brew`.

### Environment Configuration

Create a `.env` file in the project root:

```env
GROQ_API_KEY=your_groq_api_key_here
```

### Backend Setup

```bash
cd backend
pip install -r requirements.txt

# Start backend server
python -m backend.main
```

The API will run at `http://localhost:8000`

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

The UI will run at `http://localhost:5173`

## ⚖️ QS Logic Scenarios

The system is refined to handle complex Quantity Change variations:

### 1. Cost Marginal Analysis

Uses the formula: **Variation Cost = New Rate \* (New Total Qty - Original Qty)**.
The system automatically calculates the delta impact based on the new total quantity provided.

### 2. Time Impact (EOT)

Uses **Marginal Time Analysis**: **Time Impact = (New Qty - Original Qty) / Productivity**.
If an activity is on the critical path, the project duration is recalculated using the delta time.

### 3. Missing Norms (Work Study)

If no productivity norms are found in HSR/BSR, the AI proactively requests **Site Work Study Data** (e.g., "20 m2/day") to perform precise duration calculations.

## 🤝 Contributing

This is developed for research on "Change Management in Construction using Machine Learning."

**Version:** 2.1.0  
**Last Updated:** February 2026
