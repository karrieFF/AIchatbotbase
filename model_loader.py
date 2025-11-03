#model loader, transformer load automatically

from transformers import AutoModelForCausalLM, AutoTokenizer
import torch

Model_NAME = "Qwen/Qwen2.5-3B-Instruct" #"Qwen/Qwen2.5-3B-Instruct" #"Qwen/Qwen2.5-0.5B-Instruct"  # change if needed 

def load_model ():
    tokenizer = AutoTokenizer.from_pretrained(Model_NAME)
    model = AutoModelForCausalLM.from_pretrained (
        Model_NAME,
        torch_dtype=torch.float32,
        device_map="auto"      # auto, when there is GPU, will use GPU, if not, will use CPU, will put it on CPU if no GPU #device_map='cpu'#NVIDIA GPUs with CUDA support work, hugging face model, can only use cpu
    )
    return tokenizer, model