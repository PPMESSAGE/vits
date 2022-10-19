import collections
import contextlib
import sys
import wave
import os

import pypinyin

def remove_punctuation(line):
    line = line.replace("，", " ")
    line = line.replace("。", " ")
    line = line.replace("？", " ")
    line = line.replace("、", " ")
    line = line.replace("；", " ")
    line = line.replace("：", " ")

    line = line.replace(",", " ")
    line = line.replace(".", " ")
    line = line.replace("?", " ")
    line = line.replace(";", " ")
    line = line.replace(":", " ")

    return line

def convert_pinyin(line):
    p = pypinyin.lazy_pinyin(line, style=pypinyin.Style.TONE2,
                             neutral_tone_with_five=True, errors=lambda x: " ")
    return " ".join(p)

def get_text_files(wave_dir):
    files = os.listdir(wave_dir)
    files = filter(lambda f: f[-4:] == ".txt", files)
    files = list(files)
    files = list(map(lambda f: os.path.join(wave_dir, f), files))
    files.sort()
    return files

def generate_text_file(origin):
    audio_prefix = "%s_mono_16000" % origin.split("/")[-1][:-4]
    _lines = []
    i = 0
    with open(origin) as _f:
        for line in _f.readlines():
            line = "".join(line.split(".")[1:])
            line = line.strip()
            line = remove_punctuation(line)
            line = convert_pinyin(line)
            new_line = "audio_material/data/audio/%s_%03d.wav|%s" % (audio_prefix, i, line)
            i += 1
            print(new_line)
            _lines.append(new_line)
    return _lines

def main(args):
    if len(args) != 1:
        sys.stderr.write(
            'Usage: example.py <dir to text>\n')
        sys.exit(1)

    if not os.path.isdir(args[0]):
        sys.stderr.write('Not dir\n')
        sys.exit(1)

    _files = get_text_files(args[0])

    for _file in _files:
        _lines = generate_text_file(_file)
            
        

if __name__ == '__main__':
    main(sys.argv[1:])
