# AI Chatbot Base - Physical Activity Coach

A conversational AI chatbot system built with PyTorch and Transformers, designed to provide motivational interviewing-based health coaching for physical activity. The system supports both Gradio web interface and FastAPI REST API, with automatic PostgreSQL database synchronization for conversation history.

## 🎯 Features

- **AI-Powered Coaching**: Uses Qwen2.5-0.5B-Instruct model for natural conversation
- **Motivational Interviewing**: Implements MI principles for health coaching
- **Multi-Interface Support**: 
  - Gradio web UI (`app.py`)
  - FastAPI REST API (`chat_api.py`)
  - Command-line interface (`main_model.py`)
- **Database Integration**: Automatic conversation history sync to PostgreSQL
- **Session Management**: Supports multiple users and sessions with conversation history
- **Production Ready**: Includes connection pooling, error handling, and background task processing

## 📁 Project Structure

```
AIchatbotbase/
├── app.py                  # Gradio web interface
├── chat_api.py             # FastAPI REST API server
├── chat_engine.py          # Core chat engine with AI model
├── main_model.py           # Command-line interface
│
├── database/               # Database modules
│   ├── __init__.py         # Package initialization
│   ├── db_sync.py          # Synchronous PostgreSQL operations
│   ├── db_async.py         # Asynchronous PostgreSQL operations
│   ├── db_migration.py     # Database migration utilities
│   └── template_db.sql     # Database schema SQL
│
├── models/                 # ML model utilities
│   ├── __init__.py         # Package initialization
│   ├── model_loader.py     # Model loading and initialization
│   ├── text_cleaner.py     # Response cleaning utilities
│   └── prompt_template.py  # System prompts and templates
│
├── tests/                  # Test files
│   └── test_db_async.py   # Database async tests
│
├── requirements.txt         # Python dependencies
├── README.md               # This file
└── .gitignore              # Git ignore patterns
```

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- PostgreSQL 11+
- CUDA-compatible GPU (optional, CPU supported)

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd AIchatbotbase
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up PostgreSQL**
   ```bash
   # Create database and user
   psql -U postgres
   CREATE DATABASE chatbot_db;
   CREATE USER chatbot_user WITH PASSWORD 'chatbot2025';
   GRANT ALL PRIVILEGES ON DATABASE chatbot_db TO chatbot_user;
   \c chatbot_db
   GRANT ALL ON SCHEMA public TO chatbot_user;
   ```

4. **Create database tables**
   ```bash
   psql -U chatbot_user -d chatbot_db -f database/template_db.sql -W
   ```

5. **Set environment variables**
   ```bash
   # Windows PowerShell
   $env:DB_USER = "chatbot_user"
   $env:DB_PASSWORD = "your_password"
   $env:DB_HOST = "localhost"
   $env:DB_PORT = "5432"
   $env:DB_NAME = "chatbot_db"
   
   # Linux/Mac
   export DB_USER=chatbot_user
   export DB_PASSWORD=your_password
   export DB_HOST=localhost
   export DB_PORT=5432
   export DB_NAME=chatbot_db
   ```

### Running the Application

**Option 1: Gradio Web Interface**
```bash
python app.py
```
Access at `http://localhost:7860`

**Option 2: FastAPI REST API**
```bash
python chat_api.py
# Or with uvicorn
uvicorn chat_api:app --reload
```
API docs at `http://localhost:8000/docs`

**Option 3: Command Line**
```bash
python main_model.py
```

## 📚 File Documentation

### Core Application Files

#### `app.py`
Gradio-based web interface for the chatbot. Provides a user-friendly chat interface with automatic database synchronization.

**Key Features:**
- Web-based chat interface
- Automatic conversation history
- Session management
- Clear chat functionality

**Usage:**
```python
python app.py
```

#### `chat_api.py`
FastAPI REST API server for programmatic access to the chatbot. Supports async operations and background task processing.

**Endpoints:**
- `GET /` - Health check
- `POST /chat` - Send message and get response

**Request Format:**
```json
{
  "message": "Hello, I want to be more active",
  "user_id": "optional_user_id",
  "session_id": "optional_session_id"
}
```

**Response Format:**
```json
{
  "reply": "Hello! I'd be happy to help you...",
  "user_id": "user_id",
  "session_id": "session_id"
}
```

#### `chat_engine.py`
Core chat engine that manages conversations, model inference, and database synchronization.

**Key Components:**
- `GPTCoachEngine`: Main engine class
  - `chat()`: Process user messages and generate responses
  - `_get_session_messages()`: Retrieve conversation history
  - `_save_to_db()`: Save messages to database

**Features:**
- Session-based conversation management
- Automatic database sync (non-blocking)
- Model inference with configurable parameters

#### `main_model.py`
Simple command-line interface for testing the chatbot interactively.

**Usage:**
```bash
python main_model.py
# Type "exit" or "quit" to stop
```

### Database Files

#### `db_sync.py`
Synchronous PostgreSQL database operations using `psycopg2` with connection pooling.

