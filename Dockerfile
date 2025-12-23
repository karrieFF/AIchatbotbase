FROM nvidia/cuda:12.1.1-cudnn8-runtime-ubuntu22.04

# System deps
RUN apt-get update && apt-get install -y \
    python3 python3-pip git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps
COPY requirements_model.txt .
RUN pip3 install --no-cache-dir -r requirements_model.txt

# Copy code
COPY . .

# RunPod serverless entrypoint
CMD ["python3", "handler.py"]
