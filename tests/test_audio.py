"""Préparation de l'audio : WAV du micro, autres formats via ffmpeg, contrôles de durée et de silence."""

import io
import shutil
import subprocess
import wave

import numpy as np
import pytest

import audio as AU


def wav(secondes=2.0, taux=48_000, canaux=1, amplitude=0.3, largeur=2):
    t = np.arange(int(secondes * taux)) / taux
    x = amplitude * np.sin(2 * np.pi * 220 * t)
    if canaux == 2:
        x = np.stack([x, x], axis=1).reshape(-1)
    entier = (x * (2 ** (8 * largeur - 1) - 1)).astype({2: "<i2", 4: "<i4"}[largeur])
    sortie = io.BytesIO()
    with wave.open(sortie, "wb") as w:
        w.setnchannels(canaux)
        w.setsampwidth(largeur)
        w.setframerate(taux)
        w.writeframes(entier.tobytes())
    return sortie.getvalue()


@pytest.mark.parametrize("taux, canaux, largeur", [(48_000, 1, 2), (44_100, 2, 2), (16_000, 1, 4)])
def test_wav_du_micro_converti_en_16k_mono(taux, canaux, largeur):
    x = AU.preparer(wav(taux=taux, canaux=canaux, largeur=largeur))
    assert x.dtype == np.float32 and abs(AU.duree(x) - 2.0) < 0.01
    assert 0.25 < np.max(np.abs(x)) <= 1.0


@pytest.mark.skipif(not shutil.which("ffmpeg"), reason="ffmpeg absent")
def test_mp3_decode_par_ffmpeg():
    mp3 = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", "pipe:0", "-f", "mp3", "pipe:1"],
                         input=wav(), capture_output=True, check=True).stdout
    x = AU.preparer(mp3)
    assert abs(AU.duree(x) - 2.0) < 0.1


@pytest.mark.parametrize("octets, message", [
    (b"", "vide"),
    (b"pas du son du tout", "pas un enregistrement"),
    (wav(secondes=0.2), "trop court"),
    (wav(secondes=1.0, amplitude=0.001), "Je n'entends rien"),
])
def test_enregistrements_refuses_avec_message(octets, message):
    with pytest.raises(AU.AudioInvalide, match=message):
        AU.preparer(octets)


def test_trop_long(monkeypatch):
    monkeypatch.setattr(AU, "DUREE_MAX_S", 1)
    with pytest.raises(AU.AudioInvalide, match="un seul verset"):
        AU.preparer(wav(secondes=2))
