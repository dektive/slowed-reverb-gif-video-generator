from pedalboard import Pedalboard, Reverb
from pedalboard.io import AudioFile
from pydub import AudioSegment
from pydub.utils import mediainfo
import numpy as np

def reverb(audio_file: str, output_file: str, reverb_level: float = 0.25) -> str:
    board = Pedalboard([Reverb(room_size=reverb_level)])
    with AudioFile(audio_file) as _input:
        with AudioFile(output_file, 'w', _input.samplerate, _input.num_channels) as _output:
            while _input.tell() < _input.frames:
                chunk = _input.read(_input.samplerate)
                effected = board(chunk, _input.samplerate, reset=False)
                _output.write(effected)

    return output_file


def change_speed(audio_file: str, output_file: str, speed: float = 1.0) -> str:
    segment = AudioSegment.from_file(audio_file)
    bitrate = mediainfo(audio_file)['bit_rate']

    sound_with_altered_frame_rate = segment._spawn(segment.raw_data, overrides={"frame_rate": int(segment.frame_rate * speed)})
    edited_segment = sound_with_altered_frame_rate.set_frame_rate(segment.frame_rate)
    edited_segment.export(output_file, bitrate=bitrate)

    return output_file


def eight_d(audio_file: str, output_file: str, period: int = 125) -> str:
    if period < 0:
        period = period * (-1)
    elif period == 0:
        period = 200

    audio = AudioSegment.from_file(audio_file)
    audio = audio + AudioSegment.silent(duration=150)
    bitrate = mediainfo(audio_file)['bit_rate']

    edited_audio = AudioSegment.empty()
    pan = 0.9 * np.sin(np.linspace(0, 2 * np.pi, period))
    chunks = list(enumerate(audio[::100]))

    for i, chunk in chunks:
        if len(chunk) < 100:
            continue
        chunk = chunk.pan(pan[i % period])
        edited_audio += chunk

    edited_audio.export(output_file, bitrate=bitrate)
    return output_file