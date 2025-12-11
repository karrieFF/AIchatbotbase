#model loader, transformer load automatically
#this if for local models only

from transformers import AutoModelForCausalLM, AutoTokenizer
import torch

Model_NAME = "Qwen/Qwen2.5-0.5B-Instruct" #Qwen2.5-0.5B 

def load_model():
    print(f"Loading local model: {Model_NAME}...")
    try:
        tokenizer = AutoTokenizer.from_pretrained(Model_NAME, trust_remote_code=True)
        model = AutoModelForCausalLM.from_pretrained(
            Model_NAME,
            torch_dtype=torch.float16, # Use float16 for GPU
            device_map="auto",       
            trust_remote_code=True
        )
        print("✓ Local model loaded on GPU")
        return tokenizer, model

    except Exception as e:
        print(f"Error loading model: {e}")
        print("Trying CPU fallback...")
        tokenizer = AutoTokenizer.from_pretrained(Model_NAME, trust_remote_code=True)
        model = AutoModelForCausalLM.from_pretrained(
            Model_NAME,
            torch_dtype=torch.float32,
            device_map="cpu",
            trust_remote_code=True
        )
        return tokenizer, model