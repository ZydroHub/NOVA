import os
from huggingface_hub import hf_hub_download
from llama_cpp import Llama

# 1. Model Configuration
REPO_ID = "Qwen/Qwen3-0.6B-GGUF"
FILENAME = "Qwen3-0.6B-Q8_0.gguf"
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

# 3. Initialize Model 
print("Loading Qwen3-0.6B into Pi RAM...")
llm = Llama(
    model_path=MODEL_PATH,
    n_ctx=4096,   
    n_threads=4,  
    verbose=False 
)

# 4. Initialize Chat History
messages = [
    {"role": "system", "content": ""}
]

thinking_mode = True 

print("\n--- Qwen3-0.6B Chat Ready ---")
print("Type 'exit' to quit.")
print("Type '/think' to enable thinking mode.")
print("Type '/no_think' to disable thinking mode.")
print("-----------------------------\n")

# 5. Interactive Chat Loop
while True:
    user_input = input("You: ")
    
    if user_input.lower() in ['exit', 'quit']:
        print("Goodbye!")
        break
        
    if user_input.strip() == "/think":
        thinking_mode = True
        print("[System: Thinking mode ENABLED]")
        continue
    elif user_input.strip() == "/no_think":
        thinking_mode = False
        print("[System: Thinking mode DISABLED]")
        continue
        
    # Append the mode flag so the model knows how to behave
    mode_flag = " /think" if thinking_mode else " /no_think"
    prompt_with_toggle = user_input + mode_flag
    
    messages.append({"role": "user", "content": prompt_with_toggle})
    
    print("AI:\n", end="", flush=True)
    
    # 6. Dynamic Sampling Parameters
    # Applying the strict documentation parameters based on the current mode
    if thinking_mode:
        current_temp = 0.6
        current_top_p = 0.95
    else:
        current_temp = 0.7
        current_top_p = 0.8
        
    # Generate the response with the exact parameters applied
    response = llm.create_chat_completion(
        messages=messages,
        max_tokens=2048,
        temperature=current_temp,
        top_p=current_top_p,
        top_k=20,          # Consistent across both modes
        min_p=0.0,         # Consistent across both modes
        presence_penalty=1.5, # Helps prevent the endless repetition loops
        stream=True
    )
    
    # Process the streaming chunks
    full_reply = ""
    for chunk in response:
        delta = chunk['choices'][0]['delta']
        if 'content' in delta:
            text = delta['content']
            print(text, end="", flush=True)
            full_reply += text
            
    messages.append({"role": "assistant", "content": full_reply})
    print("\n")