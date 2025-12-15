"""
Cloud GPU Model Service
Deploy this on your cloud GPU (e.g., RunPod, Lambda, AWS) to serve the model via API.
Your local app (Render/Laptop) will call this service.

Usage on cloud GPU:
  1. pip install fastapi uvicorn transformers torch accelerate
  2. python cloud_gpu_model_service.py
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import torch
import os

# --- CONFIGURATION ---
# Default model (can be overridden by environment variable MODEL_NAME)
DEFAULT_MODEL = "Qwen/Qwen2.5-7B-Instruct"  # Good balance of speed/quality
# DEFAULT_MODEL = "meta-llama/Meta-Llama-3-8B-Instruct" # Alternative

MODEL_NAME = os.getenv("MODEL_NAME", DEFAULT_MODEL)

app = FastAPI()

# Allow CORS so your local app can call it
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variables for model/tokenizer
tokenizer = None
model = None

def load_model():
    """Load model into global variables."""
    global tokenizer, model
    
    print(f"\n[{MODEL_NAME}] Loading model... (This may take a few minutes)")
    
    try:
        from transformers import AutoModelForCausalLM, AutoTokenizer
        
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
        if torch.cuda.is_available():
            print(f"[{MODEL_NAME}] ✓ GPU Active: {torch.cuda.get_device_name(0)}")
            print(f"[{MODEL_NAME}] ✓ VRAM: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.2f} GB")
    except Exception as e:
        print(f"[{MODEL_NAME}] ❌ FAILED to load model: {e}")
        raise e

# --- API MODELS ---
class ChatRequest(BaseModel):
    prompt: Optional[str] = None
    messages: Optional[List[dict]] = None
    max_tokens: int = 500
    temperature: float = 0.7
    top_p: float = 0.9

# --- ENDPOINTS ---

@app.on_event("startup")
async def startup_event():
    """Load the model when the server starts."""
    load_model()

@app.get("/")
def root():
    """Root endpoint - for health checks."""
    return {
        "status": "service_running",
        "model": MODEL_NAME,
        "gpu_available": torch.cuda.is_available(),
        "endpoints": ["/health", "/generate"]
    }

@app.get("/health")
def health():
    """Health check endpoint."""
    if model is None:
        raise HTTPException(status_code=503, detail="Model not loaded yet")
    return {
        "status": "ok",
        "model": MODEL_NAME,
        "gpu": torch.cuda.get_device_name(0) if torch.cuda.is_available() else "cpu"
    }

@app.post("/generate")
def generate(request: ChatRequest):
    """Generate text from prompt or messages."""
    if model is None or tokenizer is None:
        raise HTTPException(status_code=503, detail="Model is not loaded")

    try:
        # 1. Prepare Input
        if request.messages:
            # Use chat template (Standard for Instruct models)
            text_input = tokenizer.apply_chat_template(
                request.messages,
                tokenize=False,
                add_generation_prompt=True
            )
        elif request.prompt:
            # Raw prompt fallback
            text_input = request.prompt
        else:
            raise HTTPException(status_code=400, detail="Either 'messages' or 'prompt' is required")

        # 2. Tokenize
        inputs = tokenizer(text_input, return_tensors="pt").to(model.device)

        # 3. Generate
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=request.max_tokens,
                temperature=request.temperature,
                top_p=request.top_p,
                do_sample=True,
                pad_token_id=tokenizer.eos_token_id,
            )

        # 4. Decode
        # Only decode the *new* tokens (response), not the input history
        new_tokens = outputs[0][inputs["input_ids"].shape[1]:]
        response = tokenizer.decode(new_tokens, skip_special_tokens=True)

        return {"response": response}

    except Exception as e:
        print(f"Generation Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    # Allow port to be set by environment (useful for some cloud providers)
    port = int(os.getenv("PORT", 8000))
    
    print(f"\n--- Starting Cloud Model Service on Port {port} ---\n")
    uvicorn.run(app, host="0.0.0.0", port=port)