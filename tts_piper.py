import os
import re
import subprocess
import shlex
import urllib.request
from piper.voice import PiperVoice

os.environ['ORT_LOGGING_LEVEL'] = '3'

class PocketAudio:
    def __init__(self, model_name="en_US-lessac-medium"):
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.model_dir = os.path.join(self.base_dir, "models")
        self.model_path = os.path.join(self.model_dir, f"{model_name}.onnx")
        self.config_path = os.path.join(self.model_dir, f"{model_name}.onnx.json")
        
        self._ensure_models_exist(model_name)
        print("Loading Piper into memory... (Standby)")
        self.voice = PiperVoice.load(self.model_path, config_path=self.config_path)
        print("System Ready. Outputting to USB Audio Device (hw:3,0).")

    def _ensure_models_exist(self, name):
        if not os.path.exists(self.model_dir): os.makedirs(self.model_dir)
        url_base = "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/"
        for ext in [".onnx", ".onnx.json"]:
            path = self.model_path if ext == ".onnx" else self.config_path
            if not os.path.exists(path):
                print(f"Downloading {name}{ext}...")
                urllib.request.urlretrieve(url_base + name + ext, path)

    def clean_text(self, text):
        """Remove emojis and special symbols, keeping alphanumeric, spaces and basic punctuation."""
        # This regex keeps alphanumeric, common punctuation, and whitespace
        return re.sub(r'[^a-zA-Z0-9\s.,!?;:\'\"()-]', '', text)

    def speak(self, text):
        import threading
        cleaned_text = self.clean_text(text)
        if not cleaned_text.strip():
            return
        thread = threading.Thread(target=self._speak_internal, args=(cleaned_text,), daemon=True)
        thread.start()

    def _speak_internal(self, text):
        # Target Card 3, Device 0 using plughw for compatibility
        command = "aplay -D plughw:3,0 -r 22050 -f S16_LE -t raw -"
        args = shlex.split(command)
        
        print(f"Synthesizing: {text[:50]}...")
        try:
            with subprocess.Popen(args, stdin=subprocess.PIPE) as play_process:
                for chunk in self.voice.synthesize(text):
                    play_process.stdin.write(chunk.audio_int16_bytes)
            print("Playback finished.")
        except Exception as e:
            print(f"Audio Error: {e}")

if __name__ == "__main__":
    ai = PocketAudio()
    
    msg = "I have saved this audio to a file as you requested."
    ai.speak(msg)