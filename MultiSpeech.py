# -*- coding: utf-8 -*-
import subprocess
import requests
import json
import time
import os
import re
import numpy as np
import jaconv
import librosa
import soundfile as sf
from datetime import datetime

Voicevox_speakers = {"四国めたん（あまあま）":0, "ずんだもん（あまあま）":1,
                     "四国めたん（ノーマル）":2, "ずんだもん（ノーマル）":3,
                     "四国めたん（セクシー）":4, "ずんだもん（セクシー）":5,
                     "四国めたん（ツンツン）":6, "ずんだもん（ツンツン）":7,
                     "九州そら（ノーマル）":16, "九州そら（あまあま）":15,
                     "九州そら（ツンツン）":18, "九州そら（セクシー）":17,
                     "九州そら（セクシー）":19,
                     "春日部つむぎ":8, "波音リツ":9, "雨晴はう":10,
                     "玄野武宏":11,"白上虎太郎":12,"青山龍星":13,
                     "冥鳴ひまり":14}
Coeiroink_speakers = {"つくよみちゃん":0, "AI声優-朱花":50}
AIVOICE_speakers = {"紲星あかり":5209, "紲星あかり（蕾）":5210}

def wav_wait(file):
    while True:
        try:
            if os.path.isfile("./wav/%s"%file):
                break
        except PermissionError: continue

def nchars(s, n):
    assert n > 0
    reg = re.compile("(.)\\1{%d,}" % (n - 1))  # カンマを取ると n 個ちょうどになる
    while True:
        m = reg.search(s)
        if not m:
            break
        yield m.group(0)
        s = s[m.end():]

def start():
    """Start up SofTalk.
    """
    cmd = "Softalk.exe /NM:女性01 /O:120 /S:100 /V:50 /X:1 /W:"
    v_start = subprocess.Popen(cmd, shell=True)
    v_start.kill

def voice_only(v_name, interval, speed, text):
    """Speak sentences using SofTalk.\n
        Japanese name -> (音声名, 音程, 速度, 発声文章)\n
        UtaYomi -> True(重音テト, 東北きりたん)\n
        return -> None
    """
    if v_name in ["重音テト", "MOTRoid", "試聴用", "東北きりたん"]:
        v_name = "唄詠：" + v_name

    cmd = "Softalk /NM:%s /O:%s /S:%s /V:50 /X:0 /W:%s" % (v_name, interval, speed, text)
    v_in = subprocess.Popen(cmd, shell=True)
    time.sleep(1)

def finish():
    """Stop to softalk after "softalk.voice(v_name, interval, speed, text, emo)".
    """
    cmd = "Softalk.exe /close"
    v_f = subprocess.Popen(cmd, shell=True)
    v_f.kill

# Voicevoxでのtext_to_speech
def Voicevox_voice(speaker, filename, interval, speed, intonation, text):
    """
    Internal Server Error(500)が出ることがあるのでリトライする\n
    （HTTPAdapterのretryはうまくいかなかったので独自実装）\n
    connect timeoutは10秒、read timeoutは300秒に設定（処理が重いので長めにとっておく）\n
    audio_query

    ＜音声引数＞\n
    0：四国めたん（あまあま）\n
    1：ずんだもん（あまあま）\n
    2：四国めたん（ノーマル）\n
    3：ずんだもん（ノーマル）\n
    4：四国めたん（セクシー）\n
    5：ずんだもん（セクシー）\n
    6：四国めたん（ツンツン）\n
    7：ずんだもん（ツンツン）\n
    8：春日部つむぎ\n
    9：波音リツ\n
    10：雨晴はう
    """

    wav_file = "%s\wav\%s.wav" % (os.getcwd(), filename)

    # 音声名の決定
    name = Voicevox_speakers[speaker]
    if int(interval) > 115: interval = "115"
    elif int(interval) < 85: interval = "85"
    if int(speed) > 200 : speed = "200"
    elif int(speed) < 50: speed = "50"
    if text.endswith("!") or text.endswith("?"):
        intonation = "150"

    query_payload = {"text": text, "speaker": name}
    r = requests.post("http://127.0.0.1:50021/audio_query",
                    params=query_payload)
    query_data = r.json()

    # 音質の変更
    interval_scale = int(interval) - 100
    query_data["speedScale"] = int(speed) /100
    query_data["pitchScale"] = interval_scale /100
    query_data["intonationScale"] = int(intonation) / 100

    # 音素解析
    mora_list = []
    text = ""
    for sequence in query_data['accent_phrases']:
        for val in sequence:
            if val == "moras":
                for j in sequence[val]:
                    mora_list.append(j)
            elif val == "pause_mora" and sequence[val]:
                mora_list.append(sequence[val])
    for i in mora_list:
        for j in i:
            if j in ["consonant", "vowel"] and i[j]:
                text+="%s,%d,"%(i[j], int(i[j+"_length"] * 1000))
    with open('./wav/%s.txt'%filename, 'w', encoding='UTF-8') as f:
        f.write(text.rstrip(","))

    # synthesis
    synth_payload = {"speaker": name}
    r = requests.post("http://127.0.0.1:50021/synthesis", params=synth_payload,
        data=json.dumps(query_data))
    with open(wav_file, "wb") as fp:
        fp.write(r.content)

