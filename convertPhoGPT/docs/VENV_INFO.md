# Virtual Environment in Conversion Scripts

## Overview

The conversion scripts (`convert_phogpt.sh` and `convert_phogpt.bat`) now **automatically create and use a dedicated virtual environment** for the conversion process.

## Why Virtual Environment?

### Benefits

✅ **Isolated Dependencies**
- Conversion packages are installed separately from your main project
- No conflicts with your existing Python environment
- No need to activate venv manually

✅ **No Global Pollution**
- Doesn't install packages globally
- Won't affect other Python projects
- Clean and reversible

✅ **No Admin Rights**
- No permission errors on Windows
- Safe to run in user space

✅ **Reproducible**
- Same environment every time
- Easier troubleshooting

## How It Works

### Windows (convert_phogpt.bat)

```
Step 2: Setting up virtual environment...
-----------------------------------
Creating new virtual environment at .\phogpt_conversion\venv_conversion
OK: Virtual environment created
Activating virtual environment...
OK: Virtual environment activated
  Python: E:\QC_tech\...\venv_conversion

Step 3: Installing Python dependencies in venv...
-----------------------------------
Installing huggingface_hub...
Installing torch, transformers, sentencepiece, protobuf...
OK: Dependencies installed in virtual environment
```

### Linux/Mac (convert_phogpt.sh)

```
Step 2: Setting up virtual environment...
-----------------------------------
Creating new virtual environment at ./phogpt_conversion/venv_conversion
✓ Virtual environment created
Activating virtual environment...
✓ Virtual environment activated
  Python: /path/to/phogpt_conversion/venv_conversion

Step 3: Installing Python dependencies in venv...
-----------------------------------
Installing huggingface_hub...
Installing torch, transformers, sentencepiece, protobuf...
✓ Dependencies installed in virtual environment
```

## File Structure

```
convertPhoGPT/
├── convert_phogpt.bat/sh      ← Conversion script
└── phogpt_conversion/          ← Created during conversion
    ├── venv_conversion/        ← Virtual environment (NEW)
    │   ├── Scripts/            ← (Windows) Python, pip, activate
    │   ├── bin/                ← (Linux/Mac) Python, pip, activate
    │   └── Lib/                ← Installed packages
    ├── llama.cpp/              ← Cloned repository
    └── models/
        ├── phogpt-4b-chat-hf/  ← Downloaded model
        ├── phogpt-4b-chat.gguf
        └── phogpt-4b-chat-q4_k_m.gguf
```

## What Gets Installed in the Venv

The script installs these packages in the isolated venv:

1. **huggingface_hub[cli]** - For downloading models
2. **torch** - PyTorch (for model conversion)
3. **transformers** - Hugging Face transformers
4. **sentencepiece** - Tokenization library
5. **protobuf** - Protocol buffers
6. **llama.cpp requirements** - Dependencies from llama.cpp/requirements.txt

## Automatic Cleanup

The virtual environment is **automatically deactivated** at the end of the script:

```
Deactivating virtual environment...
```

Your terminal returns to its previous state.

## Can I Delete the Venv?

**Yes!** After successfully creating the Ollama model, you can delete the virtual environment:

```bash
# Windows
rmdir /S convertPhoGPT\phogpt_conversion\venv_conversion

# Linux/Mac
rm -rf convertPhoGPT/phogpt_conversion/venv_conversion
```

The GGUF model files are separate and won't be affected.

## Running the Script Multiple Times

If you run the script again:

1. **First run**: Creates venv, installs all packages (~5-10 min)
2. **Subsequent runs**: Reuses existing venv (much faster!)

The script checks if venv exists:
```
OK: Virtual environment already exists
Activating virtual environment...
```

## Manual Virtual Environment (Advanced)

If you prefer manual control:

### Option 1: Use Existing Venv

```bash
# Activate your own venv first
source /path/to/your/venv/bin/activate  # Linux/Mac
# or
your\venv\Scripts\activate.bat          # Windows

# Then run conversion (it will use your active venv)
bash convert_phogpt.sh
```

### Option 2: Skip Venv (Not Recommended)

Modify the script to remove venv creation/activation steps. **Not recommended** as it installs globally.

## Troubleshooting

### "Failed to create virtual environment"

**Cause**: Python venv module not installed

**Solution**:
```bash
# Ubuntu/Debian
sudo apt install python3-venv

# Or reinstall Python with venv support
```

### "Failed to activate virtual environment"

**Cause**: Permission issues or corrupted venv

**Solution**:
```bash
# Delete and recreate
rm -rf convertPhoGPT/phogpt_conversion/venv_conversion
# Run script again
```

### Venv takes too much space

**Size**: ~1-2GB (mostly PyTorch)

**Solution**: Delete after conversion is complete. The GGUF files don't need it.

## Comparison: Before vs After

### Before (Old Script)
```batch
REM Check for huggingface-cli
huggingface-cli --version >nul 2>&1
if errorlevel 1 (
    echo Warning: huggingface-cli not found. Installing...
    pip install huggingface_hub[cli]  ← INSTALLS GLOBALLY
)
pip install torch transformers sentencepiece protobuf  ← GLOBAL
```

❌ Installs to global Python or active venv (unpredictable)
❌ May conflict with existing packages
❌ May need admin rights

### After (New Script)
```batch
REM Create virtual environment
python -m venv "%VENV_DIR%"

REM Activate it
call "%VENV_DIR%\Scripts\activate.bat"

REM Install in isolated venv
pip install huggingface_hub[cli]  ← ISOLATED
pip install torch transformers sentencepiece protobuf  ← ISOLATED
```

✅ Always creates isolated environment
✅ No conflicts possible
✅ No admin rights needed
✅ Reproducible and clean

## FAQ

**Q: Do I need to activate the venv manually?**
A: No! The script does it automatically.

**Q: Will this affect my main project's venv?**
A: No, it's completely isolated.

**Q: Can I use my own venv?**
A: Yes, activate it before running the script.

**Q: How much disk space does venv use?**
A: ~1-2GB (temporary, can delete after conversion).

**Q: Is the venv needed after conversion?**
A: No, you can delete it. The GGUF files are independent.

**Q: Does this work on all platforms?**
A: Yes, Windows, Linux, and macOS are all supported.

## Summary

The improved scripts now provide:
- ✅ Automatic venv creation
- ✅ Automatic activation/deactivation
- ✅ Isolated dependencies
- ✅ No global pollution
- ✅ Reproducible environment
- ✅ Works on all platforms

Just run the script and it handles everything!
