
import threading
import os
from dotenv import load_dotenv

load_dotenv() # Load environment variables from .env

from models import load_model, clean_response
from database import init_sync_pool, save_message_sync, db_sync
from models.prompt_template import build_prompt, build_prompt_follow

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
    
    #get the SMART goal data from the database
    def get_user_context (self, user_id: str):
        if not user_id or db_sync.pg_pool is None:
            return "No data available."
        
        context_parts = []
        conn = db_sync.pg_pool.getconn()
        try:
            with conn.cursor() as cur:
                # Fetch Activity (Fixed SQL commas)
                cur.execute("""
                    SELECT 
                        TO_CHAR(activity_date, 'YYYY-MM-DD'),
                        COALESCE(total_steps, 0),
                        COALESCE(very_active_minutes + fairly_active_minutes, 0),
                        COALESCE(calorie, 0),
                        COALESCE(sedentary_minutes, 0)
                    FROM activity_data 
                    WHERE user_id = %s 
                    AND activity_date >= CURRENT_DATE - INTERVAL '7 days'
                    ORDER BY activity_date ASC
                """, (user_id,))
                
                rows = cur.fetchall()
                if rows:
                    daily_str = "\n".join([f"- {r[0]}: {r[1]} Steps, {r[2]} MVPA, {r[3]} Cal, {r[4]} Sed" for r in rows])
                    context_parts.append(f"PAST 7 DAYS ACTIVITY:\n{daily_str}")
                else:
                    context_parts.append("PAST ACTIVITY: No recent data found.")
                
                # Fetch SMART Goal (Fixed SQL)
                cur.execute("""
                    SELECT 
                        specific, measurable, achievable, relevant, time_bound,
                        TO_CHAR(created_at, 'YYYY-MM-DD HH24:MI')
                    FROM extraction 
                    WHERE user_id = %s 
                    ORDER BY created_at DESC 
                    LIMIT 1
                """, (user_id,))
                
                goal = cur.fetchone()
                if goal:
                    context_parts.append(f"\nLAST GOAL ({goal[5]}):\nS: {goal[0]}\nM: {goal[1]}\nA: {goal[2]}\nR: {goal[3]}\nT: {goal[4]}")
                else:
                    context_parts.append("\nLAST GOAL: None.")
                    
        except Exception as e:
            print(f"⚠ Context Error: {e}")
            return "Error fetching data"
        finally:
            db_sync.pg_pool.putconn(conn)
        
        return "\n".join(context_parts)
        

    def check_if_returning_user (self, user_id:str, session_Id: str ):
        if not user_id or db_sync.pg_pool is None:
            return False
            
        conn = db_sync.pg_pool.getconn()
        try:
            with conn.cursor() as cur:
                # Check if this user has ANY messages in the system
                # (We don't filter by session_id!=current because current is empty anyway for new session)
                cur.execute("SELECT 1 FROM messages WHERE user_id = %s LIMIT 1", (user_id,))
                return cur.fetchone() is not None
        except Exception as e:
            print(f"⚠ Error checking returning user: {e}")
            return False
        finally:
            db_sync.pg_pool.putconn(conn)
        
    # ----- session helpers -----
    def _init_session(self, user_id: str, session_id: str) -> None:
        # ----for testing stage
        Testing_stage = True #set false in production
        use_prompt = 0

        if Testing_stage:
            if use_prompt == 1:
                user_context = self.get_user_context(user_id)

                try:
                    messages = build_prompt_follow(user_context)
                except TypeError:
                    messages = build_prompt_follow("")
                    if messages and messages[0]['role'] == 'system':
                        messages[0]['content'] += f"\n\nCONTEXT DATA:\n{user_context}"
                print("return user")
            elif use_prompt == 0:
                messages = build_prompt("")
                print("new user")
        else:
            #determine if it is the first conversation or the follow-up conversation
            is_new_agent_mode = not agent_mode 
            is_returning_user = self.check_if_returning_user(user_id, session_id) #self is to call the function inside the class

            if is_new_agent_mode and not is_returning_user:
                # Both agent_mode and user history are new: use first prompt
                messages = build_prompt("")
                print("new user (first prompt under )")
            else:
                user_context = self.get_user_context(user_id)
                try:
                    messages = build_prompt_follow(user_context)
                except TypeError:
                    messages = build_prompt_follow("")
                    if messages and messages[0]['role'] == 'system':
                        messages[0]['content'] += f"\n\nCONTEXT DATA:\n{user_context}"
                print("return user (follow-up prompt)")

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
                        "max_tokens": 500,
                        "temperature": 0.7,
                        "top_p": 0.9
                    },
                    timeout=300
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

            import torch
            # Generate outputs based on inputs (computer language)
            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    max_new_tokens=500, 
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
