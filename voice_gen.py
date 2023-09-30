from os import walk, getcwd, pardir
import yaml
import os
import wave
import torch
import contextlib
from pydub import AudioSegment
import hashlib
from nltk.tokenize import word_tokenize
from num2t4ru import num2text


def _trivial__enter__(self):
    return self


def _self_close__exit__(self, exc_type, exc_value, traceback):
    self.close()


wave.Wave_read.__exit__ = wave.Wave_write.__exit__ = _self_close__exit__
wave.Wave_read.__enter__ = wave.Wave_write.__enter__ = _trivial__enter__

torch.set_grad_enabled(False)
device = torch.device('cpu')
torch.set_num_threads(2)  # safe optimal value, i.e. 2 CPU cores, does not work properly in colab
symbols = '_~абвгдеёжзийклмнопрстуфхцчшщъыьэюя +.,!?…:;–«»'
local_file = '..\\model.jit'

if not os.path.isfile(local_file):
    torch.hub.download_url_to_file('https://models.silero.ai/models/tts/ru/v1_kseniya_16000.jit',
                                   local_file)

if not os.path.isfile('tts_utils.py'):
    torch.hub.download_url_to_file('https://raw.githubusercontent.com/snakers4/silero-models/master/tts_utils.py',
                                   'tts_utils.py')

import sys, inspect

currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)
from tts_utils import apply_tts  # modify these utils and use them your project

model = torch.jit.load('..\\model.jit',
                       map_location=device)
model.eval()

sample_rate = 16000
model = model.to(device)

lines = dict()
with open('all_form.txt', encoding='utf8') as f:
    line = f.readlines()
    for el in line:
        try:
            lines[el.split()[0]] = el.split()[1]
        except:
            pass


def stressed(text):
    res = []
    s = word_tokenize(text)
    for i in range(len(s)):
        if s[i].isnumeric():
            s[i] = num2text(int(s[i]))
    for t in s:
        try:
            res.append(lines[t.lower()])
        except:
            if len(t) > 1:
                res.append(kyrgryz_stress(t))
            else:
                res.append(t)
    return " ".join(res)


def process_base_case(word):
    GLASSN = ('а', 'е', 'ё', 'и', 'о', 'у', 'ы', 'э', 'ю', 'я')
    ind = 0
    for i, w in enumerate(word[::-1]):
        if w in GLASSN:
            ind = i
            break
    ind += 1
    word = word[:-ind] + '+' + word[-ind:]
    return word


def kyrgryz_stress(word):
    if word.endswith('ов'):
        return word[:-2] + '+' + word[-2:]
    elif word.endswith('ева'):
        return word[:-4] + '+' + word[-4:]
    elif word.endswith(('бек', 'ова', 'eв', 'бека')):
        return word[:-3] + '+' + word[-3:]
    else:
        return process_base_case(word)


def write_wave(path, audio, sample_rate):
    """Writes a .wav file.
    Takes path, PCM audio data, and sample rate.
    """
    with wave.open(path, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(audio)
        wf.close()


def ksenspeak(text, hash):
    p = os.path.abspath('..\\voices\\' + str(hash) + '.wav')
    if os.path.isfile(p):
        # print('PASS')
        return
    audio = apply_tts(texts=[text],
                      model=model,
                      sample_rate=sample_rate,
                      symbols=symbols,
                      device=device)

    for i, _audio in enumerate(audio):
        write_wave(path=f'test_0.wav',
                   audio=(audio[i] * 32767).numpy().astype('int16'),
                   sample_rate=16000)

    import librosa
    y, sr = librosa.load('test_0.wav')  # y is a numpy array of the wav file, sr = sample rate
    # y_shifted = librosa.effects.time_stretch(y, rate=0.9)
    # y_shifted = librosa.effects.pitch_shift(y_shifted, n_steps=3, bins_per_octave=24, sr=sr) # shifted by 4 half steps

    # import soundfile as sf
    # samplerate = sr
    # sf.write('test_1.wav', y_shifted, samplerate, subtype='PCM_24')

    filename = 'test_0.wav'
    sound = AudioSegment.from_file(filename, format=filename[-3:])

    octaves = 0.2

    new_sample_rate = int(sound.frame_rate * (2.0 ** octaves))
    hipitch_sound = sound._spawn(sound.raw_data, overrides={'frame_rate': new_sample_rate})
    hipitch_sound = hipitch_sound.set_frame_rate(44100)
    print(hash)

    hipitch_sound.export(str(hash) + ".wav", format="wav")


path = os.path.abspath(os.path.join(getcwd(), os.pardir))
filenames = next(walk(path), (None, None, []))[2]
filenames = [x for x in filenames if ".yml" in x]
# print(filenames)
dc = []
for f in filenames:
    with open("..\\" + f, "r", encoding='utf-8') as stream:
        try:
            dc.append(yaml.safe_load(stream))
        except yaml.YAMLError as exc:
            print(exc)

snt = []
answ = []

for d in dc:
    snt += [x[1] for x in d['conversations']]
    answ += [int(hashlib.md5(x[1].encode('utf-8')).hexdigest(), 16) for x in d['conversations']]

for i in range(len(snt)):
    st = stressed(snt[i])
    try:
        ksenspeak(st, answ[i])
    except Exception as e:
        print(st)
        print(e)

# txt = "Привет. Меня зовут Барсик. Я студентка Международного Университета Ала-Тоо"
# id_ = int(hashlib.md5(txt.encode('utf-8')).hexdigest(), 16)
# ksenspeak(stressed(txt), "privet")