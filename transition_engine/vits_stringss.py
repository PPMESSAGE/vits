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
import commons
from models import SynthesizerTrn

from text import pinyin_symbols
from text import cleaned_text_to_sequence

#
# define model and load checkpoint
hps = utils.get_hparams_from_file("../configs/tr_base.json")

def chinese_to_phonemes(text):
    text = remove_punctuation(text)
    text = convert_pinyin(text)
    return text

def save_wav(wav, path, rate):
    wav *= 32767 / max(0.01, np.max(np.abs(wav))) * 0.6
    wavfile.write(path, rate, wav.astype(np.int16))

def get_text_ids(phones, hps):
    text_norm = cleaned_text_to_sequence(phones)
    if hps.data.add_blank:
        text_norm = commons.intersperse(text_norm, 0)
    text_norm = torch.LongTensor(text_norm)
    return text_norm


net_g = SynthesizerTrn(
    len(pinyin_symbols),
    hps.data.filter_length // 2 + 1,
    hps.train.segment_size // hps.data.hop_length,
    **hps.model)
_ = net_g.eval()

_ = utils.load_checkpoint("../logs/tr_base/latest.pth", net_g, None)


def _main(text):
    phonemes = chinese_to_phonemes(text)
    input_ids = get_text_ids(phonemes, hps)

    print(datetime.datetime.now())
    with torch.no_grad():
        x_tst = input_ids.unsqueeze(0)
        x_tst_lengths = torch.LongTensor([input_ids.size(0)])
        #y_hat, attn, mask, *_ = generator.module.infer(x, x_lengths, max_len=1000)
        print(x_tst)
        print(x_tst_lengths)
        y_hat, attn, mask, *_ = net_g.infer(x_tst, x_tst_lengths, max_len=1000)
        y_hat = y_hat.cpu()
        y_hat_lengths = mask.sum([1,2]).long() * hps.data.hop_length
    print(datetime.datetime.now())

    print("hat_length", y_hat_lengths)
    audio = y_hat[0,:,:y_hat_lengths[0]].numpy()[0]
    print("audio", audio)
    #save_wav(audio, "./vits_out/" + sys.argv[2], hps.data.sampling_rate)

    print(phonemes)
    print(input_ids)
    print(type(audio))
    return audio


if __name__ == "__main__":
    print("===============================================================")
    _texts = sys.argv[1].split("[p300]")
    _audios = np.array([])
    for text in _texts:
        _audios = np.concatenate((_audios, _main(text)))
    save_wav(_audios, "./vits_out/baker.wav", hps.data.sampling_rate)
    ""
