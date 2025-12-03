"""
Simplified Cloud GPU Model Service - Starts immediately for testing
This version loads the model in the background so the HTTP service is available right away
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import threading
import time

app = FastAPI()

# Allow CORS so your local app can call it
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global state
model_loaded = False
model_loading = False
tokenizer = None
model = None
Model_NAME = "Qwen/Qwen2.5-14B-Instruct"  # Change this to your model

def load_model_background():
    """Load model in background thread"""
    global model_loaded, model_loading, tokenizer, model
    
    if model_loading or model_loaded:
        return
    
    model_loading = True
    print(f"Loading model: {Model_NAME}...")
    print("This may take 5-10 minutes on first run (model download)...")
    
    try:
        from transformers import AutoModelForCausalLM, AutoTokenizer
        import torch
        
        tokenizer = AutoTokenizer.from_pretrained(Model_NAME)
        model = AutoModelForCausalLM.from_pretrained(
            Model_NAME,
            torch_dtype=torch.float16,
            device_map="auto",
            low_cpu_mem_usage=True
        )
        model.eval()
        
        model_loaded = True
        model_loading = False
        print("✓ Model loaded and ready!")
        print(f"GPU: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'None'}")
    except Exception as e:
        print(f"❌ Error loading model: {e}")
        model_loading = False
        raise

# Start loading model in background
print("Starting HTTP service...")
print("Model will load in background - service is available immediately")
threading.Thread(target=load_model_background, daemon=True).start()

class ChatRequest(BaseModel):
    prompt: str
    max_tokens: int = 80
    temperature: float = 0.4
    top_p: float = 0.7

@app.get("/")
def root():
    """Root endpoint - always available"""
    return {
        "status": "service_running",
        "model_loaded": model_loaded,
        "model_loading": model_loading,
        "model": Model_NAME
    }

@app.get("/health")
def health():
    """Health check endpoint"""
    import torch
    return {
        "status": "ok",
        "gpu_available": torch.cuda.is_available(),
        "gpu_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
        "model": Model_NAME,
        "model_loaded": model_loaded,
        "model_loading": model_loading
    }

@app.post("/generate")
def generate(request: ChatRequest):
    """Generate text from prompt"""
    if not model_loaded:
        if model_loading:
            raise HTTPException(status_code=503, detail="Model is still loading. Please wait and try again.")
        else:
            raise HTTPException(status_code=503, detail="Model failed to load. Check server logs.")
    
    import torch
    inputs = tokenizer(request.prompt, return_tensors="pt").to(model.device)
    
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

if __name__ == "__main__":
    import uvicorn
    print("\n" + "="*50)
    print("Starting model service on http://0.0.0.0:8000")
    print("Service is available immediately (model loads in background)")
    print("Check /health endpoint to see model loading status")
    print("="*50 + "\n")
    uvicorn.run(app, host="0.0.0.0", port=8000)
