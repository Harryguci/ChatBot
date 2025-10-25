import torch

# 1. Check if CUDA is available
cuda_available = torch.cuda.is_available()
print(f"Is CUDA available? {cuda_available}")

if cuda_available:
    # 2. Get the number of GPUs
    print(f"Number of GPUs: {torch.cuda.device_count()}")
    
    # 3. Get the name of the current GPU
    current_device = torch.cuda.current_device()
    print(f"Current GPU index: {current_device}")
    print(f"Current GPU name: {torch.cuda.get_device_name(current_device)}")
else:
    print("CUDA is not available. Check your installation.")