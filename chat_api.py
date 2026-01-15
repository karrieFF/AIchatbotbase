from fastapi import FastAPI, BackgroundTasks, Query, HTTPException, UploadFile, File, Form
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
from extractor import extract_and_store_for_session, store_smart_goals # Added store_smart_goals import
from datetime import datetime, timedelta, timezone
#send gmail package
import smtplib #Simple Mail Transfer Protocol (SMTP) is a protocol used to send emails
from email.mime.text import MIMEText

#RESEND PACKAGE
import random
import string
from datetime import datetime, timedelta, timezone
import os
import requests
from dotenv import load_dotenv
import shutil 

print("DEBUG: Loading environment variables")

load_dotenv()

#---CONFIGURATION -----
#---send from google （for local testing）
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SENDER_EMAIL = "flyhellowellness@gmail.com"
SENDER_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "ysbq qezl asab dvcq")  # Use env var, fallback to hardcoded for local

#---send from resend (for production)
RESEND_API_KEY = os.getenv("RESEND_API_KEY") 
SENDER_EMAIL2 = 'noreply@activehappiness.org' #ActiveLife <onboarding@resend.dev> for showing ActiveLife 
USE_RESEND = bool(RESEND_API_KEY and RESEND_API_KEY.strip())  # True if API key exists and is not empty

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
engine = GPTCoachEngine () #we can not create one chatbot for all users

#the placeholder for another llm chatbot
#we can put another llm chatbot here
#example: engine2 = GPTCoachEngine()

# class is to define the standard format of inside computer communication
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

#CREATE GLOBAL id by looking throug the database
class UserCreate(BaseModel):
    email:str

class UserResponse(BaseModel):
    id:str
    email:str

class NotificationResponse(BaseModel):
    id: str
    title: str
    description: str
    time: str
    type: str
    unread: bool

# registration and verification models
class OTPRequest(BaseModel):
    email: str

class VerifyOTPRequest(BaseModel):
    email: str
    code: str

#three chat request
class ChatRequest(BaseModel):
    message: str
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    backend_mode: Optional[str] = None  # "llm1", "llm2", or "human"

#coach participant connection
class CoachParticipant(BaseModel):
    participant_id: str
    participant_name: Optional[str] = None
    unread_count: int

#coach reply and request 
class CoachReplyRequest(BaseModel):
    coach_id: str
    participant_id: str
    session_id: str
    message: str

class CoachReplyResponse(BaseModel):
    status: str

@app.get("/")
async def root():
    return {"message": "Server is running!"} #def root

