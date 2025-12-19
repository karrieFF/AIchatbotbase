# AI Chatbot Base - Physical Activity Coach

A conversational AI chatbot system built with PyTorch and Transformers, designed to provide motivational interviewing-based health coaching for physical activity. The system supports a React PWA frontend and a FastAPI REST API, with automatic PostgreSQL database synchronization for conversation history.

## 🎯 Features

- **AI-Powered Coaching**: Uses Qwen2.5-0.5B-Instruct model (or 14B on Cloud GPU) for natural conversation.
- **Motivational Interviewing**: Implements MI principles for health coaching.
- **SMART Goals Extraction**: Automatically extracts and stores SMART goals from conversations using LLM.
- **Activity Tracking**: View activity statistics and charts with date range filtering.
- **User Profiles**: Manage user profiles with health metrics, fitness levels, and personal information.
- **Notifications System**: Check-in reminders and notification management.
- **Multi-Platform Support**:
  - React Progressive Web App (PWA) for users.
  - FastAPI REST API for backend logic.
- **Database Integration**: Automatic sync to PostgreSQL (conversation history, user profiles, activity data, SMART goals).
- **Fitbit Integration**: Imports and analyzes Fitbit activity data.
- **Email OTP**: Secure passwordless login via email verification (Resend API for production, Gmail SMTP for local).
- **Cloud Deployment**: 
  - Frontend: Render (Static Site)
  - Backend: Render (Web Service)
  - Model: RunPod (for larger models)

## 📁 Project Structure

```
AIchatbotbase/
├── chat_api.py             # Main FastAPI REST API server
├── chat_engine.py          # Core chat engine with AI model logic
├── extractor.py             # SMART goals extraction from conversations
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
    CREATE USER chatbot_user WITH PASSWORD 'password';
    GRANT ALL PRIVILEGES ON DATABASE chatbot_db TO chatbot_user;
    ```
2.  **Run SQL Scripts**:
    Execute the SQL scripts in `database/` to create tables (`users`, `messages`, `activity_data`, `notifications`, `goals`, etc.).

### 3. Environment Variables (.env)

Create a `.env` file in `AIchatbotbase/`:

```env
# Database (Example Format)
DATABASE_URL=postgresql://chatbot_user:password@address

# Email Configuration (To send to ANY email)

RESEND_API_KEY=re_123456789

# Option 1: Resend API (Recommended for production)
1）Get a domain from cloudflare: https://www.cloudflare.com/products/registrar/
2) Verify a domain at https://resend.com/domains

RESEND_SENDER_EMAIL=noreply@activehappiness.org

# Option 2: Gmail SMTP (For local development)
# SENDER_EMAIL=your-email@gmail.com
# GMAIL_APP_PASSWORD=your-app-password

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

## 📧 Email Configuration (Resend)

### Sending to Any Email Address

By default, Resend's testing mode only allows sending to verified email addresses. To send emails to **any email address**:

#### Step 1: Add Domain in Resend

1. Go to https://resend.com/domains
2. Sign in to your Resend account
3. Click **"Add Domain"** or **"Add New Domain"**
4. Enter your domain (e.g., `yourdomain.com`)
5. Click **"Add Domain"**

#### Step 2: Verify Domain in Cloudflare

Resend will show you DNS records that need to be added. Follow these steps in **Cloudflare**:

1. **Log in to Cloudflare Dashboard**
   - Go to https://dash.cloudflare.com
   - Select your domain

2. **Navigate to DNS Settings**
   - Click **"DNS"** in the left sidebar
   - Click **"Records"** tab

3. **Add SPF Record (TXT)**
   - Click **"Add record"**
   - **Type**: `TXT`
   - **Name**: `@` (or your root domain)
   - **Content**: `v=spf1 include:resend.com ~all`
   - **TTL**: `Auto` (or `3600`)
   - Click **"Save"**

4. **Add DKIM Record (TXT)**
   - Click **"Add record"** again
   - **Type**: `TXT`
   - **Name**: Copy the exact name from Resend (usually something like `resend._domainkey` or `resend-domainkey`)
   - **Content**: Copy the exact value from Resend (a long string)
   - **TTL**: `Auto` (or `3600`)
   - Click **"Save"**

5. **Add DMARC Record (TXT, Optional but Recommended)**
   - Click **"Add record"** again
   - **Type**: `TXT`
   - **Name**: `_dmarc`
   - **Content**: `v=DMARC1; p=none;`
   - **TTL**: `Auto` (or `3600`)
   - Click **"Save"**

6. **Wait for Propagation**
   - DNS changes typically take 5-30 minutes in Cloudflare
   - Resend will automatically check and verify your domain
   - You'll see a **"Verified"** status in Resend when complete

#### Step 3: Configure Environment Variable

Once your domain is verified, set the environment variable:

**In your `.env` file:**
```env
RESEND_SENDER_EMAIL=noreply@yourdomain.com
```

**Or with a display name:**
```env
RESEND_SENDER_EMAIL="ActiveLife <noreply@yourdomain.com>"
```

**In Render (Production):**
1. Go to your Render service dashboard
2. Navigate to **"Environment"** tab
3. Add new environment variable:
   - **Key**: `RESEND_SENDER_EMAIL`
   - **Value**: `noreply@yourdomain.com`
4. Save and redeploy

#### Step 4: Restart Your Application

After setting the environment variable, restart your application. You'll see a confirmation message in the startup logs:

```
✓ EMAIL CONFIG: Using Resend with verified domain (noreply@yourdomain.com)
   → Can send to any email address
