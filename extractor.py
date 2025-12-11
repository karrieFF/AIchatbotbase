#extract the smart goal from client or agent
import os 
import json
import requests

from dotenv import load_dotenv #loads the environment variables from the .env file
from models import load_model, clean_response
#open the database and get the messages
from database import init_sync_pool, save_message_sync, db_sync

load_dotenv() #load the environment variables from the .env file

def get_messages_from_db(session_id: str):
    """
    Get all messages for a given session in the format expected by the extractor.
    Returns (user_id, messages_list).
    """
    if db_sync.pg_pool is None:
        init_sync_pool()

    conn = db_sync.pg_pool.getconn()

    try:  # make sure the connection is closed even if there is an error
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT user_id, role, text FROM messages
                WHERE session_id = %s
                ORDER BY created_at ASC
                """,
                (session_id,),
            )
            rows = cur.fetchall()
            if not rows:
                return None, []

            userid = {row[0] for row in rows}
            userid = userid.pop()
            print(f"DEBUG - User ID: {userid}")
            conversation_data = [
                {"role": row[1], "content": row[2]} for row in rows
            ]  # map this format for another LLM input
            return userid, conversation_data
    finally:
        db_sync.pg_pool.putconn(conn)

#extract the smart goals from the messages
def extract_smart_goals(messages:list):
    #USE the LLM to extract the smart goals from the messages

    #print(f"DEBUG - Conversation text: {conversation_text}")

    #define the extraction prompt
    system_prompt = """
    You are a health coach analyzer. Your task is to extract the SMART goals and time for next session from the messages. 
    The messages are the messages between the client and the coach. 
    You only need to extract the key words instead of the whole sentence. 

    The SMART goals refers to the following:
    - Specific: Identify the exact type of physical activity you plan to do;
    - Measurable: Quantify the goal using the FIT criteria—Frequency (how often you exercise), Intensity (how hard you work), and Time (how long each session lasts)
    - Achievable: Ensure the goal is realistic and attainable by considering client's confidence level in completing the activity;
    - Relevant: Connect the activity to meaningful health outcomes. For example, increasing physical activity may help improve mental health;
    - Time_bound: Set a clear timeframe for completing the goal, such as committing to this plan for the upcoming week before the next session;

    The time for the next session is always following the agent asking the client to schedule a follow-up session;
    Output the SMART goals and schedule time in the following format in JSON format:
    {"specific": such as "walking",
    "measurable": such as "3 times a week; 10 minutes per time", 
    "achievable": such as  "6/10 on the confidence scale with reminders",
    "relevant": such as "improve mental health",
    "time_bound": such as "start from now till next session",
    "schedule_time": such as "2025-12-16"
    }

    """

    messages_payload = [
        {"role":"system", "content": system_prompt},
        {"role":"user", "content":f"Analyze the following messages and extract the SMART goals: \n\n{messages}"}
    ]

    #print(f"DEBUG - Messages payload: {messages_payload}")
    #call the LLM model to extract 
    #call the cloud GPU model service
    cloud_gpu_url = os.getenv("CLOUD_GPU_URL", "").strip().rstrip("/")
    

    try:
        response_text = ""

        if cloud_gpu_url:
            print(f"DEBUG - Cloud GPU URL: {cloud_gpu_url}")
            #-------------cloud GPU path-------------
            response = requests.post(
                f"{cloud_gpu_url}/generate",
                json={
                    "messages": messages_payload,
                    "max_tokens": 500,
                    "temperature": 0.7,
                    "top_p": 0.9
                },
                timeout=60
            )
            response.raise_for_status()
            response_text = response.json().get("response", "")

        else:
            #print("DEBUG - Using Local Model")
            tokenizer, model = load_model() #local model path

            chat_text = tokenizer.apply_chat_template(
                messages_payload,
                tokenize=False,
                add_generation_prompt=True,
            )
            import torch
            inputs = tokenizer(chat_text, return_tensors="pt").to(model.device) #transfer the text to tokenizer format
            
            with torch.no_grad():
                outputs = model.generate(
                        **inputs,
                        max_new_tokens=500,
                        temperature=0,
                        top_p=1,
                        do_sample=False, #set to True to use temparature/top_p
                        eos_token_id=tokenizer.eos_token_id
                )
            new_tokens = outputs[0][inputs["input_ids"].shape[1]:]
            response_text = tokenizer.decode(new_tokens, skip_special_tokens=True)

            #print(f"DEBUG - Raw response: {response_text}")
        #clean and parse response
        cleaned = clean_response(response_text)
        #print(f"DEBUG - Cleaned response:{cleaned}")

        #strip code blocks if the model adds them
        if "```json" in cleaned:
            cleaned = cleaned.split("```json")[1].split("```")[0].strip()
        elif "```" in cleaned:
            cleaned = cleaned.split("```")[1].strip()

        return json.loads(cleaned)

    except requests.exceptions.RequestException as e:
        print(f"⚠ Error calling cloud GPU: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"  Response: {e.response.text[:200]}")
        raise
    except Exception as e:
        print(f"⚠ Unexpected error calling cloud GPU: {e}")
        raise

def store_smart_goals(smartgoals: dict):
    """
    Store SMART goals into the `extraction` table.
    """
    if db_sync.pg_pool is None:
        init_sync_pool()

    conn = db_sync.pg_pool.getconn()
    # only update other data is the session_id is the same
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO extraction (user_id, session_id, specific, measurable, achievable, relevant, time_bound, schedule_time
                ) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (session_id) DO UPDATE SET
                user_id       = EXCLUDED.user_id,
                specific      = EXCLUDED.specific,
                measurable    = EXCLUDED.measurable,
                achievable    = EXCLUDED.achievable,
                relevant      = EXCLUDED.relevant,
                time_bound    = EXCLUDED.time_bound,
                schedule_time = EXCLUDED.schedule_time,
                created_at    = NOW();
                """,
                (
                    smartgoals["user_id"],
                    smartgoals["session_id"],
                    smartgoals["specific"],
                    smartgoals["measurable"],
                    smartgoals["achievable"],
                    smartgoals["relevant"],
                    smartgoals["time_bound"],
                    smartgoals["schedule_time"],
                ),
            )
            conn.commit()
            print(f"✓ Stored SMART goals for user {smartgoals['user_id']}")
    except Exception as e:
        conn.rollback()
        print(f"⚠ ERROR storing SMART goals: {e}")
    finally:
        db_sync.pg_pool.putconn(conn)

