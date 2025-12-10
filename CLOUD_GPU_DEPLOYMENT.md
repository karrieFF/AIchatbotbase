# Cloud GPU Deployment Guide

## Overview

Your code now supports both local models and cloud GPU models. You can switch between them easily using environment variables.

## Architecture

- **Local Machine**: Runs your full app (FastAPI, database, React frontend)
- **Cloud GPU**: Runs only the model service (one small file)
- **Connection**: Local app calls cloud GPU API when `CLOUD_GPU_URL` is set

## Step-by-Step Setup

### Part 1: Deploy Model Service on Cloud GPU

#### 1. SSH into your cloud GPU
```bash
ssh root@<your-cloud-gpu-ip> -p <port>
```

#### 2. Upload only the model service file
**Option A: Copy-paste the file**
```bash
# On cloud GPU, create the file
nano cloud_gpu_model_service.py
# Copy-paste the content from cloud_gpu_model_service.py
```

**Option B: Use SCP (from your local machine)**
```powershell
# From Windows PowerShell
scp C:\Code\AIchatbotbase\cloud_gpu_model_service.py root@<cloud-gpu-ip>:/workspace/
```

#### 3. Install dependencies on cloud GPU
```bash
pip install fastapi uvicorn transformers torch autoawq
```

#### 4. (Optional) Update model in the service
Edit `cloud_gpu_model_service.py` on cloud GPU:
```python
# Change line 25 to your desired model:
Model_NAME = "Qwen/Qwen2.5-14B-Instruct-AWQ"  # For 14B
# OR
Model_NAME = "Qwen/Qwen2.5-32B-Instruct-AWQ"  # For 32B (needs A100 80GB)
```

#### 5. Run the model service
```bash
python cloud_gpu_model_service.py
# OR
uvicorn cloud_gpu_model_service:app --host 0.0.0.0 --port 8000
```

You should see:
```
Loading model: Qwen/Qwen2.5-14B-Instruct-AWQ...
✓ Model loaded and ready!
Starting model service on http://0.0.0.0:8000
```

#### 6. Get the public URL
- **RunPod**: Go to pod → "HTTP Service" → copy public URL
- **Vast.ai**: Check your instance's public IP/URL
- Example: `https://xxxxx-8000.proxy.runpod.net`

### Part 2: Configure Your Local App

#### 1. Install requests (if not already installed)
```bash
pip install requests
```

#### 2. Set environment variable
**Windows PowerShell:**
```powershell
$env:CLOUD_GPU_URL="https://your-cloud-gpu-url"
```

**Windows CMD:**
```cmd
set CLOUD_GPU_URL=https://your-cloud-gpu-url
```

**Or create `.env` file:**
```env
CLOUD_GPU_URL=https://your-cloud-gpu-url
```

#### 3. Run your local app
```bash
python chat_api.py
```

You should see:
```
✓ Using cloud GPU model service: https://your-cloud-gpu-url
✓ Database connection pool initialized
```

## Usage Modes

### Mode 1: Local Model (Default)
```bash
# Don't set CLOUD_GPU_URL, or set it to empty
python chat_api.py
# Output: ✓ Using local model
```

### Mode 2: Cloud GPU Model
```bash
# Set CLOUD_GPU_URL
$env:CLOUD_GPU_URL="https://your-cloud-gpu-url"
python chat_api.py
# Output: ✓ Using cloud GPU model service: https://your-cloud-gpu-url
```

## Testing

### Test Cloud GPU Service Directly
```bash
# On cloud GPU or from your local machine
curl -X POST https://your-cloud-gpu-url/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Hello, how are you?", "max_tokens": 50}'
```

### Test Health Endpoint
```bash
curl https://your-cloud-gpu-url/health
```

### Test Your Local App
Your React frontend will work the same way - just make sure your local API is running and pointing to the cloud GPU.

## Troubleshooting

### Error: "requests not installed"
```bash
pip install requests
```

### Error: "Connection refused" or timeout
- Check if cloud GPU service is running
- Verify the URL is correct
- Check firewall/security groups
- Make sure service is bound to `0.0.0.0` not `127.0.0.1`

### Error: "Model not found" on cloud GPU
- Check if model name is correct
- Verify you have enough VRAM for the model
- Try a smaller model first (7B instead of 14B)

### Model download slow on first run
- First download takes 10-30 minutes (normal)
- Subsequent runs use cached model (much faster)

## Cost Optimization

1. **Stop cloud GPU when not testing** - Only pay for active time
2. **Use smaller models for testing** - 7B is cheaper than 14B
3. **Cache models** - Models are cached after first download
4. **Monitor usage** - Check your cloud GPU dashboard

## Files Modified

- ✅ `chat_engine.py` - Added cloud GPU support
- ✅ `requirements.txt` - Added `requests`
- ✅ `cloud_gpu_model_service.py` - New file for cloud GPU

## Next Steps

1. Deploy model service on cloud GPU
2. Get the public URL
3. Set `CLOUD_GPU_URL` environment variable
4. Run your local app
5. Test with your React frontend

Your app will automatically use the cloud GPU model when the URL is set!

