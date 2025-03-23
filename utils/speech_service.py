import streamlit as st
import os
import io
import wave
from io import BytesIO
import azure.cognitiveservices.speech as speechsdk

SPEECH_KEY = os.getenv("SPEECH_KEY")
SPEECH_REGION = os.getenv("SPEECH_REGION")

def transcribe_audio(audio_data: bytes) -> str:
    """
    Transcribe the provided WAV audio bytes using Azure Cognitive Services Speech SDK.
    Returns recognized text, or an empty string if nothing is recognized.
    """
    # 1) Read WAV properties from the in-memory bytes
    with wave.open(io.BytesIO(audio_data), 'rb') as wf:
        channels = wf.getnchannels()
        sample_rate = wf.getframerate()
        sample_width = wf.getsampwidth()
        frames = wf.readframes(wf.getnframes())

    # 2) Configure the speech service
    speech_config = speechsdk.SpeechConfig(subscription=SPEECH_KEY, region=SPEECH_REGION)
    speech_config.speech_recognition_language = "en-US"

    # 3) Create an AudioStreamFormat that matches the WAV's actual format
    audio_format = speechsdk.audio.AudioStreamFormat(
        samples_per_second=sample_rate,
        bits_per_sample=sample_width * 8,
        channels=channels
    )

    # 4) Create the PushAudioInputStream (note the correct keyword: stream_format)
    push_stream = speechsdk.audio.PushAudioInputStream(stream_format=audio_format)
    push_stream.write(frames)
    push_stream.close()

    # 5) Create the recognizer and attempt recognition
    audio_config = speechsdk.audio.AudioConfig(stream=push_stream)
    recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_config)
    result = recognizer.recognize_once_async().get()

    if result.reason == speechsdk.ResultReason.RecognizedSpeech:
        return result.text
    elif result.reason == speechsdk.ResultReason.NoMatch:
        print("No speech could be recognized.")
    else:
        print(f"Speech recognition canceled or failed: {result.reason}")
    return ""

# def synthesize_text(text: str) -> bytes:
#     """
#     Synthesize the given text into WAV audio bytes using Azure Cognitive Services TTS.
#     """
#     speech_config = speechsdk.SpeechConfig(subscription=SPEECH_KEY, region=SPEECH_REGION)
#     speech_config.speech_synthesis_voice_name = "en-US-BrandonNeural"
#     speech_synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config)

#     result = speech_synthesizer.speak_text_async(text).get()
#     if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
#         return result.audio_data
#     elif result.reason == speechsdk.ResultReason.Canceled:
#         cancellation_details = result.cancellation_details
#         print("Speech synthesis canceled:", cancellation_details.reason)
#         if cancellation_details.reason == speechsdk.CancellationReason.Error:
#             print("Error details:", cancellation_details.error_details)
#     return None


def synthesize_text(text: str):
    # Azure Speech Service configuration
    speech_config = speechsdk.SpeechConfig(subscription=SPEECH_KEY, region=SPEECH_REGION)
    speech_config.speech_synthesis_voice_name = "en-US-AvaMultilingualNeural"

    # Use default audio output configuration
    synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=None)

    # Perform text-to-speech synthesis
    result = synthesizer.speak_text_async(text).get()

    # Check if synthesis was successful
    if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
        # Wrap the audio data in BytesIO for Streamlit
        audio_stream = BytesIO(result.audio_data)
        audio_stream.seek(0)
        return audio_stream
    else:
        print(f"Error synthesizing speech: {result.reason}")
        return None