```

### Testing Mode (Default)

If you don't set `RESEND_SENDER_EMAIL`, the app uses `onboarding@resend.dev` which:
- ✅ Works immediately (no domain verification needed)
- ❌ Can only send to your verified email address (e.g., `fly.karrie@gmail.com`)
- ✅ Automatically falls back to Gmail SMTP if Resend fails

### Fallback Behavior

The app automatically falls back to Gmail SMTP if:
- Resend API fails due to testing mode restrictions
- Resend API key is not set
- Any other Resend error occurs

This ensures emails are always sent, even if Resend has issues.

## 📝 API Usage Examples

### Authentication

**Request OTP**
```http
POST /auth/request-otp
Content-Type: application/json

{
  "email": "user@example.com"
}
```

**Verify OTP**
```http
POST /auth/verify-otp
Content-Type: application/json

{
  "email": "user@example.com",
  "code": "123456"
}
```

### Chat

**Send Message**
```http
POST /chat
Content-Type: application/json

{
  "message": "I want to start exercising",
  "user_id": "dac50355-5dcb-4376-aa00-0f5bde2e2f11",
  "session_id": "session456"
}
```

**Get Messages**
```http
GET /chat/messages?session_id=session456&limit=50
```

**End Session & Extract SMART Goals**
```http
POST /chat/end_session
Content-Type: application/json

{
  "user_id": "dac50355-5dcb-4376-aa00-0f5bde2e2f11",
  "session_id": "session456"
}
```

### SMART Goals

**Get SMART Goals**
```http
GET /goals/smart?user_id=dac50355-5dcb-4376-aa00-0f5bde2e2f11&limit=50
```

**Get SMART Goals by Date**
```http
GET /goals/smart?user_id=dac50355-5dcb-4376-aa00-0f5bde2e2f11&date=2025-01-15&limit=1
```

### Activity Data

**Get Activity Stats**
```http
GET /activity/stats?user_id=dac50355-5dcb-4376-aa00-0f5bde2e2f11&start_date=2025-01-01&end_date=2025-01-07
```

**Get Activity Chart Data**
```http
GET /activities/chart?user_id=dac50355-5dcb-4376-aa00-0f5bde2e2f11&start_date=2025-01-01&end_date=2025-01-07
```

### User Profile

**Get Profile**
```http
GET /users/profile?user_id=dac50355-5dcb-4376-aa00-0f5bde2e2f11
```

**Update Profile**
```http
PUT /users/profile
Content-Type: application/json

{
  "user_id": "dac50355-5dcb-4376-aa00-0f5bde2e2f11",
  "name": "John Doe",
  "phone": "+1234567890",
  "date_of_birth": "1990-01-01",
  "gender": "male",
  "height_cm": 175,
  "weight_kg": 70,
  "fitness_level": "intermediate",
  "health_profile": "No known health issues"
}
```

### Notifications

**Get Notifications**
```http
GET /notifications?user_id=dac50355-5dcb-4376-aa00-0f5bde2e2f11
```

**Mark Notification as Read**
```http
POST /notifications/{notification_id}/read
```

**Delete Notification**
```http
DELETE /notifications/{notification_id}
```

### Fitbit Data Import
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
