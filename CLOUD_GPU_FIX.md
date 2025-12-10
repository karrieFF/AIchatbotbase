# Cloud GPU Setup - Fixed Version

## The Problem

The `autoawq` library is deprecated and incompatible with newer `transformers` versions, causing import errors.

## The Solution

Use **non-AWQ models** instead. They work perfectly fine and don't require the problematic `autoawq` library.

## Updated Installation (On Cloud GPU)

```bash
# Install dependencies (NO autoawq needed!)
pip install fastapi uvicorn transformers torch accelerate

# Run the service
python cloud_gpu_model_service.py
```

## Model Options

The service now uses regular models (not AWQ):

- `Qwen/Qwen2.5-14B-Instruct` - 14B model (regular, ~28GB)
- `Qwen/Qwen2.5-7B-Instruct` - 7B model (smaller, ~14GB)
- `Qwen/Qwen2.5-32B-Instruct` - 32B model (large, needs A100 80GB)

## Memory Requirements

| Model | Size | GPU Needed |
|-------|------|------------|
| 7B | ~14GB | RTX 3090 (24GB) ✅ |
| 14B | ~28GB | A100 40GB ✅ |
| 32B | ~56GB | A100 80GB ✅ |

## If You Get Out of Memory

If 14B doesn't fit, use 7B:
```python
Model_NAME = "Qwen/Qwen2.5-7B-Instruct"
```

The 7B model is still much better than your local 1.5B model!

## Quick Setup Commands

```bash
# On cloud GPU terminal
cd /workspace/AIchatbotbase

# Install (no autoawq!)
pip install fastapi uvicorn transformers torch accelerate

# Run
python cloud_gpu_model_service.py
```

That's it! No more autoawq compatibility issues.

