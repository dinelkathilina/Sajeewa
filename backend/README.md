# Variation Evaluation Backend 🧪🐍

FastAPI-based server for processing construction variations with AI-driven analysis.

## 🚀 Setup Instructions

1. **Install Dependencies**:

   ```bash
   pip install -r requirements.txt
   ```

2. **Environment Variables**:
   Ensure you have a `.env` file in the root or `backend/` folder with:

   ```env
   GROQ_API_KEY=your_key_here
   ```

3. **Run Server**:
   ```bash
   python -m backend.main
   ```

## 🏗️ Architecture

- **`main.py`**: Entrance point and REST endpoints.
- **`engine.py`**: Core logic for Cost (FIDIC 12.3) and Time (CPM/Marginal Analysis).
- **`ml_model.py`**: NLP layer using Groq to extract structured data from user chat.
- **`storage_manager.py`**: File-based persistence layer using JSON.
- **`ocr_processor.py`**: Tesseract-powered OCR for rate breakdown extraction.

## 📂 Data Storage

Project data is stored in `backend/data/`:

- `projects_index.json`: Main index of all uploaded projects.
- `project_{id}.json`: Detailed breakdown of BOQ, activities, and variations for a specific project.
