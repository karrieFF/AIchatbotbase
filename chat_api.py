from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from chat_engine import GPTCoachEngine

app = FastAPI()

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
def chat(req: ChatRequest):
    user_id = req.user_id or "default"
    session_id = req.session_id or "default"
    reply = engine.chat(req.message, user_id=user_id, session_id=session_id)
    return ChatResponse(reply=reply, user_id=user_id, session_id=session_id)