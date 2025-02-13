
import PySimpleGUI as sg
import pyaudio
import wave
import whisper
import datetime
import re
import pyperclip
import warnings
from collections import Counter
from threading import Thread
import numpy as np

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
volume_level = 0

def top_three_words(text):
    words = re.findall(r"\w+", text.lower())
    stop = {"the", "is", "a", "an", "and", "or", "of", "to",
            "in", "for", "that", "on", "with", "it", "be",
            "this", "you", "i", "we", "at", "by"}
    filtered = [w for w in words if w not in stop]
    common = Counter(filtered).most_common(3)
    return "_".join([c[0] for c in common]) if common else "no_summary"

def record_audio():
    """Threaded function to capture audio and update volume_level."""
    global recording, frames, volume_level
    frames = []
    pa = pyaudio.PyAudio()
    stream = pa.open(format=FORMAT, channels=CHANNELS, rate=RATE,
                     input=True, frames_per_buffer=CHUNK)

    while recording:
        data = stream.read(CHUNK)
        frames.append(data)

        samples = np.frombuffer(data, dtype=np.int16)
        raw_amplitude = np.average(np.abs(samples))
        volume_level = int(raw_amplitude * 2)

    stream.stop_stream()
    stream.close()
    pa.terminate()

def transcribe_audio(wav_file):
    model = whisper.load_model("base")
    result = model.transcribe(wav_file)
    return result["text"]

def save_audio_file(filename):
    pa = pyaudio.PyAudio()
    wf = wave.open(filename, 'wb')
    wf.setnchannels(CHANNELS)
    wf.setsampwidth(pa.get_sample_size(FORMAT))
    wf.setframerate(RATE)
    wf.writeframes(b''.join(frames))
    wf.close()

def main():
    sg.theme("DarkBlue3")

    layout = [
        [sg.Text(" ")],
        [
            sg.Button("Record", button_color=("white", "red"), font=("Arial", 14, "bold")),
            sg.Button("Stop recording", button_color=("white", "darkorange"), font=("Arial", 14, "bold")),
            sg.Button("Copy to clipboard", button_color=("white", "green"), font=("Arial", 14, "bold"))
        ],
        [sg.Text(" ")],
        [sg.ProgressBar(max_value=5000, orientation='h', size=(40, 20), key='-METER-')],
        [sg.Text(" ")],
        [sg.Multiline("", size=(60, 10), key="-TRANSCRIPT-")],
        [sg.Exit()]
    ]

    window = sg.Window("Dictate", layout, finalize=True)
    global recording, volume_level
    record_thread = None

    def show_quick_msg(msg, duration=2):
        """Helper to place the popup at (30, 250) relative to the main window."""
        main_x, main_y = window.current_location()
        popup_x = main_x + 30
        popup_y = main_y + 305
        sg.popup_quick_message(
            msg,
            auto_close_duration=duration,
            location=(popup_x, popup_y)
        )

    while True:
        event, _ = window.read(timeout=100)
        if event in (sg.WIN_CLOSED, "Exit"):
            break

        if event == "Record":
            if not record_thread or not record_thread.is_alive():
                recording = True
                record_thread = Thread(target=record_audio, daemon=True)
                record_thread.start()
                show_quick_msg("Recording started!", duration=3)

        elif event == "Stop recording":
            if recording:
                recording = False
                if record_thread and record_thread.is_alive():
                    record_thread.join()

                wave_output = "temp_audio.wav"
                save_audio_file(wave_output)
                show_quick_msg("Transcribing...")

                text = transcribe_audio(wave_output)
                summary = top_three_words(text)
                stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"transcript_{stamp}_{summary}.txt"
                with open(filename, "w", encoding="utf-8") as f:
                    f.write(text)

                window["-TRANSCRIPT-"].update(text)
                show_quick_msg(f"Saved to {filename}", 2)

        elif event == "Copy to clipboard":
            transcript = window["-TRANSCRIPT-"].get()
            if transcript.strip():
                pyperclip.copy(transcript)
                show_quick_msg("Copied to clipboard!")

        window['-METER-'].update(current_count=volume_level)

    window.close()

if __name__ == "__main__":
    main()


