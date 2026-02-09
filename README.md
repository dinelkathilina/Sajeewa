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
- **ML Predictions**: Cost and time impact forecasting (in development)
- **Smart Context Search**: TF-IDF similarity for BOQ item matching

## 🛠️ Tech Stack

### Backend

- **Framework**: Python 3.10+, FastAPI
- **Database**: SQLAlchemy with SQLite
- **Data Processing**: Pandas, NumPy
- **CPM Analysis**: NetworkX
- **OCR**: Tesseract, pdf2image, Pillow
- **ML**: scikit-learn
- **PDF Generation**: ReportLab
- **AI Engine**: Groq API (Qwen-32B)

### Frontend

- **Framework**: React 18, Vite
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **HTTP Client**: Axios

## 🚀 Getting Started

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

**Linux:**

```bash
sudo apt-get install tesseract-ocr
```

**macOS:**

```bash
brew install tesseract
```

### Environment Configuration

Create a `.env` file in the project root:

```env
GROQ_API_KEY=your_groq_api_key_here
```

### Backend Setup

```bash
cd backend
pip install -r requirements.txt

# Run database migration (first time only)
cd ..
py -3 migrate_enhanced_schema.py

# Start backend server
cd backend
python -m backend.main
```

The API will run at `http://localhost:8000`

**API Documentation:** `http://localhost:8000/docs`

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

The UI will run at `http://localhost:5173`

## 📖 How to Use

### 1. Upload Project Files

**Required Files:**

- **BOQ** (Excel/CSV): Bill of Quantities with items, quantities, and rates
- **Rate Breakdown** (PDF/Excel/CSV): Material/Labor/Equipment cost breakdowns
- **Master Program** (Excel/CSV/XML): Project schedule with activities and dependencies

**Optional Files** (upload during variation evaluation):

- BSR (Basic Schedule of Rates)
- HSR (Historical Schedule of Rates)
- Quotations from suppliers
- Specifications and drawings

### 2. FIDIC Workflow

The system guides you through a structured workflow:

**Step 1: Variation Type Selection**

- System presents 6 FIDIC variation types
- Select the type that best describes your variation

**Step 2: Details Collection**

- Identify affected BOQ items
- Specify quantity/specification/method/location changes
- Link to affected schedule activities

**Step 3: Additional Files**

- Upload supporting documents (BSR/HSR/Quotations)
- System uses these for accurate rate determination

**Step 4: Evaluation**

- AI analyzes collected information
- Calculates cost impact using FIDIC 12.3 logic
- Performs CPM analysis for time impact
- Runs QS validation checks

### 3. Example Conversations

**Quantity Change:**

```
User: "I need to evaluate a variation for increasing Guard Stones quantity"
AI: "I'll help you with that. This appears to be a Type 1: Quantity Changes variation.
     Which BOQ item is affected?"
User: "Guard Stones, increase from 150 to 200 units"
AI: [Calculates cost impact using original rates]
```

**Time Impact:**

```
User: "The CEB Poles installation will be delayed by 15 days"
AI: "Let me analyze the schedule impact..."
    [Performs CPM analysis]
    "The CEB Poles activity is on the critical path. This delay will result in
     an EOT of 15 days."
```

### 4. Generate Proposal

Once evaluation is complete, generate a professional PDF proposal containing:

- Variation description and type
- Detailed cost breakdown by BOQ items
- Time impact analysis with CPM justification
- QS validation results
- Executive summary with recommendations

## 📁 Project Structure

```
Sajeewa/
├── backend/
│   ├── database.py              # Enhanced schema with 7 tables
│   ├── engine.py                # Cost & Time engines with CPM
│   ├── ml_model.py              # AI model with FIDIC workflow
│   ├── main.py                  # FastAPI application
│   ├── ocr_processor.py         # PDF OCR processing
│   ├── session_manager.py       # Conversation management
│   ├── validation_engine.py     # QS validation checks
│   ├── pdf_utils.py             # Professional PDF generation
│   └── requirements.txt         # Python dependencies
├── frontend/
│   ├── src/
│   │   ├── App.tsx              # Main application
│   │   ├── components/          # React components
│   │   └── ...
│   └── package.json
├── migrate_enhanced_schema.py   # Database migration script
├── .env                         # Environment variables
└── README.md
```

## 🗄️ Database Schema

### Core Tables

- **projects**: Project information and file references
- **boq_items**: Bill of Quantities items
- **rate_breakdowns**: Material/Labor/Equipment rates
- **variations**: Variation records with cost/time impacts

### Enhanced Tables

- **sessions**: Conversation session tracking
- **variation_types**: FIDIC variation categories (seeded)
- **activities**: Master program tasks with CPM data
- **additional_files**: Supporting documents (BSR/HSR/Quotations)
- **variation_details**: Detailed line items per variation
- **chat_messages**: Conversation history

## 🔌 API Endpoints

### File Upload

- `POST /upload/files` - Upload BOQ, Rate Breakdown, Schedule
- `POST /upload/additional-files` - Upload BSR/HSR/Quotations

### Session Management

- `POST /session/create` - Create new session
- `GET /session/{id}` - Get session context
- `POST /session/{id}/continue` - Resume session
- `POST /session/{id}/close` - Close session

### Chat & Evaluation

- `POST /chat` - Send message with FIDIC workflow support
- `GET /variation-types` - Get FIDIC variation types

### Validation

- `POST /variation/validate/{id}` - Run QS validation
- `GET /variation/validation-report/{id}` - Get validation report

### PDF Generation

- `POST /generate-pdf` - Generate variation proposal PDF

## 🧪 Testing

### Backend Tests

```bash
# Test OCR processing
py -3 -c "from backend.ocr_processor import ocr_processor; print(ocr_processor.is_pdf('test.pdf'))"

# Test CPM calculation
py -3 -c "from backend.engine import TimeEngine; te = TimeEngine(); te.parse_schedule('schedule.xlsx'); print(te.calculate_cpm_full())"

# Test validation
py -3 -c "from backend.validation_engine import ValidationEngine; from backend.database import SessionLocal; db = SessionLocal(); ve = ValidationEngine(db); print(ve.validate_variation(1))"
```

### Manual Testing

1. Upload sample files through the UI
2. Start a variation evaluation conversation
3. Follow the FIDIC workflow
4. Generate and review PDF proposal

## 🎯 Roadmap

### Completed ✅

- Database schema with session management
- OCR processing for PDF rate breakdowns
- Full CPM implementation (ES/EF/LS/LF/Float)
- QS validation engine (4 checks)
- FIDIC workflow integration
- Professional PDF generation
- Session-based conversation tracking

### In Progress 🚧

- FIDIC 12.3 rate determination logic
- BSR/HSR/Quotation parsing
- ML cost/time prediction models
- Frontend FIDIC workflow UI

### Planned 📋

- Historical data training for ML models
- Advanced visualization charts
- Multi-project comparison
- Export to Excel/Word formats
- Company branding customization

## 📄 License

This project is developed for dissertation research on "Change Management in Construction using Machine Learning."

## 🤝 Contributing

This is a research project. For questions or collaboration opportunities, please contact the developer.

---

**Version:** 2.0.0  
**Last Updated:** February 2026  
**Developed by:** Sajeewa  
**Research Focus:** ML-based Construction Variation Evaluation
