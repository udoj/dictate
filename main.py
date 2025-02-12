import pyaudio
import wave
import whisper
import datetime
import re
from collections import Counter
from threading import Thread
import warnings

warnings.filterwarnings(
    "ignore",
    message="FP16 is not supported on CPU; using FP32 instead"
)

CHUNK = 1024
RATE = 16000
CHANNELS = 1
FORMAT = pyaudio.paInt16
WAVE_OUTPUT = "temp_audio.wav"
recording = False
frames = []

def top_three_words(text):
    words = re.findall(r"\w+", text.lower())
    stop = {"the","is","a","an","and","or","of","to","in","for","that","on","with","it","be","this","you","i","we","at","by"}
    filtered = [w for w in words if w not in stop]
    common = Counter(filtered).most_common(3)
    return "_".join([c[0] for c in common]) if common else "no_summary"

def record_audio():
    global recording, frames
    frames = []
    pa = pyaudio.PyAudio()
    stream = pa.open(format=FORMAT, channels=CHANNELS, rate=RATE,
                     input=True, frames_per_buffer=CHUNK)
    print("▶ Recording started. Press ENTER in the main console to stop.")
    while recording:
        data = stream.read(CHUNK)
        frames.append(data)
    stream.stop_stream()
    stream.close()
    pa.terminate()
    print("⏹ Recording stopped.")

def main():
    global recording

    input("Press ENTER to start recording...\n")
    recording = True
    record_thread = Thread(target=record_audio, daemon=True)
    record_thread.start()

    input("Press ENTER to stop recording...\n")
    recording = False
    record_thread.join()

    wf = wave.open(WAVE_OUTPUT, 'wb')
    pa = pyaudio.PyAudio()
    wf.setnchannels(CHANNELS)
    wf.setsampwidth(pa.get_sample_size(FORMAT))
    wf.setframerate(RATE)
    wf.writeframes(b''.join(frames))
    wf.close()

    print("Transcribing audio...")
    model = whisper.load_model("base")
    # force English if you want: model.transcribe(WAVE_OUTPUT, language="en")
    result = model.transcribe(WAVE_OUTPUT)
    text = result["text"]
    summary = top_three_words(text)

    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"transcript_{stamp}_{summary}.txt"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(text)

    print("🎤 Transcribed Text:")
    print(text)
    print(f"✅  Saved transcript to {filename}")
    print("🗒 3-word summary:", summary)

if __name__ == "__main__":
    main()

