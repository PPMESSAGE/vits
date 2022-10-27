import collections
import contextlib
import sys
import wave
import os

import pypinyin

sys.path.append('..')
from text import pinyin_symbols


def remove_punctuation(line):
    punc = "#1"
    line = line.replace("，", punc)
    line = line.replace("。", punc)
    line = line.replace("？", punc)
    line = line.replace("、", punc)
    line = line.replace("；", punc)
    line = line.replace("：", punc)
    line = line.replace("！", punc)
    line = line.replace("“", punc)
    line = line.replace("”", punc)
    line = line.replace("‘", punc)
    line = line.replace("’", punc)

    line = line.replace(",", punc)
    line = line.replace(".", punc)
    line = line.replace("?", punc)
    line = line.replace(";", punc)
    line = line.replace(":", punc)
    line = line.replace("!", punc)
    line = line.replace("\"", punc)
    line = line.replace("'", punc)

    return line

_MAX = 0
def convert_pinyin(line):
    #p = pypinyin.lazy_pinyin(line, style=pypinyin.Style.TONE2,
    #                         neutral_tone_with_five=True, errors=lambda x: " ")
    p = ["#sos"]
    x = pypinyin.lazy_pinyin(line, style=pypinyin.Style.INITIALS,
                             strict=False,
                             #strict=True,
                             errors=lambda x: "#2" if x != "#1" else "#1")
    #print(line)
    #print(x)
    assert(x[0] in pinyin_symbols)
    y = pypinyin.lazy_pinyin(line, style=pypinyin.Style.FINALS_TONE3,
                             strict=True,
                             neutral_tone_with_five=True,
                             errors=lambda x: "#2" if x != "#1" else "#1")
    
    #print(x)
    assert(x[0] in pinyin_symbols)
    assert(len(x) == len(y))
    for i in range(len(x)):
        if x[i] == "":
            p.append("^")
        else:
            p.append(x[i])
        if x[i] == "#1" or x[i] == "#2":
            pass
        else:
            p.append(y[i])
            p.append("#3")
    #p.append("#sil")
    p.append("#eos")

    return " ".join(p)
    #q = []
    #_is_blank = False
    #for i in p:
    #    if i == "#1" or i == "#2" or i == "#0":
    #        if _is_blank == False:
    #            _is_blank = True
    #        if _is_blank == True:
    #            continue
    #    else:
    #        if _is_blank == True:
    #            _is_blank = False
    #    q.append(i)

    #print(q)
    # 256
    #global _MAX
    #if len(p) > _MAX:
    #    _MAX = len(p)
    #    print("MAX >>>>>>>>>>>>>> %d" % _MAX)
    #return " ".join(q)

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
            new_line = "audio_material/data/22050/%s_%03d_22050.wav|%s" % (audio_prefix, i, line)
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
