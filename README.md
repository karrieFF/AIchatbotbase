# AI Chatbot Base - Physical Activity Coach

A conversational AI chatbot system built with PyTorch and Transformers, designed to provide motivational interviewing-based health coaching for physical activity. The system supports a React PWA frontend and a FastAPI REST API, with automatic PostgreSQL database synchronization for conversation history.

## 🎯 Features

- **AI-Powered Coaching**: Uses Qwen2.5-0.5B-Instruct model (or 14B on Cloud GPU) for natural conversation.
- **Motivational Interviewing**: Implements MI principles for health coaching.
- **Multi-Platform Support**:
  - React Progressive Web App (PWA) for users.
  - FastAPI REST API for backend logic.
- **Database Integration**: Automatic sync to PostgreSQL (conversation history, user profiles, activity data).
- **Fitbit Integration**: Imports and analyzes Fitbit activity data.
- **Email OTP**: Secure passwordless login via email verification.
- **Cloud Deployment**: 
  - Frontend: Render (Static Site)
  - Backend: Render (Web Service)
  - Model: RunPod (for larger models)

## 📁 Project Structure

```
AIchatbotbase/
├── chat_api.py             # Main FastAPI REST API server
├── chat_engine.py          # Core chat engine with AI model logic
├── read_fitbit.py          # Script to import Fitbit CSV data to DB
├── cloud_gpu_model_service.py # Service for running model on RunPod
│
├── database/               # Database modules
│   ├── db_sync.py          # Synchronous PostgreSQL operations
│   ├── db_async.py         # Asynchronous PostgreSQL operations
│   └── db_migration.py     # Database migration utilities
│
├── models/                 # ML model utilities
│   ├── model_loader.py     # Model loading and initialization
│   └── prompt_template.py  # System prompts and templates
│
├── archive/                # Old/Unused files (backups)
├── docs/                   # Documentation and notes
├── requirements.txt        # Python dependencies for API
├── requirements_model.txt  # Python dependencies for Model Service
└── README.md               # This file
```

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- PostgreSQL 13+
- Node.js & npm (for frontend)

### 1. Installation

**Backend Setup**
```bash
git clone <repository-url>
cd AIchatbotbase
pip install -r requirements.txt
```

**Frontend Setup**
```bash
cd move-chat-sync
npm install
```

### 2. Database Setup

1.  **Create Database**:
    ```sql
    CREATE DATABASE chatbot_db;
    CREATE USER chatbot_user WITH PASSWORD 'chatbot2025';
    GRANT ALL PRIVILEGES ON DATABASE chatbot_db TO chatbot_user;
    ```
2.  **Run SQL Scripts**:
    Execute the SQL scripts in `database/` to create tables (`users`, `messages`, `activity_data`, `notifications`, `goals`, etc.).

### 3. Environment Variables (.env)

Create a `.env` file in `AIchatbotbase/`:

```env
# Database (Example Format)
DATABASE_URL=postgresql://chatbot_user:password@address

# Email (Resend or Gmail)
SENDER_EMAIL=your-email@resend.dev
RESEND_API_KEY=re_123456789

# Cloud Model (Optional)
CLOUD_GPU_URL=https://your-runpod-id-8000.proxy.runpod.net/v1 
```

### 4. Running the Application

**Run Backend (API)**

First, activate your virtual environment (e.g., `qwen_env`):

```powershell
# Windows
.\qwen_env\Scripts\activate
# OR specific path: C:\Users\flyka\qwen_env\Scripts\activate
```

Then run the API (Choose one method):

```bash
# Method 1: Direct Python
python chat_api.py

# Method 2: Uvicorn (Recommended for development)
uvicorn chat_api:app --reload
```
*API runs at `http://localhost:8000`*

**Run Frontend**
```bash
# In move-chat-sync/
npm run dev
```
*App runs at `http://localhost:5173`*

## ☁️ Deployment Guide

### Phase 1: Database (Render)
1.  Create a **PostgreSQL** database on Render.com (Free tier).
2.  Copy the `External Database URL`.
    *Format: `postgresql://cloud_database_name:password@address`*
3.  Connect via a local tool (DBeaver/pgAdmin) using that URL and run your SQL initialization scripts.

### Phase 2: Backend (Render)
1.  Create a **Web Service** on Render connected to this repo.
2.  **Root Directory**: `AIchatbotbase`
3.  **Build Command**: `pip install -r requirements.txt`
4.  **Start Command**: `uvicorn chat_api:app --host 0.0.0.0 --port $PORT`
5.  **Env Vars**: Add `CLOUD_GPU_URL`, `DATABASE_URL`, `RESEND_API_KEY`, etc.

### Phase 3: Frontend (Render)
1.  Create a **Static Site** on Render connected to this repo.
2.  **Root Directory**: `move-chat-sync`
3.  **Build Command**: `npm run build`
4.  **Publish Directory**: `dist`
5.  **Env Vars**: Set `VITE_API_BASE_URL` and `VITE_CHATBOT_API_URL` to your Render Backend URL (e.g., `https://active-api.onrender.com`).

### Phase 4: AI Model (RunPod - Optional)
*For running large models (14B+) that don't fit on Render Free Tier.*

1.  Deploy a GPU Pod on RunPod.io.
2.  Run the setup command in the RunPod terminal:

    **Option A: One-line Command (Recommended)**
    ```bash
    bash -c "cd /workspace && (test -d AIchatbotbase && (cd AIchatbotbase && git pull) || git clone https://github.com/karrieFF/AIchatbotbase.git) && cd AIchatbotbase && pip install -r requirements_model.txt && python cloud_gpu_model_service.py"
    ```

    **Option B: Manual Steps**
    ```bash
    cd /workspace
    git clone https://github.com/karrieFF/AIchatbotbase.git
    cd AIchatbotbase
    pip install -r requirements_model.txt
    python cloud_gpu_model_service.py
    ```

3.  Set `CLOUD_GPU_URL` in your Render Backend environment variables.

## 📝 API Usage Examples

**Chat Endpoint**
```http
POST /chat
Content-Type: application/json

{
  "message": "I want to start exercising",
  "user_id": "user123",
  "session_id": "session456"
}
```

**Fitbit Data Import**
```bash
python read_fitbit.py
```
> **Note:**
> 1. Set `DATABASE_URL` in `.env` to import to the **Cloud Database**.
> 2. Comment out or unset `DATABASE_URL` to import data to the **Local Database**.

## 🔐 Security Notes

- **Never commit .env files**.
- Use **Resend** for emails in production (port 587 is blocked on most free cloud tiers).
- The `read_fitbit.py` script requires `load_dotenv` to work with cloud databases.

## 👥 Authors

[Your Name/Organization]

## 🙏 Acknowledgments

- Qwen team for the Qwen2.5 model
- HuggingFace for transformers library
- Shadcn/UI for frontend components