#---------register functions----
def _send_email_resend(email:str, code:str):
    """Send OTP email using Resend API (works on Render free tier)"""
    try:
        if not RESEND_API_KEY:
            print(f"⚠ WARNING: RESEND_API_KEY not set. OTP for {email}: {code}")
            return False
            
        response = requests.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {RESEND_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "from": SENDER_EMAIL2,
                "to": [email],
                "subject": "Your Verification Code",
                "html": f"""
                    <h2>Your Verification Code</h2>
                    <p>Your verification code is: <strong>{code}</strong></p>
                    <p>This code expires in 10 minutes.</p>
                """,
            },
            timeout=10  # 10 second timeout
        )
        
        if response.status_code == 200:
            print(f"✓ Email sent to {email}")
            return True
        else:
            print(f"✗ Resend API error: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"Failed to send email: {e}")
        return False

def _send_email_smtp(email:str, code:str):
    try:
        msg = MIMEText(f"Your verification code is: {code}\n\nThis code expires in 10 minutes.")
        msg['Subject'] = "Your Verification Code"
        msg['From'] = SENDER_EMAIL
        msg['To'] = email

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.send_message(msg)
        return True
        print(msg)
    except Exception as e:
        print(f"Failed to send email: {e}")
        return False

def send_email_otp(email: str, code: str):
    """
    Send OTP email using Resend API (production) or SMTP (local).
    Automatically chooses based on RESEND_API_KEY environment variable.
    """
    if USE_RESEND:
        # Production: Use Resend API (works on Render)
        return _send_email_resend(email, code)
    else:
        # Local: Use Gmail SMTP
        return _send_email_smtp(email, code)

#--------------get the backend mode for the user-------
def get_backend_mode_for_user(user_id: str) -> str:
    """
    Look up backend_mode for a user in the users table.
    Fallback to 'ptcoach' if not set or DB is unavailable.
    """
    if db_sync.pg_pool is None:
        return "ptcoach"

    conn = db_sync.pg_pool.getconn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT backend_mode FROM users WHERE id = %s", (user_id,))
            row = cur.fetchone()
            if row and row[0]:
                return row[0]
            return "ptcoach"
    finally:
        db_sync.pg_pool.putconn(conn)

# Wrapper function to handle errors in background tasks
def save_with_error_handling(session_id: str, user_id: str, role: str, text: str, metadata: Optional[dict] = None):
    try:
        save_message_sync(session_id, user_id, role, text, metadata=metadata)
    except Exception as e:
        print(f"⚠ CRITICAL: Background task failed to save {role} message:")
        print(f"  Error: {e}")
        print(f"  Session: {session_id}, User: {user_id}")
        import traceback
        traceback.print_exc()

@app.post("/auth/request-otp")
def request_otp(req: OTPRequest):
    #print(f"DEBUG: Request OTP for email: {req.email}")
    if db_sync.pg_pool is None:
        raise HTTPException(status_code=500, detail="Database not available")

    # 1. Generate Code
    code = ''.join(random.choices(string.digits, k=6))
    expiration = datetime.now(timezone.utc) + timedelta(minutes=10)

    conn = db_sync.pg_pool.getconn()
    try:
        with conn.cursor() as cur:
            # Check if user exists
            cur.execute("SELECT id FROM users WHERE email = %s", (req.email,))
            if not cur.fetchone():
                # Option A: Auto-register user (Easiest for prototype)
                cur.execute("INSERT INTO users (email) VALUES (%s)", (req.email,))
                # Option B: Return error if you want strict registration
                # raise HTTPException(status_code=404, detail="User not found")

            # Update User with Code
            cur.execute("""
                UPDATE users 
                SET verification_code = %s, code_expires_at = %s 
                WHERE email = %s
            """, (code, expiration, req.email))
            conn.commit()
            
            # Send Email
            #print(f"DEBUG: OTP for {req.email}: {code}") # Print to console for testing
            send_email_otp(req.email, code) # Uncomment to use real email
            
            return {"message": "Verification code sent"}
    finally:
        db_sync.pg_pool.putconn(conn)

@app.post("/auth/verify-otp")
def verify_otp(req: VerifyOTPRequest):
    if db_sync.pg_pool is None:
        raise HTTPException(status_code=500, detail="Database not available")

    conn = db_sync.pg_pool.getconn()
    try:
        with conn.cursor() as cur:
            # Check Code
            cur.execute("""
                SELECT id FROM users 
                WHERE email = %s 
                AND verification_code = %s 
                AND code_expires_at > NOW()
            """, (req.email, req.code))
            
            row = cur.fetchone()
            
            if row:
                user_id = str(row[0])
                # Clear code so it can't be reused
                cur.execute("UPDATE users SET verification_code = NULL WHERE id = %s", (user_id,))
                conn.commit()
                return {"user_id": user_id, "status": "success"}
            else:
                raise HTTPException(status_code=401, detail="Invalid or expired code")
    finally:
        db_sync.pg_pool.putconn(conn)

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

#--------split chat endpoint -------------
@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest, background_tasks: BackgroundTasks):
    """
    Chat endpoint with automatic database sync.
    Supports:
      - ptcoach  → GPTCoachEngine (engine)
      - ptftcoach → GPTCoachEngineV2 (engine_v2, when available)
      - human → human coach, no LLM
    """
    # 1) Require user_id from frontend (global ID)
    if not req.user_id:
        raise HTTPException(status_code=400, detail="user_id is required")

    try:
        UUID(req.user_id) #must be UUID, but do NOT generate a new one
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user_id format")

    user_id = req.user_id #trust global ID
    session_id = validate_or_generate_uuid(req.session_id)

    # 2) determine backend_mode
    if req.backend_mode:
        backend_mode = req.backend_Mode
    else:
        backend_mode = get_backend_mode_for_user(user_id)

    if backend_mode in ('ptcoach', 'ptftcoach'):
        #for now, use the same, we can update later
        reply = engine.chat(req.message, user_id=user_id, session_id=session_id)

        # Schedule DB writes in background (user + assistant), tagging backend_mode
        background_tasks.add_task(
            save_with_error_handling,
            session_id, user_id, "user", req.message,
            {"backend_mode": backend_mode}
        )
        background_tasks.add_task(
            save_with_error_handling,
            session_id, user_id, "assistant", reply,
            {"backend_mode": backend_mode}
        )

        return ChatResponse(reply=reply, user_id=user_id, session_id=session_id)

    elif backend_mode == "human":

        standby_text = "Your message has been sent to your coach. They'll reply soon."

        # Save ONLY the user message and mark needs_reply = True; DO NOT call LLM
        background_tasks.add_task(
            save_with_error_handling,
            session_id, user_id, "user", req.message,
            {"backend_mode": backend_mode, "needs_reply": True}
        )

        # Return an acknowledgement (frontend will show this as a short coach message)
        return ChatResponse(reply=standby_text, user_id=user_id, session_id=session_id)

    else:
        raise HTTPException(status_code=400, detail=f"Invalid backend_mode: {backend_mode}")

