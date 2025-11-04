from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from chat_engine import GPTCoachEngine
from db_async import init_db_pool, close_db_pool
from db_sync import init_sync_pool, close_sync_pool
from uuid import uuid4
from starlette.concurrency import run_in_threadpool
from db_async import save_message
from contextlib import asynccontextmanager
from fastapi import BackgroundTasks
from db_sync import save_message_sync

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

@app.get("/")
async def root():
    return {"message": "Server is running!"} #def root

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
    user_id: Optional[str] = "default"
    session_id: Optional[str] = "default"

class ChatResponse(BaseModel):
    reply: str
    user_id: str
    session_id: str


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest, background_tasks: BackgroundTasks):
    """
    Chat endpoint with automatic database sync.
    Uses background tasks to sync without blocking the response.
    """
    user_id = req.user_id or str(uuid4())
    session_id = req.session_id or str(uuid4())

    # Get reply synchronously (this is the slow part)
    reply = engine.chat(req.message, user_id=user_id, session_id=session_id)

    # Schedule DB writes in background (runs after response is returned)
    # This doesn't block the user - they get response immediately
    background_tasks.add_task(save_message_sync, session_id, user_id, "user", req.message)
    background_tasks.add_task(save_message_sync, session_id, user_id, "assistant", reply)

    return ChatResponse(reply=reply, user_id=user_id, session_id=session_id)