import os
import json
from huggingface_hub import hf_hub_download
from llama_cpp import Llama

# 1. Model Configuration
REPO_ID = "unsloth/functiongemma-270m-it-GGUF"
FILENAME = "functiongemma-270m-it-Q8_0.gguf" # Capital Q is required!
LOCAL_DIR = "./models"
MODEL_PATH = os.path.join(LOCAL_DIR, FILENAME)

# 2. Auto-Download Logic
if not os.path.exists(MODEL_PATH):
    print(f"Model not found at {MODEL_PATH}. Downloading from Hugging Face...")
    os.makedirs(LOCAL_DIR, exist_ok=True)
    MODEL_PATH = hf_hub_download(
        repo_id=REPO_ID,
        filename=FILENAME,
        local_dir=LOCAL_DIR
    )
    print("Download complete!")

# 3. Initialize Model (Optimized for Pi 5)
print("Loading FunctionGemma-270M GGUF into Pi RAM...")
llm = Llama(
    model_path=MODEL_PATH,
    n_ctx=2048,   
    n_threads=4,  
    verbose=False 
)

# 4. Define Our Tools
tools = [
    {
        "name": "get_weather",
        "description": "Get the current weather for a city",
        "parameters": {
            "type": "object",
            "properties": {
                "city": {"type": "string", "description": "The city name, e.g. London"}
            },
            "required": ["city"]
        }
    },
    {
        "name": "turn_on_light",
        "description": "Turns on a smart light in a specific room",
        "parameters": {
            "type": "object",
            "properties": {
                "room": {"type": "string", "description": "The room name"}
            },
            "required": ["room"]
        }
    }
]

user_query = "what is the weather in atlanta"

# 5. Manually Construct the Gemma Prompt
# We strictly use <start_of_turn> tags and the 'developer' role to activate tool calling.
prompt = f"""<bos><start_of_turn>developer
You are a model that can do function calling with the following functions:
{json.dumps(tools)}<end_of_turn>
<start_of_turn>user
{user_query}<end_of_turn>
<start_of_turn>model
"""

print("\nFormatting prompt and generating tool call...")

# 6. Generate the Function Call
output = llm(
    prompt,
    max_tokens=128,
    temperature=0.1,       # Low temperature for strict API output
    stop=["<end_of_turn>"] # Tells the model to stop once the function call is printed
)

response = output["choices"][0]["text"].strip()

print("\n--- FunctionGemma Output ---")
print(response)