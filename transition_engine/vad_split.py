import collections
import contextlib
import sys
import wave
import os

import webrtcvad

CHANNELS = 1
SAMPLE_WIDTH = 2

def read_wave(path):
    """Reads a .wav file.

    Takes the path, and returns (PCM audio data, sample rate).
    """
    with contextlib.closing(wave.open(path, 'rb')) as wf:
        print("num_channels: %s, sample_width: %s, sample_rate: %s" % (wf.getnchannels(),
                                                                       wf.getsampwidth(),
                                                                       wf.getframerate())) 
        num_channels = wf.getnchannels()
        assert num_channels == CHANNELS
        sample_width = wf.getsampwidth()
        assert sample_width == SAMPLE_WIDTH
        sample_rate = wf.getframerate()
        assert sample_rate in (8000, 16000, 32000, 48000)
        pcm_data = wf.readframes(wf.getnframes())
        return pcm_data, sample_rate


def write_wave(path, audio, sample_rate):
    """Writes a .wav file.

    Takes path, PCM audio data, and sample rate.
    """
    with contextlib.closing(wave.open(path, 'wb')) as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(SAMPLE_WIDTH)
        wf.setframerate(sample_rate)
        wf.writeframes(audio)


class Frame(object):
    """Represents a "frame" of audio data."""
    def __init__(self, bytes, timestamp, duration):
        self.bytes = bytes
        self.timestamp = timestamp
        self.duration = duration


def frame_generator(frame_duration_ms, audio, sample_rate):
    """Generates audio frames from PCM audio data.

    Takes the desired frame duration in milliseconds, the PCM data, and
    the sample rate.

    Yields Frames of the requested duration.
    """
    n = int(sample_rate * (frame_duration_ms / 1000.0) * 2)
    offset = 0
    timestamp = 0.0
    duration = (float(n) / sample_rate) / 2.0
    while offset + n < len(audio):
        yield Frame(audio[offset:offset + n], timestamp, duration)
        timestamp += duration
        offset += n

# =========================================

_V_INTERVAL_FRAME = 24
_S_INTERVAL_FRAME = 33
_keep = []
_silence = []
_voice_frames = []

def _null_status(is_speech, frame):
    global _keep
    if is_speech == 0:
        return "NULL"
    if is_speech == 1:
        _keep = []
        _keep.append(frame)
        return "PRE_V"
    return "NULL"

def _voice_status(is_speech, frame):
    global _keep
    global _silence
    if is_speech == 1:
        _keep.append(frame)
        return "VOICE"
    if is_speech == 0:
        _keep.append(frame)
        _silence = []
        return "PRE_N"    
    return "VOICE"

def _pre_n_status(is_speech, frame):
    global _keep
    global _silence
    global _voice_frames
    if is_speech == 0:
        _silence.append(frame)
        _keep.append(frame)
        if len(_silence) > _S_INTERVAL_FRAME:
            _voice_frames.append(_keep)
            _keep = []
            return "NULL"
        else:
            return "PRE_N"
    if is_speech == 1:
        _keep.append(frame)
        return "VOICE"
    
    return "PRE_N"

def _pre_v_status(is_speech, frame):
    global _keep
    if is_speech == 1:
        _keep.append(frame)
        if len(_keep) > _V_INTERVAL_FRAME:
            return "VOICE"
        else:
            return "PRE_V"
    if is_speech == 0:
        _keep = []
        return "NULL"
    return "PRE_V"

def vad_dding(vad, frames, sample_rate):
    _status = "NULL"
    for frame in frames:
        is_speech = vad.is_speech(frame.bytes, sample_rate)
        if _status == "NULL":
            _status = _null_status(is_speech, frame)
        elif _status == "VOICE":
            _status = _voice_status(is_speech, frame)
        elif _status == "PRE_V":
            _status = _pre_v_status(is_speech, frame)
        elif _status == "PRE_N":
            _status = _pre_n_status(is_speech, frame)
        else:
            print("ERROR _status: %s" % _status)

def get_wave_files(wave_dir):
    files = os.listdir(wave_dir)
    print(files)
    files = filter(lambda f: f[-4:] == ".wav", files)
    files = list(files)
    files = list(map(lambda f: os.path.join(wave_dir, f), files))
    return files

def save_split_files(split_dir, file_name, framess, sample_rate):
    pre = file_name.split("/")[-1][:-4]
    i = 0
    for frames in framess:
        file_name = pre + "%03d.wav" % i
        print(file_name)
        i += 1
        dest = os.path.join(split_dir, file_name)
        print(dest)
        wave_data = b""
        for frame in frames:
            wave_data += frame.bytes
        write_wave(dest, wave_data, sample_rate)
    return


def main(args):
    if len(args) != 2:
        sys.stderr.write(
            'Usage: example.py <dir to mono> <dir to data>\n')
        sys.exit(1)

    if not os.path.isdir(args[0]):
        sys.stderr.write('Not dir\n')
        sys.exit(1)

    if not os.path.isdir(args[1]):
        sys.stderr.write('Not dir\n')
        sys.exit(1)

    vad = webrtcvad.Vad(0)
    wave_files = get_wave_files(args[0])
    for wave_file in wave_files:
        global _voice_frames
        _voice_frames = []
        audio, sample_rate = read_wave(wave_file)
        frames = frame_generator(30, audio, sample_rate)
        frames = list(frames)
        vad_dding(vad, frames, sample_rate)
        save_split_files(args[1], wave_file, _voice_frames, sample_rate)
        print("frames: %s" % len(_voice_frames))
    
    # segments = vad_collector(sample_rate, 30, 300, vad, frames)
    # for i, segment in enumerate(segments):
    #     path = 'chunk-%002d.wav' % (i,)
    #     print(' Writing %s' % (path,))
    #     write_wave(path, segment, sample_rate)


if __name__ == '__main__':
    main(sys.argv[1:])
