import collections
import queue
import threading
import numpy as np
import pyaudio
import time
from faster_whisper import WhisperModel

# --- CONFIGURATION ---
MODEL_SIZE = "tiny"         # Tiny is fastest for Pi 5
DEVICE = "cpu"              # Pi 5 uses CPU
COMPUTE_TYPE = "int8"       # Optimized for ARM CPUs
CHUNK_SIZE = 1024           # Frames per buffer
FORMAT = pyaudio.paInt16    # 16-bit PCM
CHANNELS = 1                # Mono
RATE = 16000                # Whisper expects 16kHz
SILENCE_THRESHOLD = 500     # Adjust based on your mic sensitivity
# ---------------------

class STTEngine:
    def __init__(self):
        self.model = None
        self.listening = False
        self.audio_queue = queue.Queue()
        self.result_queue = queue.Queue() # For passing text back to main thread
        self.thread = None
        self.stream = None
        self.p = pyaudio.PyAudio()

    def load_model(self):
        if self.model is None:
            print(f"Loading Whisper model '{MODEL_SIZE}'...")
            self.model = WhisperModel(MODEL_SIZE, device=DEVICE, compute_type=COMPUTE_TYPE, cpu_threads=4)
            print("Whisper model loaded.")

    def _mic_callback(self, in_data, frame_count, time_info, status):
        if self.listening:
            self.audio_queue.put(in_data)
        return (None, pyaudio.paContinue)

    def start_listening(self):
        if self.listening:
            return
        
        # Ensure model is loaded (this might block if not preloaded, so best to preload)
        if not self.model:
            self.load_model()
            
        self.listening = True
        self.audio_queue = queue.Queue() # Clear queue
        
        self.stream = self.p.open(format=FORMAT,
                        channels=CHANNELS,
                        rate=RATE,
                        input=True,
                        input_device_index=0,
                        frames_per_buffer=CHUNK_SIZE,
                        stream_callback=self._mic_callback)
        
        self.thread = threading.Thread(target=self._process_audio, daemon=True)
        self.thread.start()
        print("STT Started Listening")

    def stop_listening(self):
        self.listening = False
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
            self.stream = None
        # We don't join the thread immediately to avoid UI blocking, it will exit loop
        print("STT Stopped Listening")

    def _process_audio(self):
        # Buffer to hold current "phrase"
        MAX_BUFFER_LEN = 100 # ~3 seconds of audio
        audio_buffer = collections.deque(maxlen=MAX_BUFFER_LEN)
        
        while self.listening:
            try:
                # Get data from queue with timeout to allow checking self.listening
                data = self.audio_queue.get(timeout=0.5)
                audio_buffer.append(data)
                
                # Drain pending
                while not self.audio_queue.empty():
                    audio_buffer.append(self.audio_queue.get())

                # Transcribe if we have enough data? 
                # Actually, for a "Push to Talk" style, we might want to just accumulate 
                # and transcribe ONLY when stopped or periodically?
                # The user request said: "start to transcribe my voice then when I press it again it stops transcription then that transcription is sent"
                # This implies we should ACCUMULATE audio while listening, and transcribe AT THE END.
                
                # However, for long sentences, intermediate transcription is nice.
                # But for simplicity and satisfying "sent to ai model... when I press it again it stops",
                # let's just keep accumulating in a larger buffer?
                # If we use deque with maxlen, we lose start.
                # Let's switch to a list for the full session if it's push-to-talk.
                # Wait, if I speak for 10 seconds, deque(100) (approx 3s) will lose info.
                
                # REVISION: creating a full buffer for the session.
                pass 
            except queue.Empty:
                continue
        
        # End of listening loop - Final Transcription
        if len(audio_buffer) > 0:
            full_audio = b''.join(audio_buffer)
            # We need to preserve ALL audio for the final query? 
            # The existing code used a deque for rolling window.
            # But the user interaction model is "Press Start -> Speak -> Press Stop -> Transcribe".
            # So I should probably capture EVERYTHING between Start and Stop.
        else:
            return

    def transcribe_accumulated(self):
        """
        Actually, let's change the strategy.
        _mic_callback fills a buffer.
        When stop_listening is called, we process that buffer.
        """
        pass # Re-implementing logic below

    # RETHINKING IMPLEMENTATION FOR USER REQUEST:
    # "press it, it start to transcribe... press it again it stops... then that transcription is sent"
    
    def start_capture(self):
        if self.listening: return
        self.listening = True
        self.audio_frames = []
        
        if not self.model: self.load_model()

        self.stream = self.p.open(format=FORMAT,
                        channels=CHANNELS,
                        rate=RATE,
                        input=True,
                        input_device_index=0,
                        frames_per_buffer=CHUNK_SIZE,
                        stream_callback=self._capture_callback)
        print("Capture Started")

    def _capture_callback(self, in_data, frame_count, time_info, status):
        if self.listening:
            self.audio_frames.append(in_data)
        return (None, pyaudio.paContinue)

    def stop_and_transcribe(self):
        self.listening = False
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
            self.stream = None
        
        print(f"Capture Stopped. Frames: {len(self.audio_frames)}")
        if not self.audio_frames:
            return ""
        
        # Process
        return self._transcribe_buffer(self.audio_frames)

    def _transcribe_buffer(self, frames):
        start_t = time.time()
        current_audio = b''.join(frames)
        # Convert to float32
        audio_np = np.frombuffer(current_audio, dtype=np.int16).astype(np.float32) / 32768.0
        
        # Transcribe
        segments, _ = self.model.transcribe(audio_np, beam_size=1, language="en", vad_filter=True)
        
        text = " ".join([s.text for s in segments]).strip()
        print(f"Transcription ({time.time()-start_t:.2f}s): {text}")
        return text

    def terminate(self):
        self.p.terminate()


if __name__ == "__main__":
    # Test
    engine = STTEngine()
    engine.load_model()
    try:
        while True:
            input("Press Enter to Start Recording...")
            engine.start_capture()
            input("Press Enter to Stop and Transcribe...")
            text = engine.stop_and_transcribe()
            print(f"Final Text: {text}")
    except KeyboardInterrupt:
        engine.terminate()