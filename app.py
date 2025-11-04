# app.py
import gradio as gr
from uuid import uuid4
from chat_engine import GPTCoachEngine
from database import init_sync_pool, close_sync_pool

# Initialize database pool
init_sync_pool()

engine = GPTCoachEngine()

# Store user/session IDs (simple approach - in production use session state)
user_id = str(uuid4())
session_id = str(uuid4())

# Initialize conversation history
conversation_history = [{"role": "assistant", "content": engine.greeting}]

def chat_gradio(user_text, history):
    """
    Chat function that syncs to database automatically.
    """
    global user_id, session_id, conversation_history

    # Ensure history is a list (handle None case)
    if history is None:
        history = []
    
    # Get reply from engine (this automatically saves to DB)
    reply = engine.chat(user_text, user_id=user_id, session_id=session_id)
    
    # Update history with messages format (list of dicts with 'role' and 'content')
    history.append({"role": "user", "content": user_text})
    history.append({"role": "assistant", "content": reply})

    # Update global history
    conversation_history = history
    
    # Return updated history and empty string to clear input
    return history, ""
def clear_chat():
    """Clear chat and reset conversation."""
    global conversation_history
    conversation_history = [{"role": "assistant", "content": engine.greeting}]
    return [], ""

with gr.Blocks() as demo:
    gr.Markdown("## 🧠 Physical Activity Coach")
    chatbot = gr.Chatbot(
        value=conversation_history,  # Messages format
        height=500,
        type="messages" # Add this line to fix the warning
    )
    msg = gr.Textbox(
        placeholder="Let's start the journey to promote physical activity and improve physical and mental health!",
        label = "Your Message"
        )
    clear = gr.Button("Clear")

    msg.submit(chat_gradio, [msg, chatbot], [chatbot, msg])
    clear.click(clear_chat, None, [chatbot, msg])

if __name__ == "__main__":
    try:
        demo.launch(share=True)
    finally:
        # Cleanup on exit
        close_sync_pool()