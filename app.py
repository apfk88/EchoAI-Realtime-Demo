import streamlit as st
import os
import time
import assemblyai as aai
import threading
from streamlit.runtime.scriptrunner import add_script_run_ctx

from dotenv import load_dotenv
load_dotenv()

from assembly_transcriber import AssemblyTranscriber
aai.settings.api_key = os.getenv('ASSEMBLYAI_API_KEY')

# Set Streamlit page config
st.set_page_config(page_title='Real-Time AT&T Agent', initial_sidebar_state='expanded')

# Header
st.image('echo_logo.svg', width=150)
st.title('Real-time Agent Assist')

# Call Selection
file_path = st.selectbox('Select a call', ['call1.mp3', 'call2.mp3', 'call3.mp3'], index=0)

# Init sidebar
st.sidebar.title('Agent Notes')

# Init session state
st.session_state['previous_note'] = ''
st.session_state['previous_transcript'] = []

# LeMUR calls to generate notes / suggestions
def lemur(text):
    # Replace speaker tags with Customer and Agent
    text = text.replace('SPEAKER 0:', 'Customer:').replace('SPEAKER 1:', 'Agent:')

    # Prompt for LeMUR
    prompt = f'''
    You are a helpful customer service agent assistant. Your job is to take dilligent notes for the agent during the phone call.
    I will provide you will a live transcript of the call and the previous_notes you took.

    Sometimes you will be asked to make suggestions to the agent based on what the customer said.
    You will only give the following suggestions if one of the following rules is true:
    - If customer says they live in an apartment or home, suggest that the agent ask if they own or rent.
    - If a customer says they are using an alternative service that isn't AT&T,suggest that the agent ask them what they don't like about their current service.
    - If a customer wants internet or cable service, suggest that the agent ask them if they'd be interested in bundling other services.
    
    Instructions:
    - Provide your notes in less than 3 bullet points.
    - Only include notes about the customer and not about the agent's business.
    - Return only your notes and no preamble or sign-off.
    - Do not repeat new notes that are already included in the previous notes.
    - Do not assume anything about the customer's situation.
    - Only include a suggestion if it meets the given rules.
    - Do not repeat suggestions that have already been given.
    - If you include a suggestion, make its the last bullet point.
    - If you include a suggestion, format it as "Suggestion: <suggestion>"
    - If you have no notes or suggestions, return "• No new notes. Listening..."
    '''
    
    # Add previous notes to input text to reduce repetition
    if st.session_state['previous_note'] != '':
        prompt += f'''
        Previous Notes: {st.session_state['previous_note']}
        '''
        input_text = f'<transcript>{text}</transcript>\n\n</previous_notes>{st.session_state["previous_note"]}</previous_notes>'
    else:
        input_text = text
    
    res = aai.Lemur().task(input_text=input_text, prompt=prompt, final_model=aai.LemurModel.default).response
    
    # Add new generated notes to previous notes variable
    st.session_state['previous_note'] += f'{res}\n'
    return res

# Get transcript from db.json, since we have two streams, we use a file to store the transcript in chronological order
def get_transcript():
    try:
        with open('db.json', 'r') as f:
            text = f.read()
            return text
    except:
        return None

# Thread to pull transcript from db.json and present it in the UI in real-time
def present_transcript():
    while True:
        tr = get_transcript()
        
        if tr:
            # Temp workaround to fix AT&T transcription
            tr = tr.replace('At and t', 'AT&T').replace(' at and t', ' AT&T').replace('at AMP t', 'AT&T')
        
            split = tr.split('\n')
            for s in split:
                # Skip if already presented
                if s in st.session_state['previous_transcript']:
                    continue
                    
                # Add agent and customer tags
                if 'SPEAKER 0:' in s:
                    st.write(f'Customer: {s.replace("SPEAKER 0:","")}')
                elif 'SPEAKER 1:' in s:
                    st.write(f'Agent: {s.replace("SPEAKER 1:","")}')
                
                # Add line to previous transcript variable
                st.session_state['previous_transcript'].append(s)
                
                # Attempting to align transcript to audio file for demo. 
                # Add sleep based on the length of the line and ~150 WPM
                # 150 WPM = 2.5 WPS
                sleep_time = len(s.split(' ')) / 2.5
                sleep_time = max(2, sleep_time)
                sleep_time = min(8, sleep_time)
                time.sleep(sleep_time)
        # time.sleep(2)
    
