"""
Test script to check if cloud GPU service is accessible
Run this from your LOCAL machine (not cloud GPU)
"""
import requests
import sys

# Replace with your RunPod HTTP Service URL
# You can find this in RunPod dashboard -> HTTP Services -> click the link
CLOUD_GPU_URL = input("Enter your RunPod HTTP Service URL (e.g., https://xxxxx-8000.proxy.runpod.net): ").strip()

if not CLOUD_GPU_URL:
    print("❌ No URL provided")
    sys.exit(1)

# Remove trailing slash
CLOUD_GPU_URL = CLOUD_GPU_URL.rstrip('/')

print(f"\n🔍 Testing connection to: {CLOUD_GPU_URL}\n")

# Test 1: Health endpoint
print("1. Testing /health endpoint...")
try:
    response = requests.get(f"{CLOUD_GPU_URL}/health", timeout=10)
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        print(f"   ✅ Health check passed!")
        print(f"   Response: {response.json()}")
    else:
        print(f"   ❌ Health check failed: {response.text}")
except requests.exceptions.ConnectionError:
    print("   ❌ Connection refused - Service not running or not accessible")
except requests.exceptions.Timeout:
    print("   ❌ Timeout - Service not responding")
except Exception as e:
    print(f"   ❌ Error: {e}")

# Test 2: Generate endpoint
print("\n2. Testing /generate endpoint...")
try:
    test_prompt = "<|im_start|>user\nHello!<|im_end|>\n<|im_start|>assistant\n"
    response = requests.post(
        f"{CLOUD_GPU_URL}/generate",
        json={
            "prompt": test_prompt,
            "max_tokens": 20,
            "temperature": 0.4,
            "top_p": 0.7
        },
        timeout=60
    )
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"   ✅ Generate test passed!")
        print(f"   Response: {result.get('response', 'No response')}")
    else:
        print(f"   ❌ Generate failed: {response.text}")
except requests.exceptions.ConnectionError:
    print("   ❌ Connection refused - Service not running or not accessible")
except requests.exceptions.Timeout:
    print("   ❌ Timeout - Service not responding (model might still be loading)")
except Exception as e:
    print(f"   ❌ Error: {e}")

print("\n" + "="*50)
print("If all tests pass, your service is working!")
print("If tests fail, check the troubleshooting steps below.")
