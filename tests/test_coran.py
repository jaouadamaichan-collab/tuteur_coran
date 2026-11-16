"""Texte embarqué : complet, conforme au découpage standard (Hafs), jamais modifié par l'app."""

import pytest

import coran

# Nombre de versets par sourate (numérotation de Koufa, récitation Hafs).
VERSETS = [7, 286, 200, 176, 120, 165, 206, 75, 129, 109, 123, 111, 43, 52, 99, 128, 111, 110, 98, 135, 112, 78, 118,
           64, 77, 227, 93, 88, 69, 60, 34, 30, 73, 54, 45, 83, 182, 88, 75, 85, 54, 53, 89, 59, 37, 35, 38, 29, 18, 45,
           60, 49, 62, 55, 78, 96, 29, 22, 24, 13, 14, 11, 11, 18, 12, 12, 30, 52, 52, 44, 28, 28, 20, 56, 40, 31, 50,
           40, 46, 42, 29, 19, 36, 25, 22, 17, 19, 26, 30, 20, 15, 21, 11, 8, 8, 19, 5, 8, 8, 11, 11, 8, 3, 9, 5, 4, 7,
           3, 6, 3, 5, 4, 5, 6]


def test_114_sourates_6236_versets():
    s = coran.sourates()
    assert len(s) == 114 and [len(x["versets"]) for x in s] == VERSETS and sum(VERSETS) == 6236


def test_premier_et_dernier_verset():
    import alignement as A
    assert [A.squelette(m) for m in A.mots(coran.verset(1, 1)["texte"])] == ["بسم", "لله", "لرحمن", "لرحيم"]
    assert [A.squelette(m) for m in A.mots(coran.verset(114, 6)["texte"])] == ["من", "لجنه", "ولنس"]
    assert coran.verset(1, 1)["fr"].startswith("Au nom d'Allah")


@pytest.mark.parametrize("s, v", [(0, 1), (115, 1), (1, 8), (1, 0)])
def test_reference_inexistante(s, v):
    with pytest.raises(ValueError):
        coran.verset(s, v)


def test_audio_de_reference():
    assert coran.url_audio_reference(2, 255) == "https://everyayah.com/data/Alafasy_128kbps/002255.mp3"


def test_libelle():
    assert coran.libelle_sourate(coran.sourate(112)).startswith("112. Al-Ikhlas — الإخلاص")
