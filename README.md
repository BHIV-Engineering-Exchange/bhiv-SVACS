# SVACS Vision Runtime + Demo Integration

This workspace contains an integrated project for vessel detection and the SVACS demo dashboard.

## Folder structure

- `backend/` — Python FastAPI vessel vision runtime and training utilities
- `frontend/` — cloned `svacs-demo` repository with dashboard frontend and demo backend services
- `README.md` — this document
- `requirements.txt` — Python dependencies for the backend

## Backend

The backend is located in `backend/`.

### Install

1. Create a Python environment.
2. Install Python dependencies:

```bash
pip install -r requirements.txt
```

### Run

```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Train

```bash
cd backend
python train_model.py
```

This will also copy the best trained weights to `backend/vessel_front_model.pt`.

### API test

```bash
cd backend
python test_api.py ship1.jpeg
```

## Frontend

The frontend is located in `frontend/`.

### Install

```bash
cd frontend
npm install
```

### Run

Option 1: use the helper script

```powershell
cd C:\Users\vijay\Downloads\svacs-main\svacs-main
run-frontend.cmd
```

Option 2: use the installed Node CLI directly

```powershell
cd C:\Users\vijay\Downloads\svacs-main\svacs-main\frontend
"C:\Program Files\nodejs\npm.cmd" install
"C:\Program Files\nodejs\npm.cmd" run dev -- --host 0.0.0.0 --port 5173 --open
```

The dashboard can then be accessed in the browser at the local Vite URL shown in the terminal. If port `5173` is in use, Vite will automatically choose another port such as `5174` and print it in the console.

## Notes

- The backend uses `backend/vessel_front_model.pt` by default.
- If you want to use a different model path, update `backend/app/core/config.py` or set the `YOLO_MODEL_PATH` environment variable.
- The frontend is a separate Node.js/Vite project and uses `frontend/package.json` for dependencies.
