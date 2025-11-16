from fastapi import FastAPI, BackgroundTasks, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
from uuid import uuid4, UUID
from contextlib import asynccontextmanager
from starlette.concurrency import run_in_threadpool
from chat_engine import GPTCoachEngine
from database import (
    init_db_pool,
    close_db_pool,
    init_sync_pool,
    close_sync_pool,
    save_message_sync
)
import database.db_sync as db_sync


#this is to determine if the id is validate
def validate_or_generate_uuid(value: Optional[str]) -> str:
    """
    Validate UUID or generate a new one.
    Treats None, empty string, or "default" as invalid and generates new UUID.
    """
    if not value or value == "default" or value.strip() == "":
        return str(uuid4())
    
    # Try to validate if it's a valid UUID format
    try:
        UUID(value)
        return value
    except (ValueError, AttributeError):
        # If not a valid UUID, generate a new one
        return str(uuid4())

#db_sync
@asynccontextmanager
async def lifespan(app):
    # startup (async and sync pools)
    await init_db_pool()
    init_sync_pool()
    try:
        yield
    finally:
        # shutdown (close async and sync pools)
        await close_db_pool()
        close_sync_pool()

app = FastAPI(lifespan=lifespan)


#CORS (Cross‑Origin Resource Sharing) controls which websites (origins) are allowed to call your API from the browser.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

#create one chatbot for all users
engine = GPTCoachEngine ()

class ChatRequest(BaseModel):
    message: str
    user_id: Optional[str] = None
    session_id: Optional[str] = None

class ChatResponse(BaseModel):
    reply: str
    user_id: str
    session_id: str

class MessageResponse(BaseModel):
    id: int
    session_id: str
    user_id: str
    role: str
    text: str
    created_at: str

def get_messages_from_db(session_id: str, limit: int = 50) -> List[dict]:
    """Retrieve messages from database for a given session."""
    if db_sync.pg_pool is None:
        return []
    
    conn = db_sync.pg_pool.getconn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, session_id, user_id, role, text, created_at
                FROM messages
                WHERE session_id = %s
                ORDER BY created_at ASC
                LIMIT %s
                """,
                (session_id, limit)
            )
            rows = cur.fetchall()
            messages = []
            for row in rows:
                # Convert backend format to frontend format
                # Backend uses: role ("user" or "assistant"), text
                # Frontend expects: sender ("user" or "ai"), message
                role = row[3]  # "user" or "assistant"
                sender = "ai" if role == "assistant" else "user"
                
                messages.append({
                    "id": str(row[0]),
                    "user_id": str(row[2]),
                    "sender": sender,  # Convert "assistant" to "ai"
                    "message": row[4],  # Use "message" instead of "text"
                    "created_at": row[5].isoformat() if row[5] else None
                })
            return messages
    except Exception as e:
        print(f"⚠ Error fetching messages: {e}")
        return []
    finally:
        db_sync.pg_pool.putconn(conn)


@app.get("/")
async def root():
    return {"message": "Server is running!"} #def root

#CREATE GLOBAL id by looking throug the database
class UserCreate(BaseModel):
    email:str

class UserResponse(BaseModel):
    id:str
    email:str

@app.post("/users/register", response_model=UserResponse)
def register_user(user: UserCreate):
    if db_sync.pg_pool is None:
        raise RuntimeError("Database not avaliable")

    conn = db_sync.pg_pool.getconn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, email FROM users WHERE email = %s", (user.email,))
            row = cur.fetchone()
            if row:
                return UserResponse(id=str(row[0]), email=row[1])

            #) otherwise create new users (DB auto-generates id)
            cur.execute(
                "INSERT INTO users (email) VALUES (%s) RETURNING id, email",
                (user.email,),
            )
            row = cur.fetchone()
        conn.commit()
        return UserResponse(id=str(row[0]), email=row[1])
    finally:
        db_sync.pg_pool.putconn(conn)


@app.get("/chat/messages")
def get_messages(
    session_id: str = Query(..., description="Session ID to retrieve messages for"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of messages to retrieve")
):
    """
    Retrieve chat messages for a given session.
    """
    messages = get_messages_from_db(session_id, limit)
    return {"messages": messages}

@app.get("/users/profile")
def get_profile (user_id: str = Query(..., description="User ID")):
    if db_sync.pg_pool is None:
        raise RuntimeError("Database not available")
    
    conn = db_sync.pg_pool.getconn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT name, phone, date_of_birth, gender, 
                height_cm, weight_kg, fitness_level, health_profile
                FROM user_profiles
                WHERE user_id = %s
                """,
                (user_id,),
            )
            row = cur.fetchone()

        if not row:
            return {
                "name": None,
                "phone": None,
                "date_of_birth": None,
                "gender": None,
                "height_cm": None,
                "weight_kg": None,
                "fitness_level": None,
                "health_profile": None,
            }

        return {
            "name": row[0],
            "phone": row[1],
            "date_of_birth": row[2],
            "gender": row[3],
            "height_cm": row[4],
            "weight_kg": row[5],
            "fitness_level": row[6],
            "health_profile": row[7],
        }
    finally:
        db_sync.pg_pool.putconn(conn)

