import requests
import json
import sys

# Configuration
MODEL = "qwen3:0.6b"
API_URL = "http://localhost:11434/api/chat"

class ChatBot:
    def __init__(self, model=MODEL, api_url=API_URL, thinking=True):
        self.model = model
        self.api_url = api_url
        self.thinking = thinking
        self.history = []

    def preload_model(self):
        """Sends a minimal request to wake up the model."""
        try:
            print(f"Preloading model {self.model}...")
            # Use 'generate' endpoint for a quick empty check or just a simple chat
            # Actually, sending an empty message might trigger a response.
            # Let's just send a "hello" and ignore response, or just check connectivity.
            # Faster: just check tags or show model info? No, we want to load it into RAM.
            # We'll send a very short prompt.
            payload = {
                "model": self.model,
                "messages": [{"role": "user", "content": "hi"}],
                "stream": False
            }
            requests.post(self.api_url, json=payload, timeout=30)
            print("Model preloaded.")
            return True
        except Exception as e:
            print(f"Failed to preload model: {e}")
            return False

    def generate_response(self, user_input, stream_callback=None):
        """
        Generates a response for the given input.
        If stream_callback is provided, it calls stream_callback(chunk) for each token.
        Returns the full response string.
        """
        self.history.append({"role": "user", "content": user_input})
        
        options = {}
        if not self.thinking:
            # Try to disable thinking via options
            options["thinking"] = False 
            # Some models/versions might use num_think or just rely on system prompt
            # But we will also filter the output manually.
        
        payload = {
            "model": self.model,
            "messages": self.history,
            "stream": True,
            "options": options
        }

        full_response = ""
        try:
            with requests.post(self.api_url, json=payload, stream=True) as response:
                response.raise_for_status()
                for line in response.iter_lines():
                    if line:
                        try:
                            json_response = json.loads(line)
                            if "message" in json_response:
                                content = json_response["message"].get("content", "")
                                if content:
                                    full_response += content
                                    if stream_callback:
                                        stream_callback(content)
                            
                            if json_response.get("done", False):
                                # If thinking is disabled, strip out <think> tags from history
                                final_content = full_response
                                if not self.thinking:
                                    import re
                                    final_content = re.sub(r'<think>.*?</think>', '', full_response, flags=re.DOTALL).strip()
                                
                                self.history.append({"role": "assistant", "content": final_content})
                                # If we filtered, should we update full_response to return the filtered version?
                                # Yes, usually the caller wants the final visible text.
                                # However, stream_callback has already shown the reasoning... 
                                # Use a buffer strategy for streaming if we really want to hide it?
                                # For now, let's return filtered content.
                                full_response = final_content

                        except json.JSONDecodeError:
                            continue
        except requests.exceptions.RequestException as e:
            error_msg = f"Error: {e}"
            if stream_callback:
                stream_callback(error_msg)
            return error_msg

        return full_response

def chat():
    """
    Main chat loop for CLI testing.
    """
    bot = ChatBot()
    print(f"Starting chat with {bot.model}...")
    print("Type 'exit' or 'quit' to end the session.")

    while True:
        try:
            user_input = input("\nYou: ").strip()
            if not user_input:
                continue

            if user_input.lower() in ["exit", "quit"]:
                print("Goodbye!")
                break

            print("Bot: ", end="", flush=True)
            bot.generate_response(user_input, stream_callback=lambda x: print(x, end="", flush=True))
            print()

        except KeyboardInterrupt:
            print("\nExiting...")
            break

if __name__ == "__main__":
    chat()
