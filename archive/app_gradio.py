# app.py
import gradio as gr
from uuid import uuid4
from chat_engine import GPTCoachEngine
from database import init_sync_pool, close_sync_pool

# Initialize database pool
init_sync_pool()

engine = GPTCoachEngine()

# --- Helpers for unique IDs and State ---
def get_uuid():
    """Generate a unique ID."""
    return str(uuid4())

def get_initial_history():
    """Return the initial greeting message."""
    return [{
        "role": "assistant", 
        "content": "Hello! I'm here to support you in your journey towards better health, just as you would want me to help someone else. What brings you here today?"
    }]

def chat_gradio(user_text, history, user_id, session_id):
    """
    Chat function that syncs to database automatically.
    """
    # Ensure history is a list
    if history is None:
        history = []
    
    # Don't send empty messages
    if not user_text.strip():
        return history, ""

    # Update history
    history.append({"role": "user", "content": user_text})
    yield history, ""  # Yields history with user msg, clears input box


     # Get reply from engine (this automatically saves to DB)
    # The engine uses session_id to retrieve context from DB.
    reply = engine.chat(user_text, user_id=user_id, session_id=session_id)
    history.append({"role": "assistant", "content": reply})
    yield history, ""

def clear_chat():
    """Clear chat and generate a NEW session ID to reset context."""
    new_session_id = get_uuid()
    return get_initial_history(), "", new_session_id

with gr.Blocks() as demo:
    # State: These create unique IDs for EACH browser tab/user
    user_id_state = gr.State(get_uuid)
    session_id_state = gr.State(get_uuid)

    gr.Markdown("""
    # 🧠 Physical Activity Coach
    Welcome! I'm here to help you explore and increase your motivation for physical activity using motivational interviewing.
    """)
    
    chatbot = gr.Chatbot(
        value=get_initial_history, # Initialize with greeting
        height=500,
        label="Conversation"
    )
    msg = gr.Textbox(
        placeholder="Let's start the journey to promote physical activity and improve physical and mental health!",
        label = "Your Message"
    )
    
    with gr.Row():
        clear = gr.Button("Clear Chat")
        submit_btn = gr.Button("Send", variant="primary")

    # Define arguments for chat function
    chat_args = {
        "fn": chat_gradio,
        "inputs": [msg, chatbot, user_id_state, session_id_state],
        "outputs": [chatbot, msg]
    }

    msg.submit(**chat_args)
    submit_btn.click(**chat_args)
    
    # Clear chat resets UI AND generates a new session_id
    clear.click(clear_chat, None, [chatbot, msg, session_id_state])

if __name__ == "__main__":
    try:
        # demo.launch(
        # theme=gr.themes.Soft(),
        # share=True) #, debug=True
        demo.launch(theme=gr.themes.Soft(), 
        share=True)
    finally:
        # Cleanup on exit
        close_sync_pool()