#-----get coach participants----------------
@app.get("/coach/participants", response_model=List[CoachParticipant])
def get_coach_participants(coach_id: str = Query(..., description="Coach user ID")):
    """
    For coach users: list assigned participants with count of unread (needs_reply) messages.
    Uses users.assigned_coach_id instead of a mapping table.
    """
    if db_sync.pg_pool is None:
        raise HTTPException(status_code=500, detail="Database not available")

    try:
        UUID(coach_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid coach_id format")

    conn = db_sync.pg_pool.getconn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT 
                    p.id AS participant_id,
                    COALESCE(up.name, p.email) AS participant_name,
                    COALESCE(
                      COUNT(*) FILTER (
                        WHERE m.role = 'user'
                          AND (m.metadata->>'needs_reply')::boolean = true
                          AND COALESCE((m.metadata->>'replied')::boolean, 'false')::boolean = false
                      ),
                      0
                    ) AS unread_count
                FROM users p
                LEFT JOIN user_profiles up ON up.user_id = p.id
                LEFT JOIN messages m 
                  ON m.user_id = p.id
                WHERE p.assigned_coach_id = %s
                GROUP BY p.id, participant_name
                ORDER BY participant_name
                """,
                (coach_id,),
            )
            rows = cur.fetchall()
            return [
                CoachParticipant(
                    participant_id=str(r[0]),
                    participant_name=r[1],
                    unread_count=r[2],
                )
                for r in rows
            ]
    finally:
        db_sync.pg_pool.putconn(conn)

#------------coach reply messages ------------
@app.post("/coach/reply", response_model=CoachReplyResponse)
def coach_reply(req: CoachReplyRequest):
    """
    Coach sends a reply to a participant.
    Stored as role='assistant' so it shows as coach/AI in participant chat.
    Also clears needs_reply on that participant's messages for this session.
    """
    if db_sync.pg_pool is None:
        raise HTTPException(status_code=500, detail="Database not available")

    # Basic ID validation
    try:
        UUID(req.coach_id)
        UUID(req.participant_id)
        UUID(req.session_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid ID format")

    conn = db_sync.pg_pool.getconn()
    try:
        with conn.cursor() as cur:
            # 1) Insert coach reply as assistant message
            cur.execute(
                """
                INSERT INTO messages (session_id, user_id, role, text, metadata)
                VALUES (%s, %s, 'assistant', %s,
                        jsonb_build_object(
                          'backend_mode', 'human',
                          'assigned_coach_id', %s
                        ))
                """,
                (req.session_id, req.participant_id, req.message, req.coach_id),
            )

            # 2) Mark previous user messages for this session as replied
            cur.execute(
                """
                UPDATE messages
                SET metadata = COALESCE(metadata, '{}'::jsonb) || jsonb_build_object('replied', true)
                WHERE user_id = %s
                  AND session_id = %s
                  AND role = 'user'
                  AND (metadata->>'needs_reply')::boolean = true
                  AND COALESCE((metadata->>'replied')::boolean, 'false')::boolean = false
                """,
                (req.participant_id, req.session_id),
            )

            conn.commit()

        return CoachReplyResponse(status="ok")

    except Exception as e:
        conn.rollback()
        print(f"Error saving coach reply: {e}")
        raise HTTPException(status_code=500, detail="Failed to save reply")
    finally:
        db_sync.pg_pool.putconn(conn)

# --- SMART goals endpoint ---
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

#-----------SMART goals visualization endpoint--------------
@app.get("/goals/smart", response_model=List[SMARTGoalResponse])
def get_smart_goals(
    user_id: str = Query(..., description="User ID to fetch goals for"),
    limit: int = Query(1, description="Number of recent goals to fetch"),
    date: str = Query(None, description="Optional date (YYYY-MM-DD). Returns latest goal on or before this date."),
):
    """
    Fetch the most recent extracted SMART goals for a user.
    If 'date' is provided, return the latest goal whose created_at::date is <= date.
    """
    if db_sync.pg_pool is None:
        raise HTTPException(status_code=500, detail="Database not available")

    conn = db_sync.pg_pool.getconn()
    try:
        with conn.cursor() as cur:
            if date:
                cur.execute(
                    """
                    SELECT 
                        user_id, session_id, 
                        specific, measurable, achievable, relevant, time_bound, created_at
                    FROM extraction
                    WHERE user_id = %s
                      AND created_at::date <= %s::date
                    ORDER BY created_at DESC
                    LIMIT %s
                    """,
                    (user_id, date, limit)
                )
            else:
                cur.execute(
                    """
                    SELECT 
                        user_id, session_id, 
                        specific, measurable, achievable, relevant, time_bound, created_at
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
                    "created_at": row[7].isoformat() if row[7] else None
                })
            return goals
    except Exception as e:
        print(f"Error fetching goals: {e}")
        return []
    finally:
        db_sync.pg_pool.putconn(conn)


