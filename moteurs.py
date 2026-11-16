"""Moteurs de reconnaissance comparés par le banc d'essai.

Deux modèles Whisper de même taille, pour isoler l'effet de la spécialisation :
- tarteel-ai/whisper-base-ar-quran (Apache-2.0) : Whisper entraîné sur des récitations du Coran ;
- openai/whisper-base (MIT) : Whisper généraliste, en arabe.
Hypothèse à vérifier : le modèle spécialisé reconnaît mieux la récitation mais « entend » plus souvent le bon
verset quand l'élève se trompe (il masque des erreurs). Le banc d'essai mesure les deux effets.
Les modèles sont téléchargés depuis Hugging Face au premier usage (environ 300 Mo chacun) et tournent sur CPU.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable

import numpy as np

from audio import TAUX


@dataclass(frozen=True)
class Moteur:
    id: str
    nom: str
    modele: str
    description: str


MOTEURS = {
    "tarteel": Moteur("tarteel", "Spécialisé Coran (Tarteel)", "tarteel-ai/whisper-base-ar-quran",
                      "Whisper base entraîné sur des récitations du Coran"),
    "whisper": Moteur("whisper", "Généraliste (Whisper)", "openai/whisper-base",
                      "Whisper base d'OpenAI, arabe courant"),
}


class MoteurIndisponible(RuntimeError):
    pass


def creer_pipeline(modele: str):
    """Pipeline de reconnaissance Hugging Face (import tardif : torch est lourd)."""
    try:
        from transformers import pipeline
    except ImportError as ex:  # pragma: no cover - dépend de l'installation
        raise MoteurIndisponible("Les bibliothèques de reconnaissance (transformers, torch) ne sont pas installées.") from ex
    try:
        return pipeline("automatic-speech-recognition", model=modele, device="cpu")
    except Exception as ex:  # téléchargement impossible, mémoire insuffisante…
        raise MoteurIndisponible(f"Impossible de charger le modèle {modele} : {ex}") from ex


@dataclass
class Transcription:
    texte: str
    secondes: float


def transcrire(pipe: Callable, audio: np.ndarray) -> Transcription:
    """Transcrit un verset récité. On impose l'arabe ; si le modèle refuse cette option (certains modèles affinés
    fixent déjà la langue), on réessaie sans."""
    entree = {"raw": audio, "sampling_rate": TAUX}
    options = {"chunk_length_s": 30} if len(audio) > 30 * TAUX else {}
    debut = time.perf_counter()
    try:
        try:
            sortie = pipe(dict(entree), generate_kwargs={"language": "arabic", "task": "transcribe"}, **options)
        except (ValueError, TypeError):
            sortie = pipe(dict(entree), **options)
    except Exception as ex:
        raise MoteurIndisponible(f"La reconnaissance a échoué : {ex}") from ex
    texte = sortie.get("text", "") if isinstance(sortie, dict) else str(sortie)
    return Transcription(texte.strip(), time.perf_counter() - debut)
