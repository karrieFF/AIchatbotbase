# app.py
import gradio as gr
from chat_engine import GPTCoachEngine

engine = GPTCoachEngine()  # load once

def chat_gradio(user_text, history):
    # history is a list of [user, assistant]
    # we only need user_text – we’ll let engine manage its own message history
    reply = engine.chat(user_text)
    history = history + [[user_text, reply]]
    return history, history

with gr.Blocks() as demo:
    gr.Markdown("## 🧠 GPTCoach – Physical Activity Coach")
    chatbot = gr.Chatbot(
        value=[["assistant", engine.greeting]],
        height=500,
    )
    msg = gr.Textbox(placeholder="Tell me about your PA goals...")
    clear = gr.Button("Clear")

    msg.submit(chat_gradio, [msg, chatbot], [chatbot, chatbot])
    clear.click(lambda: [[], []], None, [chatbot, msg])

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860, share=True)
