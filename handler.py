import runpod
import torch
import os
from transformers import AutoModelForCausalLM, AutoTokenizer

# --- CONFIGURATION ---
DEFAULT_MODEL = "Qwen/Qwen2.5-14B-Instruct"
MODEL_NAME = os.getenv("MODEL_NAME", DEFAULT_MODEL)

# Global variables to cache model in memory (Warm Start)
tokenizer = None
model = None

def load_model():
    global tokenizer, model
    print(f"\n[{MODEL_NAME}] Loading model...")
    
    try:
        tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, trust_remote_code=True)
        
        # Load model with FP16 for GPU optimization
        model = AutoModelForCausalLM.from_pretrained(
            MODEL_NAME,
            torch_dtype=torch.float16,
            device_map="auto",
            low_cpu_mem_usage=True,
            trust_remote_code=True
        )
        model.eval()
        print(f"[{MODEL_NAME}] ✓ Model loaded successfully!")
        
    except Exception as e:
        print(f"[{MODEL_NAME}] ❌ FAILED to load model: {e}")
        raise e

# Initialize model immediately when container starts
if model is None:
    load_model()

def handler(job):
    """
    RunPod handler function.
    'job' contains 'input' with the JSON payload sent to the API.
    """
    job_input = job["input"]
    
    # 1. Parse Input
    prompt = job_input.get("prompt")
    messages = job_input.get("messages")
    max_tokens = job_input.get("max_tokens", 500)
    temperature = job_input.get("temperature", 0.7)
    top_p = job_input.get("top_p", 0.9)

    if not prompt and not messages:
        return {"error": "Missing 'prompt' or 'messages' in input"}

    try:
        # 2. Prepare Input Text
        if messages:
            text_input = tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True
            )
        else:
            text_input = prompt

        # 3. Tokenize
        inputs = tokenizer(text_input, return_tensors="pt").to(model.device)

        # 4. Generate
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
                do_sample=True,
                pad_token_id=tokenizer.eos_token_id,
            )

        # 5. Decode Response
        # Only decode the new tokens
        new_tokens = outputs[0][inputs["input_ids"].shape[1]:]
        response = tokenizer.decode(new_tokens, skip_special_tokens=True)

        return {"response": response}

    except Exception as e:
        return {"error": str(e)}

# Start the serverless worker
runpod.serverless.start({"handler": handler})