@app.get("/activity/stats")
async def get_activity_stats(user_id: str, start_date:str = None, end_date:str = None):
    # Logic:
    # 1. If NO dates: Default to single day = CURRENT_DATE
    # 2. If ONLY start: Default end = start (Single Day mode)
    # 3. If BOTH: Use Range
    if not start_date:
        start_date = "CURRENT_DATE"
        end_date = "CURRENT_DATE"
    else:
        start_date = f"'{start_date}'"

    if not end_date:
        end_date = start_date #single day
    else:
        end_date = f"'{end_date}'" #range

    conn = db_sync.pg_pool.getconn()
    try:
        with conn.cursor() as cur:
            cur.execute(f"""
                SELECT 
                    COALESCE(total_steps, 0) as steps,
                    COALESCE(very_active_minutes + fairly_active_minutes, 0) as mvpa,
                    COALESCE(sedentary_minutes, 0) as sedentary,
                    COALESCE(calorie, 0) as calories
                FROM activity_data 
                WHERE user_id = %s 
                AND activity_date >= {start_date}
                AND activity_date <= {end_date}
            """, (user_id,))
            
            row = cur.fetchone()
            
            if row:
                return {
                    "Steps": row[0],
                    "MVPA": row[1],
                    "Sedentary": row[2],
                    "Calories": row[3],
                    "activityCount": 0 # Placeholder if you don't track count
                }
            else:
                # Return zeros if no data found for that date
                return {
                    "Steps": 0, "MVPA": 0, "Sedentary": 0, "Calories": 0, "activityCount": 0
                }
    finally:
        db_sync.pg_pool.putconn(conn)
    
@app.get("/activities/chart")
def get_activity_chart(
    user_id: str = Query(..., description="User ID"),
    start_date: str = Query(None, description="Start date YYYY-MM-DD"),
    end_date: str = Query(None, description="End date YYYY-MM-DD"),
):
    if db_sync.pg_pool is None:
        raise HTTPException(status_code=500, detail="Database not available")

    # Default window: last 7 days (including today)
    if not end_date:
        end_date_sql = "CURRENT_DATE"
    else:
        end_date_sql = f"'{end_date}'"

    if not start_date:
        start_date_sql = "CURRENT_DATE - INTERVAL '6 days'"
    else:
        start_date_sql = f"'{start_date}'"

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
                WHERE user_id = %s 
                  AND activity_date >= {start_date_sql}
                  AND activity_date <= {end_date_sql}
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


#-----notifications endpoint-------------





# --- put the profile  @put: put something already exists---
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

