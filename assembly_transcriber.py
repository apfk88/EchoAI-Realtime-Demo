import os
import time

import assemblyai as aai
from dotenv import load_dotenv
load_dotenv()

aai.settings.api_key = os.getenv('ASSEMBLYAI_API_KEY')

SAMPLE_RATE = 22050 # Hz, based on EchoAI's audio files

class AssemblyTranscriber(aai.RealtimeTranscriber):
    def __init__(self, channel=0):
        self.channel = channel
        super().__init__(
            on_data=self.on_data,
            on_error=self.on_error,
            on_open=self.on_open, # optional
            on_close=self.on_close, # optional
            sample_rate=SAMPLE_RATE,
            encoding=aai.AudioEncoding.pcm_s16le,
            # word_boost=['AT&T']
        )
        
    def on_open(self, session_opened: aai.RealtimeSessionOpened):
        "Called when the connection has been established."
        print("Session ID:", session_opened.session_id)

    def on_data(self, transcript: aai.RealtimeTranscript):
        "Called when a new transcript has been received."

        if not transcript.text:
            return

        if isinstance(transcript, aai.RealtimeFinalTranscript):
            print(transcript.text, end="\r\n")
            # Add to db.json in the format "SPEAKER <channel>: <transcript>"
            with open(f'db.json', 'a') as f:
                f.write(f'SPEAKER {self.channel}: {transcript.text}\n')
            
    def on_error(self, error: aai.RealtimeError):
        "Called when the connection has been closed."
        print("An error occured:", error)

    def on_close(self):
        "Called when the connection has been closed."
        print("Closing Session")

        # copy to calllog-<timestamp>.txt
        # with open(f'calllog-{int(time.time())}.txt', 'w') as f:
        #     f.write(text)
        # os.remove('db.json')