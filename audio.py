"""Préparer un enregistrement pour la reconnaissance : mono, 16 kHz, nombres flottants entre -1 et 1.

Le micro du navigateur (st.audio_input) donne un WAV, lu directement. Un fichier envoyé (MP3, M4A, OGG…) est
décodé par ffmpeg (installé sur Streamlit Cloud via packages.txt). L'audio ne fait que transiter en mémoire.
"""

from __future__ import annotations

import io
import subprocess
import wave
from math import gcd

import numpy as np
from scipy.signal import resample_poly

TAUX = 16_000
DUREE_MAX_S = 180          # un verset dépasse rarement 2 minutes
DUREE_MIN_S = 0.5
SILENCE = 0.01             # niveau crête en dessous duquel on considère qu'il n'y a rien d'enregistré


class AudioInvalide(ValueError):
    pass


def _depuis_wav(octets: bytes) -> np.ndarray:
    with wave.open(io.BytesIO(octets)) as w:
        canaux, largeur, taux, n = w.getnchannels(), w.getsampwidth(), w.getframerate(), w.getnframes()
        brut = w.readframes(n)
    if largeur == 2:
        x = np.frombuffer(brut, dtype="<i2").astype(np.float32) / 32768.0
    elif largeur == 4:
        x = np.frombuffer(brut, dtype="<i4").astype(np.float32) / 2147483648.0
    elif largeur == 1:
        x = (np.frombuffer(brut, dtype=np.uint8).astype(np.float32) - 128.0) / 128.0
    else:
        raise AudioInvalide("Format WAV non pris en charge")
    if canaux > 1:
        x = x.reshape(-1, canaux).mean(axis=1)
    if taux != TAUX:
        p = gcd(TAUX, taux)
        x = resample_poly(x, TAUX // p, taux // p).astype(np.float32)
    return x


def _avec_ffmpeg(octets: bytes) -> np.ndarray:
    try:
        r = subprocess.run(
            ["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", "pipe:0", "-ac", "1", "-ar", str(TAUX), "-f", "f32le", "pipe:1"],
            input=octets, capture_output=True, timeout=60, check=False,
        )
    except FileNotFoundError as ex:
        raise AudioInvalide("Ce format n'est pas lisible ici : envoie un fichier WAV ou enregistre-toi avec le micro.") from ex
    if r.returncode != 0 or not r.stdout:
        raise AudioInvalide("Ce fichier n'est pas un enregistrement audio lisible.")
    return np.frombuffer(r.stdout, dtype="<f4").copy()


def preparer(octets: bytes) -> np.ndarray:
    """Audio prêt pour la reconnaissance. Lève AudioInvalide avec un message à montrer tel quel."""
    if not octets:
        raise AudioInvalide("L'enregistrement est vide.")
    if octets[:4] == b"RIFF" and octets[8:12] == b"WAVE":
        try:
            x = _depuis_wav(octets)
        except (wave.Error, EOFError, ValueError):
            x = _avec_ffmpeg(octets)
    else:
        x = _avec_ffmpeg(octets)
    duree = len(x) / TAUX
    if duree < DUREE_MIN_S:
        raise AudioInvalide("L'enregistrement est trop court.")
    if duree > DUREE_MAX_S:
        raise AudioInvalide(f"L'enregistrement dépasse {DUREE_MAX_S // 60} minutes : enregistre un seul verset à la fois.")
    if float(np.max(np.abs(x))) < SILENCE:
        raise AudioInvalide("Je n'entends rien : vérifie que le micro est autorisé et rapproche-toi.")
    return np.clip(x, -1.0, 1.0).astype(np.float32)


def duree(x: np.ndarray) -> float:
    return len(x) / TAUX