@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest, background_tasks: BackgroundTasks):
    """
    Chat endpoint with automatic database sync.
    Uses background tasks to sync without blocking the response.
    """
    # 1) Require user_id from frontend (global ID)
    if not req.user_id:
        raise HTTPException(status_code=400, detail="user_id is required")

    # 2) Validate user_id format (must be UUID, but do NOT generate a new one)
    try:
        UUID(req.user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user_id format")

    user_id = req.user_id #trust global ID

    # 3) session_id: validate or generate new per conversation
    session_id = validate_or_generate_uuid(req.session_id)

    # Get reply synchronously (this is the slow part)
    reply = engine.chat(req.message, user_id=user_id, session_id=session_id)

    # Wrapper function to handle errors in background tasks
    def save_with_error_handling(session_id: str, user_id: str, role: str, text: str):
        try:
            save_message_sync(session_id, user_id, role, text)
        except Exception as e:
            print(f"⚠ CRITICAL: Background task failed to save {role} message:")
            print(f"  Error: {e}")
            print(f"  Session: {session_id}, User: {user_id}")
            import traceback
            traceback.print_exc()

    # Schedule DB writes in background (runs after response is returned)
    # This doesn't block the user - they get response immediately
    background_tasks.add_task(save_with_error_handling, session_id, user_id, "user", req.message)
    background_tasks.add_task(save_with_error_handling, session_id, user_id, "assistant", reply)

    return ChatResponse(reply=reply, user_id=user_id, session_id=session_id)

#user profile udpate
class UserProfileUpdate(BaseModel):
    user_id: str
    name: str | None = None
    phone: str | None = None
    date_of_birth: str | None = None  # "YYYY-MM-DD"
    gender: str | None = None
    height_cm: int | None = None
    weight_kg: int | None = None
    fitness_level: str | None = None
    health_profile: str | None = None

@app.put("/users/profile", response_model=UserProfileUpdate)
def upsert_profile(profile: UserProfileUpdate):
    if db_sync.pg_pool is None:
        raise RuntimeError("Database not available")

    conn = db_sync.pg_pool.getconn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO user_profiles
                  (user_id, name, phone, date_of_birth, gender,
                   height_cm, weight_kg, fitness_level, health_profile)
                VALUES
                  (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (user_id) DO UPDATE SET
                  name = EXCLUDED.name,
                  phone = EXCLUDED.phone,
                  date_of_birth = EXCLUDED.date_of_birth,
                  gender = EXCLUDED.gender,
                  height_cm = EXCLUDED.height_cm,
                  weight_kg = EXCLUDED.weight_kg,
                  fitness_level = EXCLUDED.fitness_level,
                  health_profile = EXCLUDED.health_profile,
                  updated_at = now()
                """,
                (
                    profile.user_id,
                    profile.name,
                    profile.phone,
                    profile.date_of_birth,
                    profile.gender,
                    profile.height_cm,
                    profile.weight_kg,
                    profile.fitness_level,
                    profile.health_profile,
                ),
            )
        conn.commit()
        return profile
    finally:
        db_sync.pg_pool.putconn(conn)