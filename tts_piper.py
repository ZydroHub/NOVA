import os
import re
import subprocess
import shlex
import threading
import queue
import time
import urllib.request
import pyaudio
from piper.voice import PiperVoice

os.environ['ORT_LOGGING_LEVEL'] = '3'

# Optional output-device selection.
# - TTS_OUTPUT_DEVICE_INDEX: explicit PyAudio output device index
# - TTS_OUTPUT_DEVICE_NAME: substring match against output-device name
# - TTS_ALSA_DEVICE: backward-compatible alias for name matching
TTS_OUTPUT_DEVICE_INDEX = os.environ.get("TTS_OUTPUT_DEVICE_INDEX", "").strip()
TTS_OUTPUT_DEVICE_NAME = os.environ.get("TTS_OUTPUT_DEVICE_NAME", "").strip()
TTS_ALSA_DEVICE = os.environ.get("TTS_ALSA_DEVICE", "").strip()

# Sentence-ending punctuation (split on these, keep delimiter with sentence)
SENTENCE_END_RE = re.compile(r'(?<=[.!?\n])\s*')


def split_sentences(text):
    """Split text into sentences on . ! ? and newlines. Strips each; drops empty."""
    if not text or not text.strip():
        return []
    parts = SENTENCE_END_RE.split(text.strip())
    return [p.strip() for p in parts if p.strip()]


def merge_short_sentences(sentences, min_len=42):
    """Merge very short sentence fragments to reduce choppy TTS transitions."""
    merged = []
    buffer = ""
    for sentence in sentences:
        s = sentence.strip()
        if not s:
            continue
        if not buffer:
            buffer = s
            continue
        # Keep natural flow by combining tiny fragments into a longer phrase.
        if len(buffer) < min_len:
            buffer = f"{buffer} {s}".strip()
        else:
            merged.append(buffer)
            buffer = s
    if buffer:
        merged.append(buffer)
    return merged


class PocketAudio:
    def __init__(self, model_name="en_US-lessac-medium"):
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.model_dir = os.path.join(self.base_dir, "models")
        self.model_path = os.path.join(self.model_dir, f"{model_name}.onnx")
        self.config_path = os.path.join(self.model_dir, f"{model_name}.onnx.json")
        
        self._ensure_models_exist(model_name)
        print("Loading Piper into memory... (Standby)")
        self.voice = PiperVoice.load(self.model_path, config_path=self.config_path)
        self.sample_rate = int(getattr(getattr(self.voice, "config", None), "sample_rate", 22050))
        print(f"System Ready. Piper sample rate: {self.sample_rate} Hz")

        # Initialize PyAudio for cross-platform audio playback
        self.p = pyaudio.PyAudio()
        self.output_device_index = self._resolve_output_device_index()
        if self.output_device_index is None:
            print("TTS output device: system default")
        else:
            dev = self.p.get_device_info_by_index(self.output_device_index)
            print(f"TTS output device: {dev.get('name')} (index {self.output_device_index})")

        # Sentence-by-sentence playback queue
        self._queue = queue.Queue()
        self._queue_drained_callback = None
        self._worker = threading.Thread(target=self._queue_worker, daemon=True)
        self._worker.start()

    def _resolve_output_device_index(self):
        # 1) explicit index has highest priority
        if TTS_OUTPUT_DEVICE_INDEX:
            try:
                idx = int(TTS_OUTPUT_DEVICE_INDEX)
                dev = self.p.get_device_info_by_index(idx)
                if dev.get('maxOutputChannels', 0) > 0:
                    return idx
                print(f"TTS warning: device index {idx} is not an output device, using default")
            except Exception as e:
                print(f"TTS warning: invalid TTS_OUTPUT_DEVICE_INDEX '{TTS_OUTPUT_DEVICE_INDEX}': {e}")

        # 2) name match (new env var or backward-compatible alias)
        name_query = (TTS_OUTPUT_DEVICE_NAME or TTS_ALSA_DEVICE).lower()
        if name_query:
            for i in range(self.p.get_device_count()):
                dev = self.p.get_device_info_by_index(i)
                if dev.get('maxOutputChannels', 0) > 0 and name_query in str(dev.get('name', '')).lower():
                    return i
            print(f"TTS warning: no output device matched '{name_query}', using default")

        return None

    def _open_output_stream(self):
        kwargs = {
            "format": pyaudio.paInt16,
            "channels": 1,
            "rate": self.sample_rate,
            "output": True,
        }
        if self.output_device_index is not None:
            kwargs["output_device_index"] = self.output_device_index
        return self.p.open(**kwargs)

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
        stream = None
        while True:
            try:
                text = self._queue.get()
                if text is None:
                    continue
                if stream is None:
                    stream = self._open_output_stream()
                self._speak_internal(text, stream=stream)
                if self._queue.empty() and self._queue_drained_callback:
                    try:
                        self._queue_drained_callback()
                    except Exception as e:
                        print(f"TTS queue drained callback error: {e}")
            except Exception as e:
                if stream is not None:
                    try:
                        stream.stop_stream()
                        stream.close()
                    except Exception:
                        pass
                    stream = None
                print(f"TTS worker error: {e}")

    def clean_text(self, text):
        """Remove emojis and special symbols, keeping alphanumeric, spaces and basic punctuation."""
        cleaned = re.sub(r'[^a-zA-Z0-9\s.,!?;:\'\"()-]', '', text)
        return re.sub(r'\s+', ' ', cleaned).strip()

    def enqueue_sentence(self, sentence):
        """Add a single sentence to the playback queue. Non-blocking. Returns True if queued."""
        cleaned = self.clean_text(sentence)
        if cleaned.strip():
            self._queue.put(cleaned)
            return True
        return False

    def enqueue_text(self, text):
        """Split text into sentences and enqueue each. Returns number of queued sentences."""
        queued = 0
        sentences = merge_short_sentences(split_sentences(text))
        for s in sentences:
            if self.enqueue_sentence(s):
                queued += 1
        return queued

    def speak(self, text):
        """Speak full text by splitting into sentences and enqueueing. Non-blocking."""
        return self.enqueue_text(text)

    def _speak_internal(self, text, stream=None):
        print(f"Synthesizing: {text[:50]}...")
        try:
            # Use a persistent worker stream when available to avoid per-sentence pops/gaps.
            owns_stream = stream is None
            if stream is None:
                stream = self._open_output_stream()
            t0 = time.perf_counter()
            chunk_count = 0
            for chunk in self.voice.synthesize(text):
                stream.write(chunk.audio_int16_bytes)
                chunk_count += 1
            tts_ms = (time.perf_counter() - t0) * 1000
            if chunk_count == 0:
                print("TTS warning: synthesize returned 0 chunks")
            print(f"  text-to-speech: {tts_ms:.0f} ms")
            if owns_stream:
                stream.stop_stream()
                stream.close()
        except Exception as e:
            print(f"Audio Error: {e}")

    def terminate(self):
        """Clean up resources."""
        if hasattr(self, 'p'):
            self.p.terminate()

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