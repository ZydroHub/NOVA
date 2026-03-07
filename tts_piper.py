import os
import re
import subprocess
import shlex
import threading
import queue
import time
import urllib.request
from piper.voice import PiperVoice

os.environ['ORT_LOGGING_LEVEL'] = '3'

# ALSA device for playback (e.g. plughw:3,0 for USB). Use "default" for system default.
TTS_ALSA_DEVICE = os.environ.get("TTS_ALSA_DEVICE", "default")

# Sentence-ending punctuation (split on these, keep delimiter with sentence)
SENTENCE_END_RE = re.compile(r'(?<=[.!?\n])\s*')


def split_sentences(text):
    """Split text into sentences on . ! ? and newlines. Strips each; drops empty."""
    if not text or not text.strip():
        return []
    parts = SENTENCE_END_RE.split(text.strip())
    return [p.strip() for p in parts if p.strip()]


class PocketAudio:
    def __init__(self, model_name="en_US-lessac-medium"):
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.model_dir = os.path.join(self.base_dir, "models")
        self.model_path = os.path.join(self.model_dir, f"{model_name}.onnx")
        self.config_path = os.path.join(self.model_dir, f"{model_name}.onnx.json")
        
        self._ensure_models_exist(model_name)
        print("Loading Piper into memory... (Standby)")
        self.voice = PiperVoice.load(self.model_path, config_path=self.config_path)
        print(f"System Ready. Outputting to ALSA device: {TTS_ALSA_DEVICE}")

        # Sentence-by-sentence playback queue
        self._queue = queue.Queue()
        self._queue_drained_callback = None
        self._worker = threading.Thread(target=self._queue_worker, daemon=True)
        self._worker.start()

    def _ensure_models_exist(self, name):
        if not os.path.exists(self.model_dir): os.makedirs(self.model_dir)
        # Size is last segment of name (e.g. en_US-lessac-medium -> medium; low/medium/high)
        size = name.split("-")[-1]
        url_base = f"https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/{size}/"
        for ext in [".onnx", ".onnx.json"]:
            path = self.model_path if ext == ".onnx" else self.config_path
            if not os.path.exists(path):
                print(f"Downloading {name}{ext}...")
                urllib.request.urlretrieve(url_base + name + ext, path)

    def set_queue_drained_callback(self, callback):
        """Optional sync callback (called from worker thread) when queue becomes empty after playback."""
        self._queue_drained_callback = callback

    def clear_queue(self):
        """Remove all pending sentences from the queue. Current sentence keeps playing to completion."""
        try:
            while True:
                self._queue.get_nowait()
        except queue.Empty:
            pass

    def _queue_worker(self):
        while True:
            try:
                text = self._queue.get()
                if text is None:
                    continue
                self._speak_internal(text)
                if self._queue.empty() and self._queue_drained_callback:
                    try:
                        self._queue_drained_callback()
                    except Exception as e:
                        print(f"TTS queue drained callback error: {e}")
            except Exception as e:
                print(f"TTS worker error: {e}")

    def clean_text(self, text):
        """Remove emojis and special symbols, keeping alphanumeric, spaces and basic punctuation."""
        return re.sub(r'[^a-zA-Z0-9\s.,!?;:\'\"()-]', '', text)

    def enqueue_sentence(self, sentence):
        """Add a single sentence to the playback queue. Non-blocking."""
        cleaned = self.clean_text(sentence)
        if cleaned.strip():
            self._queue.put(cleaned)

    def enqueue_text(self, text):
        """Split text into sentences and enqueue each. Use for full-text (e.g. function_gemma) or backward compat."""
        for s in split_sentences(text):
            self.enqueue_sentence(s)

    def speak(self, text):
        """Speak full text by splitting into sentences and enqueueing. Non-blocking."""
        self.enqueue_text(text)

    def _speak_internal(self, text):
        command = f"aplay -D {TTS_ALSA_DEVICE} -r 22050 -f S16_LE -t raw -"
        args = shlex.split(command)
        print(f"Synthesizing: {text[:50]}...")
        try:
            with subprocess.Popen(args, stdin=subprocess.PIPE) as play_process:
                t0 = time.perf_counter()
                for chunk in self.voice.synthesize(text):
                    play_process.stdin.write(chunk.audio_int16_bytes)
                tts_ms = (time.perf_counter() - t0) * 1000
                print(f"  text-to-speech: {tts_ms:.0f} ms")
                play_process.stdin.close()
                play_process.wait()
            if play_process.returncode != 0:
                print(f"aplay exited with code {play_process.returncode}")
        except Exception as e:
            print(f"Audio Error: {e}")

if __name__ == "__main__":
    # Test all three sizes: small (low), medium, large (high)
    models = [
        ("small", "en_US-lessac-low"),
        ("medium", "en_US-lessac-medium"),
        ("large", "en_US-lessac-high"),
    ]
    msg = "Hello, my name is Pocket. Nice to meet you."

    for label, model_name in models:
        print(f"\n{'='*60}\n  Model: {label} ({model_name})\n{'='*60}")
        done = threading.Event()
        ai = PocketAudio(model_name=model_name)
        ai.set_queue_drained_callback(lambda: done.set())
        ai.speak(msg)
        print("Waiting for playback to finish...")
        if not done.wait(timeout=30):
            print("Timeout waiting for playback.")
        else:
            print("Done.")