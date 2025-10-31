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
    session_id: Optional[str] = "default"

class ChatResponse(BaseModel):
    reply: str
    session_id: str

@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    reply = engine.chat(req.message, session_id=req.session_id or "default")
    return ChatResponse(reply=reply, session_id=req.session_id or "default")