def Coeiroink_voice(speaker, filename, param, interval, speed, intonation, text, emo):
    """
    Internal Server Error(500)が出ることがあるのでリトライする\n
    （HTTPAdapterのretryはうまくいかなかったので独自実装）\n
    connect timeoutは10秒、read timeoutは300秒に設定（処理が重いので長めにとっておく）\n
    audio_query

    ＜音声引数＞\n
    0：つくよみちゃん\n
    1：AI声優-朱花
    """

    if int(interval) > 115: interval = "115"
    elif int(interval) < 85: interval = "85"
    if int(speed) > 200 : speed = "200"
    elif int(speed) < 50: speed = "50"
    wav_file = "%s\wav\%s.wav" % (os.getcwd(), filename)

    # 音声名の決定
    name = Coeiroink_speakers[speaker]

    query_payload = {"text": text, "speaker": name}
    r = requests.post("http://127.0.0.1:50031/audio_query",
                    params=query_payload)
    query_data = r.json()

    # 音質の変更
    interval_scale = int(interval) - 100
    query_data["speedScale"] = int(speed) /100
    query_data["pitchScale"] = interval_scale /100
    query_data["intonationScale"] = int(intonation) / 100

    # 音素解析
    mora_list = []
    text = ""
    for sequence in query_data['accent_phrases']:
        for val in sequence:
            if val == "moras":
                for j in sequence[val]:
                    mora_list.append(j)
            elif val == "pause_mora" and sequence[val]:
                mora_list.append(sequence[val])
    for i in mora_list:
        for j in i:
            if j in ["consonant", "vowel"] and i[j]:
                text+="%s,%d,"%(i[j], int(i[j+"_length"] * 1000))
    with open('./wav/%s.txt'%filename, 'w', encoding='UTF-8') as f:
        f.write(text.rstrip(","))

    # synthesis
    synth_payload = {"speaker": name}
    r = requests.post("http://127.0.0.1:50031/synthesis", params=synth_payload,
        data=json.dumps(query_data))
    with open(wav_file, "wb") as fp:
        fp.write(r.content)

def AIVOICE_voice(v_name:str, filename:str, interval:str, speed:str, intonation:str, sentence:str):
    wav_file = "%s\wav\%s.wav" % (os. getcwd(), filename)
    if int(interval) > 200: interval = "200"
    elif int(interval) < 50: interval = "50"
    if int(speed) > 400 : speed = "400"
    elif int(speed) < 50: speed = "50"
    AIVOICE_name = AIVOICE_speakers[v_name]

    # 連続した半角記号を一文字化
    match_filler = list(nchars(sentence, 2))
    if match_filler:
        for i in match_filler:
            filter = re.search('[「『!?！？。、]+', i)
            if filter:
                sentence = sentence.replace(i, list(set(i))[0])
    if sentence.endswith("!") or sentence.endswith("?"):
        intonation = "150"
    # 発声処理
    cmd = "SeikaSay2.exe -cid %d -save %s -volume 1 -speed %f -pitch %f -intonation %f" % (AIVOICE_name, wav_file, int(speed) / 100, int(interval) / 100, int(intonation) / 100)
    cmd += " -t %s" % sentence
    subprocess.Popen(cmd, shell=True)
    wav_wait("%s.wav"%filename)
    wav_wait("%s.lab"%filename)

    # 音素解析
    l = [s.strip() for s in open("./wav/%s.lab"%filename, encoding = "utf-8_sig").readlines()]
    text = ""
    for i, val in enumerate(l):
        temp = val.split()
        _time = (float(temp[1]) - float(temp[0])) / 10000
        text+= temp[2]+",%d,"%int(_time)
    text = text.replace("q,", "cl,")
    with open('./wav/%s.txt'%filename, 'w', encoding='UTF-8') as f:
        f.write(text.rstrip(",")) #音素列を文字として保存


def softalk_voice(v_name, filename, interval, speed, sentence):
    """Make wav file used SofTalk.\n
    Japanese name -> (音声名, 音程, 速度, 発声文章、感情)\n
    UtaYomi -> True(重音テト, 東北きりたん)\n
    return -> wav_file: path
    """

    wav_file = "%s\wav\%s.wav" % (os.getcwd(), filename)

    if v_name in ["重音テト", "MOTRoid", "試聴用", "東北きりたん"]:
        v_name = "唄詠：" + v_name

    cmd = "Softalk.exe /NM:%s /PS:True /O:%s /S:%s /V:50 /R:%s /X:1 /W:%s" % (v_name, interval, speed, wav_file, sentence)
    _ = subprocess.Popen(cmd, shell=True)

def voice(v_name:str, interval:str, speed:str, intonation:str, text:str):
    """Make wav file used SofTalk or Voicevox.\n
    Japanese name -> (音声名, 音程, 速度, 発声文章、感情)\n
    UtaYomi -> True(重音テト, 東北きりたん)\n
    return -> wav_file: path
    """
    file_name = "%s" %(datetime.now().strftime("%d%H%M%S"))
    if v_name in [j for j in Voicevox_speakers]:
        Voicevox_voice(v_name, file_name, interval, speed, intonation, text)
    elif v_name in [q for q in Coeiroink_speakers]:
        Coeiroink_voice(v_name, file_name, interval, speed, intonation, text)
    elif v_name in [i for i in AIVOICE_speakers]:
        AIVOICE_voice(v_name, file_name, interval, speed, intonation, text)
    else:
        softalk_voice(v_name, file_name, interval, speed, text)

    return file_name
