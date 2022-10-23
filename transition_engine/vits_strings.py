import os
import sys
import numpy as np

import pypinyin
from scipy.io import wavfile

import datetime
import torch

from merge_text import remove_punctuation
from merge_text import convert_pinyin

sys.path.append('..')
import utils
from models import SynthesizerTrn

from text import pinyin_symbols
from text import cleaned_text_to_sequence

def chinese_to_phonemes(text):
    text = remove_punctuation(text)
    text = convert_pinyin(text)
    return text

def save_wav(wav, path, rate):
    wav *= 32767 / max(0.01, np.max(np.abs(wav))) * 0.6
    wavfile.write(path, rate, wav.astype(np.int16))

def get_text_ids(phones, hps):
    text_norm = cleaned_text_to_sequence(phones)
    text_norm = torch.LongTensor(text_norm)
    return text_norm

#
# define model and load checkpoint
hps = utils.get_hparams_from_file("../configs/tr_base.json")

net_g = SynthesizerTrn(
    len(symbols),
    hps.data.filter_length // 2 + 1,
    hps.train.segment_size // hps.data.hop_length,
    **hps.model).cuda()
_ = net_g.eval()

_ = utils.load_checkpoint("../logs/tr_base/G_160000.pth", net_g, None)

# check directory existence
if not os.path.exists("./vits_out"):
    os.makedirs("./vits_out")

if __name__ == "__main__":
    n = 0
    fo = open("vits_strings.txt", "r+")
    while(True):
        try:
            message = fo.readline().strip()
        except Exception as e:
            print('nothing of except:', e)
            break
        if (message == None):
            break
        if (message == ""):
            break
        n = n + 1

        print("===============================================================")
        phonemes = chinese_to_phonemes(message)
        input_ids = get_text_ids(phonemes, hps)

        print(datetime.datetime.now())
        with torch.no_grad():
            x_tst = input_ids.cuda().unsqueeze(0)
            x_tst_lengths = torch.LongTensor([input_ids.size(0)]).cuda()
            audio = net_g.infer(x_tst, x_tst_lengths, noise_scale=0, noise_scale_w=0, length_scale=1)[0][0,0].data.cpu().float().numpy()
        print(datetime.datetime.now())

        save_wav(audio, f"./vits_out/{n}_baker.wav", hps.data.sampling_rate)

        print(message)
        print(phonemes)
        print(input_ids)
    fo.close()

    # can be deleted
    os.system("chmod 777 ./vits_out -R")
