import collections
import queue
import threading
import numpy as np
import pyaudio
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

# Initialize Faster Whisper
print(f"Loading model '{MODEL_SIZE}'...")
model = WhisperModel(MODEL_SIZE, device=DEVICE, compute_type=COMPUTE_TYPE)

audio_queue = queue.Queue()

def mic_callback(in_data, frame_count, time_info, status):
    """Collects audio from the mic and puts it in the queue."""
    audio_queue.put(in_data)
    return (None, pyaudio.paContinue)

def run_stt():
    """Processes the queue and transcribes speech."""
    p = pyaudio.PyAudio()
    
    stream = p.open(format=FORMAT,
                    channels=CHANNELS,
                    rate=RATE,
                    input=True,
                    input_device_index=0,
                    frames_per_buffer=CHUNK_SIZE,
                    stream_callback=mic_callback)

    print("\n--- Listening! Speak into the mic (Ctrl+C to stop) ---")
    
    # Buffer to hold current "phrase"
    # Use maxlen to automatically discard old data
    MAX_BUFFER_LEN = 100 # ~3 seconds of audio
    audio_buffer = collections.deque(maxlen=MAX_BUFFER_LEN)
    
    try:
        while True:
            # Get data from queue (blocking for the first chunk)
            data = audio_queue.get()
            audio_buffer.append(data)
            
            # Drain any additional pending chunks to catch up (prevents lag)
            while not audio_queue.empty():
                audio_buffer.append(audio_queue.get())

            # Once we have sufficient audio context
            if len(audio_buffer) >= 15: 
                # Concatenate once directly into numpy
                # Optimization: Avoid b''.join() every loop if possible, 
                # but map/filter is fast. FasterWhisper needs float32.
                
                # To minimize copy, we join only when transcribing.
                # A ring buffer approach might be better, but deque is okay for this scale.
                
                current_audio = b''.join(audio_buffer)
                audio_np = np.frombuffer(current_audio, dtype=np.int16).astype(np.float32) / 32768.0
                
                # Transcribe
                segments, _ = model.transcribe(audio_np, beam_size=5)
                
                for segment in segments:
                    # Clear line and print (simple real-time feel)
                    print(f"\rTranscript: {segment.text}", end="", flush=True)
                
                # Optimization: Clear buffer overlap strategy?
                # The original code sliced the list: audio_buffer = audio_buffer[-20:]
                # Deque with maxlen handles the "growing too large" case automatically.
                # However, to avoid re-transcribing the same old start indefinitely, 
                # we might want to pop left. 
                # For now, relying on maxlen is a rolling window, which is good for context.


    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        stream.stop_stream()
        stream.close()
        p.terminate()

if __name__ == "__main__":
    run_stt()