#----notifications endpoint-------------
@app.get("/notifications", response_model=List[NotificationResponse])
def get_notifications(user_id: str = Query(..., description="User ID")):
    if db_sync.pg_pool is None:
        raise HTTPException(status_code=500, detail="Database not available")
    
    conn = db_sync.pg_pool.getconn()
    try:
        with conn.cursor() as cur:
            # 1. CHECK IF WE NEED TO GENERATE A NEW CHECK-IN REMINDER
            cur.execute("SELECT MAX(created_at) FROM messages WHERE user_id = %s", (user_id,))
            row = cur.fetchone()
            last_active = row[0] if row else None
            
            if last_active:
                now = datetime.now(last_active.tzinfo) if last_active.tzinfo else datetime.now()
                days_since = (now - last_active).days
                
                # Logic: 7-14 days since last message AND it's after 6 PM
                # (You can temporarily set these to True for testing as we discussed)
                #is_checkin_window = 7 <= days_since <= 14
                #is_evening = now.hour >= 18 
    #------------------------testing code------------------
                is_checkin_window = True
                is_evening = True

                if is_checkin_window and is_evening:
                    # Check if we already created a notification for this user TODAY
                    cur.execute("""
                        SELECT id FROM notifications 
                        WHERE user_id = %s 
                        AND type = 'check_in' 
                        AND created_at::date = CURRENT_DATE
                    """, (user_id,))
                    
                    if not cur.fetchone():
                        # Create the notification in the DB
                        new_id = str(uuid4())
                        title = "Time to check in"
                        desc = f"It's been {days_since} days since your last session. Let's see how you're doing."
                        
                        cur.execute("""
                            INSERT INTO notifications (id, user_id, type, title, description, is_read, is_deleted)
                            VALUES (%s, %s, 'check_in', %s, %s, FALSE, FALSE)
                        """, (new_id, user_id, title, desc))
                        conn.commit()

            # 2. FETCH ALL ACTIVE NOTIFICATIONS FROM DB
            cur.execute("""
                SELECT id, title, description, created_at, type, is_read
                FROM notifications
                WHERE user_id = %s AND is_deleted = FALSE
                ORDER BY created_at DESC
            """, (user_id,))
            
            rows = cur.fetchall()
            results = []
            for row in rows:
                results.append({
                    "id": str(row[0]),
                    "title": row[1],
                    "description": row[2],
                    "time": row[3].isoformat() if row[3] else None,
                    "type": row[4],
                    "unread": not row[5] # DB stores is_read, frontend expects 'unread'
                })
                
            return results

    except Exception as e:
        print(f"Error fetching notifications: {e}")
        return []
    finally:
        db_sync.pg_pool.putconn(conn)

@app.post("/notifications/{notification_id}/read")
def read_notification(notification_id: str):
    if db_sync.pg_pool is None:
        raise HTTPException(status_code=500, detail="Database not available")
        
    conn = db_sync.pg_pool.getconn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE notifications 
                SET is_read = TRUE 
                WHERE id = %s
            """, (notification_id,))
            conn.commit()
        return {"status": "success"}
    except Exception as e:
        print(f"Error reading notification: {e}")
        raise HTTPException(status_code=500, detail="Failed to mark as read")
    finally:
        db_sync.pg_pool.putconn(conn)

@app.delete("/notifications/{notification_id}")
def delete_notification(notification_id: str):
    if db_sync.pg_pool is None:
        raise HTTPException(status_code=500, detail="Database not available")
        
    conn = db_sync.pg_pool.getconn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE notifications 
                SET is_deleted = TRUE 
                WHERE id = %s
            """, (notification_id,))
            conn.commit()
        return {"status": "success"}
    except Exception as e:
        print(f"Error deleting notification: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete")
    finally:
        db_sync.pg_pool.putconn(conn)

@app.post("/thinkaloud/upload")
async def upload_thinkaloud(
    file: UploadFile = File(...),
    session_id: str = Form(...),
    user_id: str = Form(...),
):
    upload_dir="think_aloud_recordings"
    os.makedirs(upload_dir, exist_ok=True)

    #create a safe filename
    filename = f"{user_id}_{session_id}_{file.filename}"
    filepath = os.path.join(upload_dir, filename)

    try:
        with open(filepath, 'wb') as buffer:
            shutil.copyfileobj(file.file, buffer)
        print(f"✓ Saved think-aloud audio: {filename}")
        return {"status": "success", "filename": filename}
    except Exception as e:
        print(f"⚠ Error saving audio: {e}")
        raise HTTPException(status_code=500, detail="Failed to save audio file")