
from chatbot import ChatBot
import time

def test_thinking_disabled():
    print("Initializing ChatBot with thinking=False...")
    bot = ChatBot(thinking=False)
    
    # We use a prompt that is likely to trigger reasoning in reasoning models
    prompt = "How many rs in strawberry?" 
    
    print(f"Sending prompt: {prompt}")
    response = bot.generate_response(prompt)
    
    print("\n--- Response ---")
    print(response)
    print("----------------")
    
    if "<think>" in response:
        print("FAIL: <think> tags found in response.")
    else:
        print("PASS: No <think> tags found.")

if __name__ == "__main__":
    test_thinking_disabled()