# Thread to make LeMUR calls every 15 seconds and present the notes / suggestions in the sidebar
def make_lemur_calls(sleep_time=15):
    while True:
        tr = get_transcript()
        if tr:
            response = lemur(tr)
            if '-' in response:
                response = response.replace('-', '•')
            split = response.split('•')
            
            # Loop through new notes and suggestions
            for i in range(len(split)):
                split[i] = split[i].strip()
                split[i] = split[i].replace('<text>', '')
                if len(split[i]) == 0:
                    continue
                if 'Suggestion' in split[i]:
                    # Highlight suggestions
                    st.sidebar.markdown(f'<p style="color:red;font-weight:700">{split[i]}</p>', unsafe_allow_html=True)
                elif split[i] == 'No new notes. Listening...' or split[i] == 'No new notes' or split[i] == 'No new suggestions':
                    continue
                    # st.sidebar.markdown(f'<p style="color:grey">{split[i]}</p>', unsafe_allow_html=True)
                else:
                    st.sidebar.markdown(f'• {split[i]}')
            # st.sidebar.divider()
        time.sleep(sleep_time)

def transcribe_file(fp, channel):
    transcriber = AssemblyTranscriber(channel=channel)
    # Start the connection
    transcriber.connect()
    # Only WAV/PCM16 single channel supported for now
    file_stream = aai.extras.stream_file(
    filepath=fp,
    sample_rate=22050, # sample rate of the EchoAI's audio files
    )
    transcriber.stream(file_stream)

# PyDub to split audio into channels and speed up audio, requires ffmpeg
# import pydub
# def create_channel_files(fp, channel_no):
#     audio = pydub.AudioSegment.from_file(fp)
#     with open(f'{fp}-channel{channel_no}.wav', 'wb') as f:
#         audio.split_to_mono()[channel_no].export(f, format='wav')
#     return f'{fp}-channel{channel_no}.wav'
# st.audio(create_channel_files(file_path, 0), format='audio/wav')
# st.audio(create_channel_files(file_path, 1), format='audio/wav')

# def speed_up_audio(fp, speed):
#     audio = pydub.AudioSegment.from_file(fp)
#     audio = audio.speedup(playback_speed=speed)
#     audio = audio.export(fp, format='wav')
#     return audio
# st.audio(speed_up_audio(file_path, 2.0), format='audio/wav')

# Audio player
st.audio('audio/' + file_path)

# Start button
start_button = st.button('Start Live Transcription')

if start_button:
    # Create new db.json to store transcript
    with open('db.json', 'w') as f:
        f.write('')

    st.markdown('#### Call Transcript')
    st.sidebar.markdown('<p style="color:grey">No new notes. Listening...</p>', unsafe_allow_html=True)
    
    # Transcribe each channel in a separate thread
    thread1 = threading.Thread(target=transcribe_file, args=(f"audio/{file_path}-channel0.wav",0))
    thread2 = threading.Thread(target=transcribe_file, args=(f"audio/{file_path}-channel1.wav",1))
    
    # Create thread to present transcript in real-time
    thread3 = threading.Thread(target=present_transcript)

    # Create thread to make LeMUR calls every 15 seconds
    thread4 = threading.Thread(target=make_lemur_calls)

    # Add threads to script run context
    add_script_run_ctx(thread3)
    add_script_run_ctx(thread4)

    # Start threads
    thread1.start()
    thread2.start()
    thread3.start()
    thread4.start()
    
    # Wait for both threads to finish
    thread1.join()
    thread2.join()
    thread3.join()
    thread4.join()