#convert the main to the function
def extract_and_store_for_session(session_id: str) -> None:
    """
    End-to-end helper:
    - Load messages for a session
    - Run SMART goal extraction
    - Normalize output
    - Store in the `extraction` table
    """
    # Ensure DB pool
    if db_sync.pg_pool is None:
        init_sync_pool()

    user_id, messages = get_messages_from_db(session_id)

    if not messages:
        print(f"No messages found for session {session_id}. Skipping extraction.")
        return

    print(f"Found {len(messages)} messages for session {session_id}. Running extraction...")

    smartgoals = extract_smart_goals(messages)

    # Convert a list of dicts into a single dictionary if needed
    if isinstance(smartgoals, list):
        merged = {}
        for item in smartgoals:
            if isinstance(item, dict):
                merged.update(item)
        smartgoals = merged

    # Attach identifiers
    smartgoals["user_id"] = user_id
    smartgoals["session_id"] = session_id
    print(f"DEBUG - Smartgoals for session {session_id}: {smartgoals}")

    # Store in DB
    store_smart_goals(smartgoals)


if __name__ == "__main__":
    # Example manual run for a hard-coded session (for debugging)
    demo_session_id = "29c2b0eb-d660-4e91-a566-fd8b90f550d6"
    extract_and_store_for_session(demo_session_id)
