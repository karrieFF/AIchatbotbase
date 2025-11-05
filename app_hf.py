# app_hf.py - HuggingFace Spaces version (no database)
# This version works on HuggingFace Spaces which doesn't provide PostgreSQL
# Conversations are stored in memory only (lost on restart)

import gradio as gr
from uuid import uuid4
import torch
from models import load_model, clean_response, build_prompt

# Create a simplified engine without database dependencies
class HuggingFaceEngine:
    """Simplified engine for HuggingFace Spaces (no database)."""
    
    def __init__(self):
        print("Loading model for HuggingFace Spaces...")
        self.tokenizer, self.model = load_model()
        self.model.eval()
        self.greeting = self._make_greeting()
        self.sessions = {}
        print("Model loaded successfully!")
    
    def _make_greeting(self):
        """Generate greeting message."""
        greeting_prompt = (
            "You are a friendly health coach using motivational interviewing coach. "
            "Introduce yourself briefly (<=30 words) and invite the user to talk about themselves."
        )
        greet_messages = [{"role": "system", "content": greeting_prompt}]
        
        chat_text = self.tokenizer.apply_chat_template(
            greet_messages, tokenize=False, add_generation_prompt=True
        )
        
        inputs = self.tokenizer(chat_text, return_tensors="pt").to(self.model.device)
        
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=60,
                temperature=0.3,
                top_p=0.7,
                do_sample=True,
                eos_token_id=self.tokenizer.eos_token_id,
            )
        
        new_tokens = outputs[0][inputs["input_ids"].shape[1]:]
        text = self.tokenizer.decode(new_tokens, skip_special_tokens=True)
        return clean_response(text)
    
    def _init_session(self, user_id: str, session_id: str):
        """Initialize a new session."""
        messages = build_prompt("")
        if len(messages) >= 2 and messages[1].get("role") == "user" and messages[1].get("content", "") == "":
            messages = [messages[0]]
        messages.append({"role": "assistant", "content": self.greeting})
        
        if user_id not in self.sessions:
            self.sessions[user_id] = {}
        self.sessions[user_id][session_id] = messages
    
    def _get_session_messages(self, user_id: str, session_id: str):
        """Get messages for a session."""
        if user_id not in self.sessions or session_id not in self.sessions[user_id]:
            self._init_session(user_id, session_id)
        return self.sessions[user_id][session_id]
    
    def chat(self, user_text: str, user_id: str = "default", session_id: str = "default") -> str:
        """One turn of chat without database sync."""
        messages = self._get_session_messages(user_id, session_id)
        messages.append({"role": "user", "content": user_text})
        
        chat_text = self.tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        
        inputs = self.tokenizer(chat_text, return_tensors="pt").to(self.model.device)
        
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=80,
                temperature=0.4,
                top_p=0.7,
                do_sample=True,
                eos_token_id=self.tokenizer.eos_token_id,
            )
        
        new_tokens = outputs[0][inputs["input_ids"].shape[1]:]
        response = self.tokenizer.decode(new_tokens, skip_special_tokens=True)
        response = clean_response(response)
        
        messages.append({"role": "assistant", "content": response})
        return response

# Initialize engine
engine = HuggingFaceEngine()

# Store user sessions in memory (per user, per HuggingFace session)
# This uses Gradio's request object to identify unique users
user_sessions = {}

def get_user_session(request: gr.Request):
    """Get or create session for each user based on their session hash."""
    if request is None:
        # Fallback if request not available
        user_id = str(uuid4())
        session_id = str(uuid4())
    else:
        # Use Gradio's session hash to identify unique users
        user_id = request.session_hash
        session_id = f"{user_id}_session"
    
    if user_id not in user_sessions:
        user_sessions[user_id] = {
            'user_id': user_id,
            'session_id': session_id,
            'history': [{"role": "assistant", "content": engine.greeting}]
        }
    
    return user_sessions[user_id]

def chat_gradio(user_text, history, request: gr.Request):
    """
    Chat function for HuggingFace Spaces.
    No database - conversations stored in memory only.
    """
    session = get_user_session(request)
    
    # Use session history if provided, otherwise use stored history
    if history is None or len(history) == 0:
        history = session['history'].copy()
    
    # Get reply from engine (doesn't save to DB on HuggingFace)
    try:
        reply = engine.chat(
            user_text, 
            user_id=session['user_id'], 
            session_id=session['session_id']
        )
    except Exception as e:
        # Fallback if engine has issues
        reply = "I'm having trouble processing that right now. Could you try rephrasing?"
        print(f"Engine error: {e}")
    
    # Update history
    history.append({"role": "user", "content": user_text})
    history.append({"role": "assistant", "content": reply})
    
    # Save to session storage
    session['history'] = history
    
    return history, ""

def clear_chat(request: gr.Request):
    """Clear chat and reset conversation for this user."""
    session = get_user_session(request)
    session['history'] = [{"role": "assistant", "content": engine.greeting}]
    return [], ""

# Create Gradio interface
with gr.Blocks(title="Physical Activity Coach", theme=gr.themes.Soft()) as demo:
    gr.Markdown("## 🧠 Physical Activity Coach")
    gr.Markdown("Welcome! I'm here to help you explore and increase your motivation for physical activity using motivational interviewing.")
    
    chatbot = gr.Chatbot(
        value=[{"role": "assistant", "content": engine.greeting}],
        height=500,
        type="messages",
        label="Conversation"
    )
    
    msg = gr.Textbox(
        placeholder="Let's start the journey to promote physical activity and improve physical and mental health!",
        label="Your Message",
        lines=2
    )
    
    with gr.Row():
        clear = gr.Button("Clear Chat", variant="secondary")
        submit = gr.Button("Send", variant="primary")
    
    # Event handlers
    msg.submit(chat_gradio, [msg, chatbot], [chatbot, msg])
    submit.click(chat_gradio, [msg, chatbot], [chatbot, msg])
    clear.click(clear_chat, None, [chatbot, msg])
    
    # Footer note
    gr.Markdown("---")
    gr.Markdown("*Note: Conversations are stored in memory only and will be lost when the app restarts.*")

if __name__ == "__main__":
    # HuggingFace Spaces will automatically set the port
    demo.launch()

