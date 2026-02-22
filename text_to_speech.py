import soundfile as sf
import numpy as np
from kokoro import KPipeline

def generate_paragraph_speech():
    # 1. Initialize the pipeline
    # 'a' stands for American English ('b' is available for British English)
    print("Loading Kokoro-82M model...")
    pipeline = KPipeline(lang_code='a')
    
    # 2. Define the paragraph
    paragraph = (
        "The Raspberry Pi 5 is a remarkable piece of hardware. "
        "It represents a massive leap in processing power over its predecessors, "
        "making it entirely possible to run artificial intelligence models locally. "
        "With the right software, this tiny board can synthesize human-like speech "
        "in a matter of milliseconds!"
    )
    
    # 3. Generate the audio
    # The pipeline automatically breaks the paragraph down so the model doesn't get overwhelmed.
    # 'af_heart' is one of the highest-rated American female voices included with the model.
    print("Synthesizing speech...")
    generator = pipeline(
        paragraph, 
        voice='af_heart', 
        speed=1.0, 
        split_pattern=r'\n+' # Ensures it handles structural line breaks properly
    )
    
    # 4. Collect the generated audio chunks
    audio_chunks = []
    for i, (graphemes, phonemes, audio_data) in enumerate(generator):
        print(f"  -> Processed chunk {i+1}: {graphemes.strip()}")
        audio_chunks.append(audio_data)
        
    # Combine all the individual sentence chunks into one continuous audio array
    final_audio = np.concatenate(audio_chunks)
    
    # 5. Save the final audio to a WAV file
    # Kokoro natively generates audio at a 24,000 Hz sample rate
    sf.write("pi_output.wav", final_audio, 24000)
    print("\nSuccess! Audio saved to pi_output.wav")

if __name__ == "__main__":
    generate_paragraph_speech()