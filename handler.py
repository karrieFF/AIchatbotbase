def handler(event):
    prompt = event["input"].get("prompt", "")
    return {
        "output": f"Received prompt: {prompt}"
    }