#!/bin/bash
_16000=$1
_22050=$2
for filename in ${_16000}/*.wav; do
    echo ${filename}
    _base=$(basename ${filename} .wav)
    echo ${_base}
    sox ${filename} -r 22050 ${_22050}/${_base}_22050.wav
done
