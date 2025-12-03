"""
Cloud GPU Model Service
Deploy this on your cloud GPU to serve the model via API.
Your local app will call this service.

Usage on cloud GPU:
  1. pip install fastapi uvicorn transformers torch accelerate
  2. python cloud_gpu_model_service.py
  3. Or: uvicorn cloud_gpu_model_service:app --host 0.0.0.0 --port 8000
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch

app = FastAPI()

# Allow CORS so your local app can call it
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Model configuration - change this to your desired model
# Note: Using non-AWQ models to avoid compatibility issues
Model_NAME = "Qwen/Qwen2.5-14B-Instruct"  # For 14B model (regular, not AWQ)
# Model_NAME = "Qwen/Qwen2.5-7B-Instruct"  # For 7B model (smaller, faster)
# Model_NAME = "Qwen/Qwen2.5-32B-Instruct"  # For 32B model (needs A100 80GB, no AWQ)

# Load model once at startup
print(f"Loading model: {Model_NAME}...")
print("This may take 5-10 minutes on first run (model download)...")

tokenizer = AutoTokenizer.from_pretrained(Model_NAME)
model = AutoModelForCausalLM.from_pretrained(
    Model_NAME,
    torch_dtype=torch.float16,  # Use float16 for GPU (saves memory)
    device_map="auto",  # Automatically uses GPU
    low_cpu_mem_usage=True  # Optimize memory usage
)
model.eval()

print("✓ Model loaded and ready!")
print(f"GPU: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'None'}")

from typing import List, Optional

class ChatRequest(BaseModel):
    prompt: Optional[str] = None
    messages: Optional[List[dict]] = None
    max_tokens: int = 80
    temperature: float = 0.6
    top_p: float = 0.7

@app.get("/")
def root():
    """Root endpoint - for health checks"""
    return {
        "status": "service_running",
        "model": Model_NAME,
        "endpoints": {
            "health": "/health",
            "generate": "/generate"
        }
    }

@app.post("/generate")
def generate(request: ChatRequest):
    """Generate text from prompt or messages"""
    
    # Handle messages list (auto-formatting)
    if request.messages:
        text_input = tokenizer.apply_chat_template(
            request.messages,
            tokenize=False,
            add_generation_prompt=True
        )
    # Handle raw prompt (fallback)
    elif request.prompt:
        text_input = request.prompt
    else:
        return {"error": "Either 'messages' or 'prompt' is required"}

    inputs = tokenizer(text_input, return_tensors="pt").to(model.device)
    
    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=request.max_tokens,
            temperature=request.temperature,
            top_p=request.top_p,
            do_sample=True,
            eos_token_id=tokenizer.eos_token_id,
        )
    
    # Decode only new tokens (remove the prompt)
    new_tokens = outputs[0][inputs["input_ids"].shape[1]:]
    response = tokenizer.decode(new_tokens, skip_special_tokens=True)
    
    return {"response": response}

@app.get("/health")
def health():
    """Health check endpoint"""
    return {
        "status": "ok",
        "gpu_available": torch.cuda.is_available(),
        "gpu_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
        "model": Model_NAME
    }

if __name__ == "__main__":
    import uvicorn
    import os
    
    # Use PORT from environment if available (required for Serverless), otherwise default to 8000
    port = int(os.getenv("PORT", 8000))
    
    print(f"\n{'='*50}")
    print(f"🚀 Model Service Starting on Port {port}")
    print(f"{'='*50}")
    print("1. Go to RunPod Dashboard -> Connect -> HTTP Service (Port 8000)")
    print("2. Copy that URL (e.g. https://...-8000.proxy.runpod.net)")
    print("3. Paste it into your local .env file as CLOUD_GPU_URL")
    print(f"{'='*50}\n")
    
    uvicorn.run(app, host="0.0.0.0", port=port)

