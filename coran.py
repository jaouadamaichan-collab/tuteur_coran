"""Texte du Coran embarqué dans l'application (jamais produit par une IA).

Source : paquet npm quran-json 3.1.2 (licence CC BY-SA 4.0) : texte uthmani de The Noble Qur'an Encyclopedia
(quranenc.com), traduction française de Muhammad Hamidullah (tanzil.net). 114 sourates, 6 236 versets.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

FICHIER = Path(__file__).resolve().parent / "data" / "coran.json"
RECITATEUR_REFERENCE = "Alafasy_128kbps"   # récitation de Mishary Alafasy, servie par everyayah.com


@lru_cache(maxsize=1)
def sourates() -> list[dict]:
    return json.loads(FICHIER.read_text(encoding="utf-8"))


def sourate(n: int) -> dict:
    if not 1 <= n <= 114:
        raise ValueError(f"Sourate inconnue : {n}")
    return sourates()[n - 1]


def verset(s: int, v: int) -> dict:
    versets = sourate(s)["versets"]
    if not 1 <= v <= len(versets):
        raise ValueError(f"La sourate {s} a {len(versets)} versets")
    return versets[v - 1]


def libelle_sourate(s: dict) -> str:
    return f"{s['n']}. {s['translit']} — {s['nom']} ({s['traduction']}, {len(s['versets'])} versets)"


def url_audio_reference(s: int, v: int, recitateur: str = RECITATEUR_REFERENCE) -> str:
    """Récitation de référence d'un verset (fichier MP3 lu directement par le navigateur de l'élève)."""
    return f"https://everyayah.com/data/{recitateur}/{s:03d}{v:03d}.mp3"
