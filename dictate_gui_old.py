import PySimpleGUI as sg
import pyaudio
import wave
import whisper
import datetime
import re
import pyperclip
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

recording = False
frames = []


def top_three_words(text):
    words = re.findall(r"\w+", text.lower())
    stop = {"the", "is", "a",  "an", "and", "or", "of", "to", "in", "for", "that", "on", "with", "it", "be", "this",
            "you", "i", "we", "at", "by"}
    filtered = [w for w in words if w not in stop]
    common = Counter(filtered).most_common(3)
    return "_".join([c[0] for c in common]) if common else "no_summary"


def record_audio():
    global recording, frames
    frames = []
    pa = pyaudio.PyAudio()
    stream = pa.open(format=FORMAT, channels=CHANNELS, rate=RATE,
                     input=True, frames_per_buffer=CHUNK)
    while recording:
        data = stream.read(CHUNK)
        frames.append(data)
    stream.stop_stream()
    stream.close()
    pa.terminate()


def transcribe_audio(filename):
    model = whisper.load_model("base")
    # Or model.transcribe(filename, language="en") if you want to force English
    result = model.transcribe(filename)
    return result["text"]


def main():
    layout = [
        [sg.Text("Whisper Recorder", font=("Arial", 14, "bold"))],
        [sg.Button("Record"), sg.Button("Stop"), sg.Button("Copy")],
        [sg.Multiline("", size=(60, 10), key="-TRANSCRIPT-")],
        [sg.Exit()]
    ]

    window = sg.Window("Whisper GUI", layout)
    record_thread = None
    global recording

    while True:
        event, _ = window.read(timeout=100)
        if event in (sg.WIN_CLOSED, "Exit"):
            break

        if event == "Record":
            sg.popup_quick_message("Recording started...", auto_close_duration=1)
            sg.popup_quick_message("Stopping recording...", auto_close_duration=1)
            recording = True
            record_thread = Thread(target=record_audio, daemon=True)
            record_thread.start()

        elif event == "Stop":
            if recording:

                recording = False
                if record_thread and record_thread.is_alive():
                    record_thread.join()

                wave_output = "temp_audio.wav"
                with wave.open(wave_output, 'wb') as wf:
                    pa = pyaudio.PyAudio()
                    wf.setnchannels(CHANNELS)
                    wf.setsampwidth(pa.get_sample_size(FORMAT))
                    wf.setframerate(RATE)
                    wf.writeframes(b''.join(frames))

                sg.popup_quick_message("Transcribing...", auto_close_duration=1)
                text = transcribe_audio(wave_output)
                summary = top_three_words(text)
                stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"transcript_{stamp}_{summary}.txt"
                with open(filename, "w", encoding="utf-8") as f:
                    f.write(text) # type: ignore

                window["-TRANSCRIPT-"].update(text) # type: ignore
                sg.popup_quick_message(f"Transcript saved to {filename}", auto_close_duration=2)

        elif event == "Copy":
            transcript_elem = window["-TRANSCRIPT-"]
            if transcript_elem is not None:
                transcript = transcript_elem.get()
                if transcript.strip():
                    pyperclip.copy(transcript)
                    sg.popup_quick_message("Text copied to clipboard!", auto_close_duration=1)

    window.close()


if __name__ == "__main__":
    main()
