#model loader, transformer load automatically
#this if for local models only

Model_NAME = "Qwen/Qwen2.5-1.5B-Instruct-AWQ" #Qwen2.5-0.5B 

def load_model():
    from transformers import AutoTokenizer
    from awq import AutoAWQForCausalLM

    print(f"Loading AWQ model: {Model_NAME}...")

    tokenizer = AutoTokenizer.from_pretrained(Model_NAME, trust_remote_code=True)

    try:
        # AWQ: load quantized
        model = AutoAWQForCausalLM.from_quantized(
            Model_NAME,
            device_map="auto",
            trust_remote_code=True,
            fuse_layers=True
        )
        print("✓ AWQ model loaded (device_map=auto)")
        return tokenizer, model

    except Exception as e:
        print(f"Error loading on GPU/auto: {e}")
        print("Trying CPU fallback...")

        # CPU fallback (slow)
        model = AutoAWQForCausalLM.from_quantized(
            Model_NAME,
            device_map="cpu",
            trust_remote_code=True,
            fuse_layers=False
        )
        return tokenizer, model