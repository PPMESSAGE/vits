import collections
import sys
import os
import random

def get_train_valid(audio_txt):
    _lines = []
    _train = []
    _valid = []
    with open(audio_txt) as f:
        while True:
            _line = f.readline()
            if not _line:
                break

            _line = _line.strip()
            _lines.append(_line)
            
            if len(_lines) == 10:
                _v = random.choices(_lines, k=2)
                _t = list(filter(lambda x: x not in _v, _lines))
                _train += _t
                _valid += _v
                _lines = []

    return _train, _valid

def main(args):
    if len(args) != 2:
        sys.stderr.write(
            'Usage: example.py <path to audio_txt> <dir to train/valid>\n')
        sys.exit(1)

    if not os.path.isfile(args[0]):
        sys.stderr.write('Not file\n')
        sys.exit(1)

    if not os.path.isdir(args[1]):
        sys.stderr.write('Not dir\n')
        sys.exit(1)

    _train, _valid = get_train_valid(args[0])

    print(len(_valid))
    _train_path = os.path.join(args[1], "train_audio_text.txt")
    with open(_train_path, "w") as _f:
        _f.write("\n".join(_train))

    _valid_path = os.path.join(args[1], "valid_audio_text.txt")
    with open(_valid_path, "w") as _f:
        _f.write("\n".join(_valid))


if __name__ == '__main__':
    main(sys.argv[1:])
