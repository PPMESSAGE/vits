import collections
import contextlib
import sys
import wave

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

_V_INTERVAL_FRAME = 22
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
            print("FRAMES: %d" % len(_voice_frames))
            _keep = []
            return "NULL"
        else:
            print("")
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
            print("")
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

        print("%d %s" % (is_speech, _status), end=" ")


def vad_collector(sample_rate, frame_duration_ms,
                  padding_duration_ms, vad, frames):
    """Filters out non-voiced audio frames.

    Given a webrtcvad.Vad and a source of audio frames, yields only
    the voiced audio.

    Uses a padded, sliding window algorithm over the audio frames.
    When more than 90% of the frames in the window are voiced (as
    reported by the VAD), the collector triggers and begins yielding
    audio frames. Then the collector waits until 90% of the frames in
    the window are unvoiced to detrigger.

    The window is padded at the front and back to provide a small
    amount of silence or the beginnings/endings of speech around the
    voiced frames.

    Arguments:

    sample_rate - The audio sample rate, in Hz.
    frame_duration_ms - The frame duration in milliseconds.
    padding_duration_ms - The amount to pad the window, in milliseconds.
    vad - An instance of webrtcvad.Vad.
    frames - a source of audio frames (sequence or generator).

    Returns: A generator that yields PCM audio data.
    """
    num_padding_frames = int(padding_duration_ms / frame_duration_ms)
    print("num_padding_frames: %s" % num_padding_frames)
    # We use a deque for our sliding window/ring buffer.
    ring_buffer = collections.deque(maxlen=num_padding_frames)
    # We have two states: TRIGGERED and NOTTRIGGERED. We start in the
    # NOTTRIGGERED state.
    triggered = False

    voiced_frames = []
    for frame in frames:
        is_speech = vad.is_speech(frame.bytes, sample_rate)

        sys.stdout.write('1' if is_speech else '0')
        if not triggered:
            ring_buffer.append((frame, is_speech))
            num_voiced = len([f for f, speech in ring_buffer if speech])
            # If we're NOTTRIGGERED and more than 90% of the frames in
            # the ring buffer are voiced frames, then enter the
            # TRIGGERED state.
            if num_voiced > 0.9 * ring_buffer.maxlen:
                triggered = True
                sys.stdout.write('+(%s)' % (ring_buffer[0][0].timestamp,))
                # We want to yield all the audio we see from now until
                # we are NOTTRIGGERED, but we have to start with the
                # audio that's already in the ring buffer.
                for f, s in ring_buffer:
                    voiced_frames.append(f)
                ring_buffer.clear()
        else:
            # We're in the TRIGGERED state, so collect the audio data
            # and add it to the ring buffer.
            voiced_frames.append(frame)
            ring_buffer.append((frame, is_speech))
            num_unvoiced = len([f for f, speech in ring_buffer if not speech])
            # If more than 90% of the frames in the ring buffer are
            # unvoiced, then enter NOTTRIGGERED and yield whatever
            # audio we've collected.
            if num_unvoiced > 0.9 * ring_buffer.maxlen:
                sys.stdout.write('-(%s)' % (frame.timestamp + frame.duration))
                triggered = False
                yield b''.join([f.bytes for f in voiced_frames])
                ring_buffer.clear()
                voiced_frames = []
    if triggered:
        sys.stdout.write('-(%s)' % (frame.timestamp + frame.duration))
    sys.stdout.write('\n')
    # If we have any leftover voiced audio when we run out of input,
    # yield it.
    if voiced_frames:
        yield b''.join([f.bytes for f in voiced_frames])


def main(args):
    if len(args) != 2:
        sys.stderr.write(
            'Usage: example.py <aggressiveness> <path to wav file>\n')
        sys.exit(1)
    audio, sample_rate = read_wave(args[1])
    vad = webrtcvad.Vad(int(args[0]))
    frames = frame_generator(30, audio, sample_rate)
    frames = list(frames)
    vad_dding(vad, frames, sample_rate)
    print("frames: %s" % len(_voice_frames))
    # segments = vad_collector(sample_rate, 30, 300, vad, frames)
    # for i, segment in enumerate(segments):
    #     path = 'chunk-%002d.wav' % (i,)
    #     print(' Writing %s' % (path,))
    #     write_wave(path, segment, sample_rate)


if __name__ == '__main__':
    main(sys.argv[1:])
