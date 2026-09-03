# FastAPI Backend Service

This directory contains the FastAPI emergency intake backend service.

## Prerequisites

- Python 3.10+ installed on your system.

## Installation

1. **(Optional) Upgrade `pip`**:
   ```bash
   python -m pip install --upgrade pip
   ```

2. **Install FastAPI with standard dependencies (includes Uvicorn, Pydantic, etc.)**:
   ```bash
   pip install "fastapi[standard]"
   ```

---

## Running the Server

### Option A: From the Root Directory (Recommended)
Run the server using the Python module syntax:
```bash
python -m uvicorn backend.main:app --reload
```

### Option B: From inside the `backend/` Directory
Navigating into `backend/`:
```bash
cd backend
python -m uvicorn main:app --reload
```

> **Note on Windows / Terminal environments**:  
> Running `python -m uvicorn ...` ensures Uvicorn runs correctly even if your Python `Scripts` directory (e.g., `C:\Python314\Scripts`) is not added to your system `PATH` environment variable.

---

## API Documentation & Verification

Once the server is running:
- **Base URL**: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)  
  Returns: `{"message": "Working good"}`
- **Interactive OpenAPI (Swagger) Docs**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc Documentation**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)
