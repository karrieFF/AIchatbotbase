import torch
import threading
import os
from dotenv import load_dotenv

load_dotenv() # Load environment variables from .env

from models import load_model, clean_response, build_prompt
from database import init_sync_pool, save_message_sync

class GPTCoachEngine:
    def __init__(self):
        # Check if cloud GPU URL is provided
        self.cloud_gpu_url = os.getenv("CLOUD_GPU_URL", "").strip().rstrip("/")
        
        if self.cloud_gpu_url:
            # Use cloud GPU model service
            self.use_cloud_gpu = True
            print(f"✓ Using cloud GPU model service: {self.cloud_gpu_url}")
            # No local tokenizer needed - cloud handles everything!
        else:
            # Use local model
            self.use_cloud_gpu = False
            self.tokenizer, self.model = load_model()
            self.model.eval()
            print("✓ Using local model")

        # Store separate conversation histories for each user and session
        # Structure: {user_id: {session_id: [messages]}}
        self.sessions = {}

        # Initialize database connection pool
        try:
            init_sync_pool()
            print("✓ Database connection pool initialized")
        except Exception as e:
            print(f"⚠ Warning: Database pool initialization failed: {e}")
            print("  Chat will work but messages won't be saved to database")

    # ----- session helpers -----
    def _init_session(self, user_id: str, session_id: str) -> None:
  
        messages = build_prompt("")
        # Clean up empty user messages if present
        if len(messages) >= 2 and messages[1].get("role") == "user" and messages[1].get("content", "") == "":
            messages = [messages[0]]

        # Initialize user's session storage if needed
        if user_id not in self.sessions:
            self.sessions[user_id] = {}
        self.sessions[user_id][session_id] = messages

    def _get_session_messages(self, user_id: str, session_id: str):
        """Get messages for a user's session, creating it if it doesn't exist."""
        if user_id not in self.sessions or session_id not in self.sessions[user_id]:
            self._init_session(user_id, session_id)
        return self.sessions[user_id][session_id]

    def _save_to_db(self, session_id: str, user_id: str, role: str, text: str):
        """
        Helper method to save message to database in background thread.
        This runs asynchronously and won't block the chat response.
        """
        try:
            save_message_sync(session_id, user_id, role, text)
        except Exception as e:
            # Log error but don't crash the application
            print(f"⚠ Database sync error ({role}): {e}")

    def chat(self, user_text: str, user_id: str = "default", session_id: str = "default") -> str:
        """One turn of chat: add user → generate → clean → add assistant → return text.
        
        Automatically syncs all messages to PostgreSQL database in background threads.
        """
        # Get or create user's session-specific message history
        messages = self._get_session_messages(user_id, session_id)
        
        # Add user message to session history
        messages.append({"role": "user", "content": user_text})
        
        if self.use_cloud_gpu:
            # Call cloud GPU model service with RAW messages (no local tokenization)
            try:
                import requests
                api_response = requests.post(
                    f"{self.cloud_gpu_url}/generate",
                    json={
                        "messages": messages,  # Send full conversation history
                        "max_tokens": 50,
                        "temperature": 0.7,
                        "top_p": 0.9
                    },
                    timeout=60
                )
                api_response.raise_for_status()
                result = api_response.json()
                response_text = result.get("response", "")
                response = clean_response(response_text)
            except requests.exceptions.RequestException as e:
                print(f"⚠ Error calling cloud GPU: {e}")
                if hasattr(e, 'response') and e.response is not None:
                    print(f"  Response: {e.response.text[:200]}")
                raise
            except Exception as e:
                print(f"⚠ Unexpected error calling cloud GPU: {e}")
                raise
        else:
            # Use local model (existing code)
            
            # Convert messages to chat template format
            chat_text = self.tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True,
            )

            inputs = self.tokenizer(chat_text, return_tensors="pt").to(self.model.device)

            # Generate outputs based on inputs (computer language)
            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    max_new_tokens=50, 
                    temperature=0.7, 
                    top_p=0.9, 
                    do_sample=True,
                    eos_token_id=self.tokenizer.eos_token_id,
                )

            # Decode only new tokens
            new_tokens = outputs[0][inputs["input_ids"].shape[1]:]
            response = self.tokenizer.decode(new_tokens, skip_special_tokens=True)
            response = clean_response(response)

        # Add assistant response to session history
        messages.append({"role": "assistant", "content": response})

        return response
