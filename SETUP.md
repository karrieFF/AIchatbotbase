# Setup Guide

## Step-by-Step Installation

### 1. Prerequisites Installation

**Python 3.8+**
```bash
python --version  # Should be 3.8 or higher
```

**PostgreSQL 11+**
- Windows: Download from [postgresql.org](https://www.postgresql.org/download/windows/)
- Linux: `sudo apt-get install postgresql postgresql-contrib`
- macOS: `brew install postgresql`

### 2. Clone and Navigate

```bash
git clone <repository-url>
cd AIchatbotbase
```

### 3. Create Virtual Environment (Recommended)

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python -m venv venv
source venv/bin/activate
```

### 4. Install Dependencies

```bash
pip install -r requirements.txt
```

### 5. PostgreSQL Setup

**Start PostgreSQL service:**
```bash
# Windows
net start postgresql-x64-14  # Adjust version number

# Linux
sudo systemctl start postgresql

# macOS
brew services start postgresql
```

**Create database and user:**
```bash
psql -U postgres
```

Then run:
```sql
CREATE DATABASE chatbot_db;
CREATE USER chatbot_user WITH PASSWORD 'your_secure_password';
GRANT ALL PRIVILEGES ON DATABASE chatbot_db TO chatbot_user;
\c chatbot_db
GRANT ALL ON SCHEMA public TO chatbot_user;
```

**Create tables:**
```bash
psql -U chatbot_user -d chatbot_db -f database/template_db.sql -W
```

**Grant permissions:**
```sql
-- Connect as postgres user
psql -U postgres -d chatbot_db

-- Grant permissions
GRANT ALL PRIVILEGES ON TABLE messages TO chatbot_user;
GRANT USAGE, SELECT ON SEQUENCE messages_id_seq TO chatbot_user;
```

### 6. Configure Environment Variables

**Windows PowerShell:**
```powershell
$env:DB_USER = "chatbot_user"
$env:DB_PASSWORD = "your_secure_password"
$env:DB_HOST = "localhost"
$env:DB_PORT = "5432"
$env:DB_NAME = "chatbot_db"
```

**Windows CMD:**
```cmd
set DB_USER=chatbot_user
set DB_PASSWORD=your_secure_password
set DB_HOST=localhost
set DB_PORT=5432
set DB_NAME=chatbot_db
```

**Linux/Mac:**
```bash
export DB_USER=chatbot_user
export DB_PASSWORD=your_secure_password
export DB_HOST=localhost
export DB_PORT=5432
export DB_NAME=chatbot_db
```

**Or create `.env` file:**
```env
DB_USER=chatbot_user
DB_PASSWORD=your_secure_password
DB_HOST=localhost
DB_PORT=5432
DB_NAME=chatbot_db
```

And install python-dotenv:
```bash
pip install python-dotenv
```

### 7. Verify Installation

**Test database connection:**
```python
from database import init_sync_pool
init_sync_pool()
print("Database connection successful!")
```

**Test model loading:**
```python
from models import load_model
tokenizer, model = load_model()
print("Model loaded successfully!")
```

### 8. Run the Application

Choose one of the interfaces:

**Gradio Web UI:**
```bash
python app.py
```

**FastAPI REST API:**
```bash
python chat_api.py
# Or with uvicorn:
uvicorn chat_api:app --reload --host 0.0.0.0 --port 8000
```

**Command Line:**
```bash
python main_model.py
```

## Troubleshooting

### Database Connection Issues

1. **Check PostgreSQL is running:**
   ```bash
   pg_isready
   ```

2. **Verify credentials:**
   ```bash
   psql -U chatbot_user -d chatbot_db -W
   ```

3. **Check table exists:**
   ```sql
   \dt messages
   ```

### Model Download Issues

- First run downloads the model (~1GB)
- Requires internet connection
- Model cached in `~/.cache/huggingface/`

### Import Errors

- Ensure virtual environment is activated
- Verify all dependencies installed: `pip list`
- Check Python path includes project directory

### Permission Errors

- Ensure `chatbot_user` has permissions on `messages` table
- Run grants as `postgres` superuser
- Check sequence permissions

## Next Steps

- Read the main [README.md](README.md) for detailed documentation
- Check [API documentation](http://localhost:8000/docs) when running FastAPI
- Review code comments for customization options

