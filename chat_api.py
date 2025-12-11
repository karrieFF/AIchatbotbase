from fastapi import FastAPI, BackgroundTasks, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from uuid import uuid4, UUID
from contextlib import asynccontextmanager
from starlette.concurrency import run_in_threadpool
from chat_engine import GPTCoachEngine
from extractor import extract_and_store_for_session #function from the extractor.py
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


class SessionEndRequest(BaseModel):
    user_id: str
    session_id: str


class SessionEndResponse(BaseModel):
    status: str
    session_id: str
    smart_goals: Optional[Dict[str, Any]] = None

class MessageResponse(BaseModel):
    id: int
    session_id: str
    user_id: str
    role: str
    text: str
    created_at: str

# New Pydantic model for SMART Goal Response
class SMARTGoalResponse(BaseModel):
    user_id: str
    session_id: str
    specific: Optional[str] = None
    measurable: Optional[str] = None
    achievable: Optional[str] = None
    relevant: Optional[str] = None
    time_bound: Optional[str] = None
    schedule_time: Optional[str] = None
    created_at: Optional[str] = None

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
                SELECT p.name, p.phone, p.date_of_birth, p.gender, 
                p.height_cm, p.weight_kg, p.fitness_level, p.health_profile, 
                u.created_at
                FROM user_profiles p
                JOIN users u ON p.user_id = u.id
                WHERE p.user_id = %s
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
                "created_at": None
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
            "created_at": row[8].isoformat() if row[8] else None
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

# ... imports ...
from extractor import extract_and_store_for_session, store_smart_goals # Added store_smart_goals import

# ...

@app.post("/chat/end_session", response_model=SessionEndResponse)
def end_session(req: SessionEndRequest, background_tasks: BackgroundTasks): # Added background_tasks
    """
    Mark a chat session as finished.
    1. Extracts SMART goals immediately (Blocking) -> Returns to UI for Visualization.
    2. Saves SMART goals to DB in background (Parallel) -> Persist data.
    """
    # Validate IDs
    try:
        UUID(req.user_id)
        UUID(req.session_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user_id or session_id format")

    if db_sync.pg_pool is None:
        raise HTTPException(status_code=500, detail="Database not available")

    try:
        # 1. Run extraction immediately (blocking) but DO NOT save to DB yet
        extracted_goals = extract_and_store_for_session(req.session_id, save_to_db=False)
        
        # 2. Schedule the DB save in the background
        if extracted_goals:
            background_tasks.add_task(store_smart_goals, extracted_goals)

        # 3. Return the result for visualization immediately
        return SessionEndResponse(
            status="completed", 
            session_id=req.session_id,
            smart_goals=extracted_goals
        )
    except Exception as e:
        print(f"⚠ ERROR running SMART goal extraction for session {req.session_id}: {e}")
        return SessionEndResponse(status="failed", session_id=req.session_id)

@app.get("/activities/stats")
def get_activity_stats(
    user_id: str = Query(..., description="User ID"),
    period: str = Query("today", description="Period: today, yesterday, 2_days_ago, week, month")
    ):
    if db_sync.pg_pool is None:
        raise HTTPException(status_code=500, detail="Database not avaliable")

    conn = db_sync.pg_pool.getconn()

    try:
        with conn.cursor() as cur:

            #determin the data filter
            if period == "today":
                date_filter = "activity_date = CURRENT_DATE"
            elif period == "yesterday":
                date_filter = "activity_date = CURRENT_DATE - INTERVAL '1 day'"
            elif period == "2_days_ago":
                date_filter = "activity_date = CURRENT_DATE - INTERVAL '2 days'"
            elif period == "week":
                date_filter = "activity_date >= CURRENT_DATE - INTERVAL '7 days'"
            elif period == "month":
                date_filter = "activity_date >= CURRENT_DATE - INTERVAL '30 days'"
            else:
                # Default to today if unknown
                date_filter = "activity_date = CURRENT_DATE"


            cur.execute(f"""
            SELECT
                COALESCE(SUM(total_steps), 0) as total_steps,
                COALESCE(SUM(calorie), 0) as total_calories,
                COALESCE(SUM(sedentary_minutes), 0) as sedentary,
                COALESCE(SUM(very_active_minutes + fairly_active_minutes), 0) as MVPA
            From activity_data 
            WHERE user_id = %s AND {date_filter}"""
            , (user_id,))

            rows = cur.fetchone()

            return {
                'MVPA': rows[3],
                'Sedentary': rows[2],
                'Steps': rows[0],
                'Calories': rows[1],
                "activityCount": 1 if rows[0] > 0 else 0
            }
    except Exception as e:
        print(f"Error fetching activity chart: {e}")
        return {
            'MVPA': 0,
            'Sedentary': 0,
            'Steps': 0,
            'Calories': 0,
            "activityCount": 0
        }
    finally:
        db_sync.pg_pool.putconn(conn)
    
@app.get("/activities/chart")
def get_activity_chart(
    user_id: str = Query(..., description="User ID"),
    #period: str = Query("week", description="Period: week, month")
):
    if db_sync.pg_pool is None:
        raise HTTPException(status_code=500, detail="Database not available")
        
    conn = db_sync.pg_pool.getconn()
    try:
        with conn.cursor() as cur:
            cur.execute(f"""
                SELECT 
                    TO_CHAR(activity_date, 'Dy') as day,
                    COALESCE(total_steps, 0) as steps,
                    COALESCE(very_active_minutes + fairly_active_minutes, 0) as MVPA,
                    COALESCE(calorie, 0) as calories,
                    COALESCE(sedentary_minutes, 0) as sedentary,
                    activity_date
                FROM activity_data
                WHERE user_id = %s AND activity_date >= CURRENT_DATE - INTERVAL '7 days'
                ORDER BY activity_date ASC
            """, (user_id,))

            rows = cur.fetchall()

            #Map to frontend format
            chart_data = []
            for row in rows:
                chart_data.append({
                    "day": row[0],
                    "steps": row[1],
                    "MVPA": row[2],
                    "calories": row[3],
                    "sedentary": row[4],
                    "activity_date": row[5]
                })
            return chart_data
        
    except Exception as e:
        print(f"Error fetching activity chart: {e}")
        return []
    finally:
        db_sync.pg_pool.putconn(conn)

# --- NEW ENDPOINT TO FETCH GOALS ---
@app.get("/goals/smart", response_model=List[SMARTGoalResponse])
def get_smart_goals(
    user_id: str = Query(..., description="User ID to fetch goals for"),
    limit: int = Query(1, description="Number of recent goals to fetch")
):
    """
    Fetch the most recent extracted SMART goals for a user.
    """
    if db_sync.pg_pool is None:
        raise HTTPException(status_code=500, detail="Database not available")

    conn = db_sync.pg_pool.getconn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT 
                    user_id, session_id, 
                    specific, measurable, achievable, relevant, time_bound, 
                    schedule_time, created_at
                FROM extraction
                WHERE user_id = %s
                ORDER BY created_at DESC
                LIMIT %s
                """,
                (user_id, limit)
            )
            rows = cur.fetchall()
            
            goals = []
            for row in rows:
                goals.append({
                    "user_id": str(row[0]),
                    "session_id": str(row[1]),
                    "specific": row[2],
                    "measurable": row[3],
                    "achievable": row[4],
                    "relevant": row[5],
                    "time_bound": row[6],
                    "schedule_time": row[7],
                    "created_at": row[8].isoformat() if row[8] else None
                })
            return goals
    except Exception as e:
        print(f"Error fetching goals: {e}")
        return []
    finally:
        db_sync.pg_pool.putconn(conn)

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
