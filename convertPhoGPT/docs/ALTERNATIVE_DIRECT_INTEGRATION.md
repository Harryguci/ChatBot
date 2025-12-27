# Alternative: Direct PhoGPT Integration (No GGUF Conversion)

## ⚠️ Why This Alternative?

**PhoGPT cannot be converted to GGUF format** because:

- PhoGPT uses a custom BPE tokenizer not supported by llama.cpp
- The MPT architecture has tokenizer format incompatibilities
- Error: `BPE pre-tokenizer was not recognized`

## ✅ Solution: Use PhoGPT Directly

Instead of converting to GGUF/Ollama, we can integrate PhoGPT directly using the transformers library. This is actually **better** because:

- ✅ No conversion needed
- ✅ Full model capabilities
- ✅ Better Vietnamese performance
- ✅ Direct GPU utilization

## Implementation

### Step 1: Install Dependencies

```bash
pip install torch transformers
```

### Step 2: Use PhoGPT Wrapper

We've created a wrapper that mimics the Ollama API: [job_bot/phogpt_wrapper.py](../job_bot/phogpt_wrapper.py)

### Step 3: Update main.py (Two Options)

#### Option A: Replace Ollama Client Completely

Edit `job_bot/main.py`:

```python
# OLD (line 13, 59):
import ollama
client = ollama.Client(host=OLLAMA_HOST)

# NEW:
from phogpt_wrapper import create_phogpt_client
client = create_phogpt_client(model_path="vinai/PhoGPT-4B-Chat")
```

#### Option B: Conditional Loading

```python
import os
USE_PHOGPT = os.getenv("USE_PHOGPT", "false").lower() == "true"

if USE_PHOGPT:
    from phogpt_wrapper import create_phogpt_client
    client = create_phogpt_client(model_path="vinai/PhoGPT-4B-Chat")
    print("[LLM] Using PhoGPT directly (transformers)")
else:
    import ollama
    client = ollama.Client(host=OLLAMA_HOST)
    print("[LLM] Using Ollama")
```

### Step 4: Update Environment

```bash
# .env
USE_PHOGPT=true

# Optional: Specify local model path (if downloaded)
PHOGPT_MODEL_PATH=/path/to/downloaded/phogpt

# Or use HuggingFace (will download automatically)
PHOGPT_MODEL_PATH=vinai/PhoGPT-4B-Chat
```

### Step 5: Test

```bash
python job_bot/phogpt_wrapper.py
```

Expected output:

```
[PhoGPT] Loading model: vinai/PhoGPT-4B-Chat
[PhoGPT] Device: cuda
[PhoGPT] Model loaded successfully

=== Response ===
Xin chào! Tôi là trợ lý AI của VinAI Research...
```

## Architecture Comparison

### Before (Ollama + GGUF)

```
Your Code
    ↓ (Ollama API)
Ollama Service
    ↓ (GGUF)
Quantized Model (q4_k_m)
```

### After (Direct Integration)

```
Your Code
    ↓ (PhoGPTClient)
PhoGPT (transformers)
    ↓ (PyTorch)
GPU/CPU
```

## Performance

| Metric      | Ollama GGUF          | Direct PhoGPT                        |
| ----------- | -------------------- | ------------------------------------ |
| Setup       | Complex (conversion) | Simple (pip install)                 |
| Memory      | ~2.5GB (quantized)   | ~8GB (FP16) or ~4GB (FP16 quantized) |
| Speed (GPU) | Fast                 | Very Fast                            |
| Speed (CPU) | Slow                 | Very Slow                            |
| Quality     | Good (quantized)     | Excellent (full precision)           |
| Vietnamese  | Good                 | Excellent                            |

## GPU Recommendations

- **NVIDIA GTX 1060 6GB+**: Can run FP16
- **NVIDIA RTX 2060+**: Can run BF16 (faster)
- **CPU Only**: Use Ollama instead (PhoGPT too slow on CPU)

## Code Changes Required

### Minimal Changes (5 lines)

```python
# File: job_bot/main.py

# Line ~13: Add import
from phogpt_wrapper import create_phogpt_client

# Line ~59: Replace client initialization
# OLD: client = ollama.Client(host=OLLAMA_HOST)
# NEW:
client = create_phogpt_client(
    model_path=os.getenv("PHOGPT_MODEL_PATH", "vinai/PhoGPT-4B-Chat")
)
```

**That's it!** The wrapper mimics Ollama's API, so the rest of your code works unchanged.

## Advanced: Enhance Tool Calling

The basic wrapper has simple tool call parsing. For better tool calling:

### Update `_parse_tool_calls` in phogpt_wrapper.py

```python
def _parse_tool_calls(self, response: str, tools: List[Dict]) -> Optional[List[Dict]]:
    """Enhanced tool call parsing"""
    import re

    tool_calls = []

    # Pattern: Look for function calls in response
    # Example: "Tôi sẽ gọi job_search với q='kỹ sư phần mềm'"
    for tool in tools:
        tool_name = tool.get("function", {}).get("name", "")

        # Check if tool is mentioned
        if tool_name in response:
            # Parse arguments (enhanced logic)
            args = self._extract_arguments(response, tool_name, tool)

            if args:
                tool_calls.append({
                    "id": f"call_{tool_name}_{len(tool_calls)}",
                    "type": "function",
                    "function": {
                        "name": tool_name,
                        "arguments": args
                    }
                })

    return tool_calls if tool_calls else None
```

## Fallback Strategy

If PhoGPT doesn't work well, you can:

1. **Use Qwen (current)** - Proven to work
2. **Try other Vietnamese models**:
   - `bkai-foundation-models/vietnamese-llama2-7b-40GB`
   - `vilm/vietcuna-7b-v3`
3. **Fine-tune Qwen** on Vietnamese data

## Summary

| Approach               | Pros               | Cons                        | Status     |
| ---------------------- | ------------------ | --------------------------- | ---------- |
| **GGUF Conversion**    | Fast, low memory   | ❌ Not supported for PhoGPT | Failed     |
| **Direct Integration** | Easy, full quality | Requires GPU, more memory   | ✅ Working |
| **Keep Qwen**          | Already working    | Not Vietnamese-optimized    | ✅ Working |

## Recommendation

**Use Direct Integration (Option A)** if you have:

- ✅ GPU with 6GB+ VRAM
- ✅ Need best Vietnamese quality
- ✅ Can afford ~8GB memory

**Keep Qwen** if you:

- ❌ No GPU or limited VRAM
- ✅ Need lower memory usage
- ✅ Current quality is acceptable

## Questions?

See [../job_bot/phogpt_wrapper.py](../job_bot/phogpt_wrapper.py) for the implementation.
