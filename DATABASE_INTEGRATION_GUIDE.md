# Database Integration Guide for Chat Data

This guide provides step-by-step instructions for storing chat conversations in a database.

## Table of Contents
1. [Database Options](#database-options)
2. [Database Schema Design](#database-schema-design)
3. [Installation Steps](#installation-steps)
4. [Implementation Steps](#implementation-steps)
5. [Code Integration](#code-integration)
6. [Testing](#testing)

---

## Database Options

### Option 1: SQLite (Recommended for Development/Simple Deployments)
- **Pros**: No separate server needed, easy setup, built into Python
- **Cons**: Not ideal for high concurrency, limited scalability
- **Best for**: Development, small-scale deployments

### Option 2: PostgreSQL (Recommended for Production)
- **Pros**: Excellent performance, ACID compliant, handles concurrency well
- **Cons**: Requires separate database server setup
- **Best for**: Production environments, multiple users

---

## Database Schema Design

### Recommended Schema

```sql
-- Table: Users (optional - if you want to store user metadata)
CREATE TABLE IF NOT EXISTS users (
    user_id TEXT PRIMARY KEY,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table: Sessions
CREATE TABLE IF NOT EXISTS sessions (
    session_id TEXT,
    user_id TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (session_id, user_id),
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- Table: Messages (stores individual messages in conversations)
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,  -- For SQLite
    -- id SERIAL PRIMARY KEY,  -- For PostgreSQL
    session_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    role TEXT NOT NULL,  -- 'user', 'assistant', or 'system'
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id, user_id) REFERENCES sessions(session_id, user_id) ON DELETE CASCADE
);

-- Indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id, user_id);
CREATE INDEX IF NOT EXISTS idx_messages_user ON messages(user_id);
CREATE INDEX IF NOT EXISTS idx_messages_created ON messages(created_at);
```

---

## Installation Steps

### For SQLite (No installation needed - built into Python)

SQLite comes with Python by default, but you may want to install a helper library:

```bash
pip install sqlalchemy
# OR
pip install aiosqlite  # For async operations
```

### For PostgreSQL

```bash
# Install PostgreSQL driver
pip install psycopg2-binary
# OR
pip install asyncpg  # For async operations

# If using SQLAlchemy (recommended)
pip install sqlalchemy psycopg2-binary
```

---

## Implementation Steps

### Step 1: Create Database Module

Create a new file `database.py` with database connection and operations.

### Step 2: Update Chat Engine

Modify `chat_engine.py` to load/save messages from database instead of memory.

### Step 3: Update API (Optional)

Add endpoints to retrieve chat history if needed.

---

## Code Integration

### Example 1: SQLite Implementation with SQLAlchemy

#### File: `database.py` (SQLite version)

```python
from sqlalchemy import create_engine, Column, String, Text, DateTime, Integer, ForeignKey, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import os

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    user_id = Column(String, primary_key=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Session(Base):
    __tablename__ = 'sessions'
    session_id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey('users.user_id', ondelete='CASCADE'), primary_key=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_accessed = Column(DateTime, default=datetime.utcnow)

class Message(Base):
    __tablename__ = 'messages'
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, nullable=False)
    user_id = Column(String, nullable=False)
    role = Column(String, nullable=False)  # 'user', 'assistant', 'system'
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index('idx_messages_session', 'session_id', 'user_id'),
        Index('idx_messages_user', 'user_id'),
        Index('idx_messages_created', 'created_at'),
    )

class Database:
    def __init__(self, db_path: str = "chat_data.db"):
        """Initialize database connection."""
        self.engine = create_engine(f'sqlite:///{db_path}', echo=False)
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
    
    def get_session(self):
        """Get a database session."""
        return self.SessionLocal()
    
    def save_message(self, user_id: str, session_id: str, role: str, content: str):
        """Save a single message to the database."""
        db = self.get_session()
        try:
            # Ensure user exists
            user = db.query(User).filter(User.user_id == user_id).first()
            if not user:
                user = User(user_id=user_id)
                db.add(user)
                db.commit()
            
            # Ensure session exists
            session = db.query(Session).filter(
                Session.session_id == session_id,
                Session.user_id == user_id
            ).first()
            if not session:
                session = Session(session_id=session_id, user_id=user_id)
                db.add(session)
            else:
                session.last_accessed = datetime.utcnow()
            
            # Save message
            message = Message(
                session_id=session_id,
                user_id=user_id,
                role=role,
                content=content
            )
            db.add(message)
            db.commit()
        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()
    
    def get_session_messages(self, user_id: str, session_id: str):
        """Retrieve all messages for a session."""
        db = self.get_session()
        try:
            messages = db.query(Message).filter(
                Message.user_id == user_id,
                Message.session_id == session_id
            ).order_by(Message.created_at).all()
            
            return [
                {"role": msg.role, "content": msg.content}
                for msg in messages
            ]
        finally:
            db.close()
    
    def get_user_sessions(self, user_id: str):
        """Get all sessions for a user."""
        db = self.get_session()
        try:
            sessions = db.query(Session).filter(
                Session.user_id == user_id
            ).order_by(Session.last_accessed.desc()).all()
            
            return [
                {"session_id": sess.session_id, "created_at": sess.created_at, "last_accessed": sess.last_accessed}
                for sess in sessions
            ]
        finally:
            db.close()
    
    def delete_session(self, user_id: str, session_id: str):
        """Delete a session and all its messages."""
        db = self.get_session()
        try:
            session = db.query(Session).filter(
                Session.session_id == session_id,
                Session.user_id == user_id
            ).first()
            if session:
                db.delete(session)
                db.commit()
        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()
```

### Example 2: PostgreSQL Implementation

For PostgreSQL, change the engine creation in `database.py`:

```python
# In Database.__init__:
def __init__(self, db_url: str = None):
    """Initialize database connection."""
    if db_url is None:
        # Default PostgreSQL connection string
        db_url = "postgresql://username:password@localhost:5432/chatbot_db"
    self.engine = create_engine(db_url, echo=False)
    Base.metadata.create_all(self.engine)
    self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
```

And update the Message model for PostgreSQL:

```python
class Message(Base):
    __tablename__ = 'messages'
    id = Column(Integer, primary_key=True)  # PostgreSQL uses SERIAL automatically
    # ... rest of the code stays the same
```

---

### Step 2: Update chat_engine.py

Modify your `chat_engine.py` to use the database:

```python
import torch
from model_loader import load_model
from text_cleaner import clean_response
from prompt_template import build_prompt
from database import Database  # Add this import

class GPTCoachEngine:
    def __init__(self, db_path: str = "chat_data.db"):
        # load once
        self.tokenizer, self.model = load_model()
        self.model.eval()
        # make greeting once
        self.greeting = self._make_greeting()
        
        # Initialize database
        self.db = Database(db_path)

    # ... _make_greeting method stays the same ...

    def _init_session(self, user_id: str, session_id: str, keep_greeting: bool = True) -> None:
        """Initialize a new session for a user with base prompt and greeting."""
        messages = build_prompt("")
        # Clean up empty user messages if present
        if len(messages) >= 2 and messages[1].get("role") == "user" and messages[1].get("content", "") == "":
            messages = [messages[0]]
        if keep_greeting:
            messages.append({"role": "assistant", "content": self.greeting})
        
        # Save initial messages to database
        for msg in messages:
            self.db.save_message(user_id, session_id, msg["role"], msg["content"])

    def _get_session_messages(self, user_id: str, session_id: str):
        """Get messages for a user's session from database, creating it if it doesn't exist."""
        messages = self.db.get_session_messages(user_id, session_id)
        
        # If session doesn't exist or is empty, initialize it
        if not messages:
            self._init_session(user_id, session_id)
            messages = self.db.get_session_messages(user_id, session_id)
        
        return messages

    def chat(self, user_text: str, user_id: str = "default", session_id: str = "default") -> str:
        """One turn of chat: add user → generate → clean → add assistant → return text."""
        # Save user message to database
        self.db.save_message(user_id, session_id, "user", user_text)
        
        # Get full message history from database
        messages = self.db.get_session_messages(user_id, session_id)

        # Convert messages to chat template format
        chat_text = self.tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
        )

        inputs = self.tokenizer(chat_text, return_tensors="pt").to(self.model.device)

        # Generate outputs
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=80,
                temperature=0.4,
                top_p=0.7,
                do_sample=True,
                eos_token_id=self.tokenizer.eos_token_id,
            )

        # Decode only new tokens
        new_tokens = outputs[0][inputs["input_ids"].shape[1]:]
        response = self.tokenizer.decode(new_tokens, skip_special_tokens=True)
        response = clean_response(response)

        # Save assistant response to database
        self.db.save_message(user_id, session_id, "assistant", response)

        return response
```

---

### Step 3: Optional - Add API Endpoints for History

Add to `chat_api.py`:

```python
from database import Database
from typing import List

db = Database()

@app.get("/sessions/{user_id}")
def get_user_sessions(user_id: str):
    """Get all sessions for a user."""
    sessions = db.get_user_sessions(user_id)
    return {"user_id": user_id, "sessions": sessions}

@app.get("/history/{user_id}/{session_id}")
def get_chat_history(user_id: str, session_id: str):
    """Get chat history for a specific session."""
    messages = db.get_session_messages(user_id, session_id)
    return {
        "user_id": user_id,
        "session_id": session_id,
        "messages": messages
    }

@app.delete("/sessions/{user_id}/{session_id}")
def delete_session(user_id: str, session_id: str):
    """Delete a session and its history."""
    db.delete_session(user_id, session_id)
    return {"status": "deleted", "user_id": user_id, "session_id": session_id}
```

---

## Testing

### Test the Database Integration

Create a test file `test_database.py`:

```python
from database import Database

# Initialize database
db = Database("test_chat.db")

# Test saving messages
db.save_message("user1", "session1", "user", "Hello!")
db.save_message("user1", "session1", "assistant", "Hi there!")

# Test retrieving messages
messages = db.get_session_messages("user1", "session1")
print("Messages:", messages)

# Test getting user sessions
sessions = db.get_user_sessions("user1")
print("User sessions:", sessions)
```

Run it:
```bash
python test_database.py
```

---

## Migration Strategy

If you want to migrate from in-memory storage to database:

1. **Gradual Migration**: Start using database for new sessions, keep old sessions in memory temporarily
2. **One-time Export**: Write a script to export existing `self.sessions` data to database
3. **Hybrid Approach**: Load from database on startup, keep hot sessions in memory for speed

---

## Environment Variables (Recommended)

Create a `.env` file for configuration:

```
# For SQLite
DB_TYPE=sqlite
DB_PATH=chat_data.db

# For PostgreSQL
# DB_TYPE=postgresql
# DB_URL=postgresql://user:password@localhost:5432/chatbot_db
```

Then use `python-dotenv` to load:
```bash
pip install python-dotenv
```

```python
from dotenv import load_dotenv
import os

load_dotenv()

db_type = os.getenv("DB_TYPE", "sqlite")
if db_type == "sqlite":
    db_path = os.getenv("DB_PATH", "chat_data.db")
    db = Database(db_path)
else:
    db_url = os.getenv("DB_URL")
    db = Database(db_url)
```

---

## Important Notes

1. **Backup**: Regularly backup your database
2. **Connection Pooling**: For production, configure connection pooling
3. **Indexing**: The schema includes indexes for common queries
4. **Cleanup**: Consider adding a cleanup job to delete old sessions
5. **Security**: Never expose database credentials in code - use environment variables
6. **Async**: For high concurrency, consider async database libraries (aiosqlite, asyncpg)

---

## Quick Start Checklist

- [ ] Choose database (SQLite or PostgreSQL)
- [ ] Install required packages (`sqlalchemy`, etc.)
- [ ] Create `database.py` with Database class
- [ ] Update `chat_engine.py` to use database
- [ ] Test with simple script
- [ ] Optionally add history endpoints to API
- [ ] Set up environment variables
- [ ] Test full integration
- [ ] Set up database backups

---

## Need Help?

- SQLAlchemy docs: https://docs.sqlalchemy.org/
- SQLite: https://www.sqlite.org/docs.html
- PostgreSQL: https://www.postgresql.org/docs/

