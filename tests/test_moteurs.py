"""Appel des moteurs de reconnaissance (pipeline simulé : les vrais modèles se chargent sur Streamlit Cloud)."""

import numpy as np
import pytest

import moteurs as MO


class FauxPipeline:
    def __init__(self, texte="الحمد لله رب العالمين", refuse_langue=False, panne=False):
        self.texte, self.refuse_langue, self.panne, self.appels = texte, refuse_langue, panne, []

    def __call__(self, entree, **kwargs):
        self.appels.append(kwargs)
        if self.panne:
            raise RuntimeError("mémoire insuffisante")
        if self.refuse_langue and "generate_kwargs" in kwargs:
            raise ValueError("forced_decoder_ids déjà fixés")
        assert entree["sampling_rate"] == 16_000 and entree["raw"].dtype == np.float32
        return {"text": f"  {self.texte} "}


AUDIO = np.zeros(16_000 * 3, dtype=np.float32)


def test_arabe_impose_et_texte_nettoye():
    p = FauxPipeline()
    t = MO.transcrire(p, AUDIO)
    assert t.texte == "الحمد لله رب العالمين" and t.secondes >= 0
    assert p.appels[0]["generate_kwargs"] == {"language": "arabic", "task": "transcribe"}
    assert "chunk_length_s" not in p.appels[0]


def test_modele_qui_fixe_deja_la_langue():
    p = FauxPipeline(refuse_langue=True)
    assert MO.transcrire(p, AUDIO).texte and len(p.appels) == 2 and "generate_kwargs" not in p.appels[1]


def test_long_verset_decoupe_en_morceaux_de_30s():
    p = FauxPipeline()
    MO.transcrire(p, np.zeros(16_000 * 70, dtype=np.float32))
    assert p.appels[0]["chunk_length_s"] == 30


def test_panne_du_moteur_message_clair():
    with pytest.raises(MO.MoteurIndisponible, match="mémoire insuffisante"):
        MO.transcrire(FauxPipeline(panne=True), AUDIO)


def test_deux_moteurs_de_meme_taille():
    assert {m.modele for m in MO.MOTEURS.values()} == {"tarteel-ai/whisper-base-ar-quran", "openai/whisper-base"}
