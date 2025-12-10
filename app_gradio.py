import gradio as gr
import requests
import os

API_URL = os.getenv("API_URL", "http://127.0.0.1:8000/")  # your backend endpoint

def chat_fn(message, session_id):
    try:
        resp = requests.post(API_URL, json={"message": message, "session_id": session_id})
        resp.raise_for_status()
        data = resp.json()
        return data.get("reply", ""), session_id or data.get("session_id", "")
    except Exception as e:
        return f"Error: {e}", session_id

with gr.Blocks() as demo:
    gr.Markdown("# Chatbot Coach")
    sid = gr.Textbox(label="Session ID (optional)", value="")
    msg = gr.Textbox(label="Message", placeholder="Say hi...")
    out = gr.Textbox(label="Reply")
    sid_out = gr.Textbox(label="Session ID (returned)")

    btn = gr.Button("Send")
    btn.click(chat_fn, inputs=[msg, sid], outputs=[out, sid_out])

demo.launch()