**Functions:**
- `init_sync_pool()`: Initialize connection pool
- `save_message_sync()`: Save message to database
- `close_sync_pool()`: Close connection pool

**Configuration:**
Reads from environment variables:
- `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`, `DB_NAME`

#### `db_async.py`
Asynchronous PostgreSQL operations using `asyncpg` for high-performance async operations.

**Functions:**
- `init_db_pool()`: Initialize async connection pool
- `save_message()`: Async save message
- `close_db_pool()`: Close async pool

**Use Case:** Best for FastAPI async endpoints

#### `db_migration.py`
Database migration utilities using Alembic (if configured).

**Note:** Currently contains template migration code. Configure Alembic for production use.

#### `template_db.sql`
SQL schema for creating the `messages` table and indexes.

**Tables:**
- `messages`: Stores conversation history
  - `id`: Auto-increment primary key
  - `session_id`: UUID for session identification
  - `user_id`: UUID for user identification
  - `role`: Message role (user/assistant/system)
  - `text`: Message content
  - `metadata`: JSONB for additional data
  - `created_at`: Timestamp

### Model Files

#### `model_loader.py`
Handles loading and initialization of the Qwen2.5-0.5B-Instruct model.

**Functions:**
- `load_model()`: Load tokenizer and model from HuggingFace

**Configuration:**
- Model: `Qwen/Qwen2.5-0.5B-Instruct`
- Device: Auto (GPU if available, else CPU)
- Dtype: float32

#### `text_cleaner.py`
Cleans and post-processes model responses to remove artifacts and improve readability.

**Functions:**
- `clean_response()`: Remove role tags, system prompts, and duplicate lines

**Processing Steps:**
1. Remove role tokens (user/assistant/system)
2. Remove system prompt echoes
3. Deduplicate consecutive identical lines

#### `prompt_template.py`
Defines the system prompt and message templates for motivational interviewing coaching.

**Functions:**
- `build_prompt()`: Create message list with system prompt

**Key Features:**
- Comprehensive MI coaching instructions
- Stage-based conversation flow (Engaging, Focusing, Evoking, Planning, Closing)
- OARS communication techniques
- Person-centered approach

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DB_USER` | PostgreSQL username | `chatbot_user` |
| `DB_PASSWORD` | PostgreSQL password | `chatbot2025` |
| `DB_HOST` | Database host | `localhost` |
| `DB_PORT` | Database port | `5432` |
| `DB_NAME` | Database name | `chatbot_db` |

### Model Configuration

Edit `model_loader.py` to change:
- Model name/version
- Device (CPU/GPU)
- Data type (float32/float16)

### Generation Parameters

Edit `chat_engine.py` to adjust:
- `max_new_tokens`: Response length (default: 80)
- `temperature`: Creativity (default: 0.4)
- `top_p`: Nucleus sampling (default: 0.7)

## 🗄️ Database Schema

```sql
CREATE TABLE messages (
    id BIGSERIAL PRIMARY KEY,
    session_id UUID NOT NULL,
    user_id UUID NOT NULL,
    role VARCHAR(16) NOT NULL,
    text TEXT NOT NULL,
    metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

**Indexes:**
- `idx_messages_session`: On `session_id`
- `idx_messages_user`: On `user_id`
- `idx_messages_created_at`: On `created_at`

## 🔐 Security Notes

- **Never commit passwords** to version control
- Use environment variables for sensitive data
- Restrict database user permissions in production
- Consider using `.env` files with `python-dotenv`

## 🧪 Testing

Run database tests:
```bash
python -m pytest tests/
```

## 📝 API Usage Examples

### Python Example
```python
import requests

response = requests.post(
    "http://localhost:8000/chat",
    json={
        "message": "I want to start exercising",
        "user_id": "user123",
        "session_id": "session456"
    }
)
print(response.json())
```

### cURL Example
```bash
curl -X POST "http://localhost:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Hello",
    "user_id": "user123",
    "session_id": "session456"
  }'
```

## 🐛 Troubleshooting

### Database Connection Issues
- Verify PostgreSQL is running: `pg_isready`
- Check environment variables are set correctly
- Ensure database and user exist
- Verify table permissions: `GRANT ALL PRIVILEGES ON TABLE messages TO chatbot_user;`

### Model Loading Issues
- Check internet connection (for first-time download)
- Verify CUDA is available if using GPU
- Check disk space for model cache

### Gradio Share Link Issues
- Share links require internet connection
- Use `share=False` for local-only access

## 📦 Dependencies

See `requirements.txt` for complete list. Key dependencies:
- `torch`: PyTorch for model inference
- `transformers`: HuggingFace transformers
- `gradio`: Web interface
- `fastapi`: REST API framework
- `psycopg2-binary`: PostgreSQL sync driver
- `asyncpg`: PostgreSQL async driver

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

[Add your license here]

## 👥 Authors

[Add author information]

## 🙏 Acknowledgments

- Qwen team for the Qwen2.5 model
- HuggingFace for transformers library
- Gradio for easy web interface creation

