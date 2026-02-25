import os
from pathlib import Path

from huggingface_hub import hf_hub_download
from llama_cpp import Llama

# 1. Model configuration
REPO_ID = "nlouis/functiongemma-pocket-q4_k_m"
FILENAME = "functiongemma-pocket-q4_k_m.gguf"
LOCAL_DIR = "./models"
MODEL_PATH = os.path.join(LOCAL_DIR, FILENAME)

# 2. Auto-download if not already in models/
if not os.path.exists(MODEL_PATH):
    print(f"Model not found at {MODEL_PATH}. Downloading from Hugging Face...")
    os.makedirs(LOCAL_DIR, exist_ok=True)
    MODEL_PATH = hf_hub_download(
        repo_id=REPO_ID,
        filename=FILENAME,
        local_dir=LOCAL_DIR,
    )
    print("Download complete!")

# 3. Performance settings (aligned with test_gemma.py)
PERF = {
    "n_ctx": 2048,
    "n_threads": 4,
    "n_threads_batch": 4,
    "n_batch": 512,
    "n_gpu_layers": -1,
    "use_mmap": True,
    "use_mlock": False,
    "verbose": False,
}

# 4. Load model
print(f"Loading FunctionGemma model: {MODEL_PATH}...")
llm = Llama(
    model_path=MODEL_PATH,
    n_ctx=PERF["n_ctx"],
    n_threads=PERF["n_threads"],
    n_threads_batch=PERF["n_threads_batch"],
    n_batch=PERF["n_batch"],
    n_gpu_layers=PERF["n_gpu_layers"],
    use_mmap=PERF["use_mmap"],
    use_mlock=PERF["use_mlock"],
    verbose=PERF["verbose"],
)
