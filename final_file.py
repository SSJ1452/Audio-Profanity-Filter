from google.cloud import speech_v1
import io
import os
import numpy as np
from scipy.io.wavfile import write
from pydub import AudioSegment

def sample_recognize(local_file_path):
    # Initialize the Google Cloud Speech client with the service account JSON key file
    client = speech_v1.SpeechClient.from_service_account_json('PrestiSolutions-fb3de2002b43.json')

    # Configuration for recognition
    language_code = "en-IN"
    sample_rate_hertz = 48000
    enable_word_time_offsets = True
    profanity_filter = True
    encoding = speech_v1.RecognitionConfig.AudioEncoding.FLAC

    config = {
        "enable_word_time_offsets": enable_word_time_offsets,
        "language_code": language_code,
        "sample_rate_hertz": sample_rate_hertz,
        "encoding": encoding,
        "profanity_filter": profanity_filter
    }

    # Read the audio file
    with io.open(local_file_path, "rb") as f:
        content = f.read()
    audio = {"content": content}

    # Perform speech recognition
    response = client.recognize(config=config, audio=audio)
    
    # Extract start and end times of profane words
    start_time = []
    end_time = []
    timeline = []

    for result in response.results:
        alternative = result.alternatives[0]
        print(u"Transcript: {}".format(alternative.transcript))
        for word in alternative.words:
            timeline.append(word.start_time.seconds + word.start_time.nanos * (10 ** -9))
            timeline.append(word.end_time.seconds + word.end_time.nanos * (10 ** -9))
            if '*' in word.word:
                start_time.append(word.start_time.seconds + word.start_time.nanos * (10 ** -9))
                end_time.append(word.end_time.seconds + word.end_time.nanos * (10 ** -9))
                
    return start_time, end_time, timeline

# Input audio file
input_audio = 'inaudio.aac'

# Convert the audio to the required format and single channel using ffmpeg
os.system(f'ffmpeg -i {input_audio} -vn out1.flac mono.wav')
os.system('ffmpeg -i out1.flac -ac 1 mono.flac')

# Recognize profanities and generate timelines
print("Processing audio...")
start_time, end_time, timeline = sample_recognize('mono.flac')

# Generate a beep sound for censoring profanities
sps = 44100
freq_hz = 1000.0
duration = 0.3
vol = 0.3
esm = np.arange(duration * sps)
wf = np.sin(2 * np.pi * esm * freq_hz / sps)
wf_quiet = wf * vol
wf_int = np.int16(wf_quiet * 32767)
write("beep.wav", sps, wf_int)

# Initialize combined audio with initial segment
def split_profaned_audio(audio_path, start_time, end_time, ti_me):
    audio_file = f"audio{ti_me + 1}.wav"
    os.system(f'ffmpeg -i {audio_path} -ss {start_time} -t {end_time - start_time} -acodec copy {audio_file}')
    print(f'Segment {ti_me + 1} created.')

audio_path = 'mono.wav'
split_profaned_audio(audio_path, timeline[0] + 0.1, start_time[0] + 0.1, -1)  # Initialization
sound = AudioSegment.from_wav("audio0.wav")
beep = AudioSegment.from_wav("beep.wav")
combined_sounds = sound + beep

# Process all profane sections
len_ = len(start_time)
if len_ > 1:
    for ti_me in range(len_ - 1):
        split_profaned_audio(audio_path, end_time[ti_me] + 0.1, start_time[ti_me + 1] + 0.1, ti_me)
        sound = AudioSegment.from_wav(f"audio{ti_me + 1}.wav")
        combined_sounds += sound + beep

    split_profaned_audio(audio_path, end_time[-1] + 0.1, timeline[-1] + 0.1, len_ - 1)
    sound = AudioSegment.from_wav(f"audio{len_}.wav")
    combined_sounds += sound
else:
    ti_me = 0
    split_profaned_audio(audio_path, end_time[ti_me] + 0.1, timeline[-1] + 0.1, ti_me)
    sound = AudioSegment.from_wav(f"audio{ti_me + 1}.wav")
    combined_sounds += sound + beep

# Export the final censored audio
combined_sounds.export("combined_sounds.wav", format="wav")
print("Audio processing complete. Censored audio saved as 'combined_sounds.wav'.")
