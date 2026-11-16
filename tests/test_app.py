"""Banc d'essai de bout en bout (streamlit.testing), moteurs simulés."""

import io
import wave
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

import moteurs as MO

APP = str(Path(__file__).resolve().parent.parent / "app.py")


class FauxModele:
    """Simule un modèle : chaque nom de modèle renvoie la transcription qu'on lui a fixée."""
    transcriptions: dict = {}
    charges: list = []

    def __init__(self, modele):
        self.modele = modele
        FauxModele.charges.append(modele)

    def __call__(self, entree, **kwargs):
        return {"text": FauxModele.transcriptions.get(self.modele, "")}


@pytest.fixture(autouse=True)
def moteurs(monkeypatch):
    st.cache_resource.clear()
    FauxModele.transcriptions, FauxModele.charges = {}, []
    monkeypatch.setattr(MO, "creer_pipeline", FauxModele)


def wav(secondes=2.0):
    t = np.arange(int(secondes * 16000)) / 16000
    x = (0.3 * np.sin(2 * np.pi * 220 * t) * 32767).astype("<i2")
    sortie = io.BytesIO()
    with wave.open(sortie, "wb") as w:
        w.setnchannels(1), w.setsampwidth(2), w.setframerate(16000), w.writeframes(x.tobytes())
    return sortie.getvalue()


def lancer():
    at = AppTest.from_file(APP, default_timeout=30)
    at.run()
    assert not at.exception, at.exception
    return at


def choisir(at, sourate=1, verset=2):
    at.selectbox(key="sourate").set_value(sourate).run()
    at.number_input(key=f"verset_{sourate}").set_value(verset).run()


def envoyer_audio(at, octets=None):
    at.file_uploader(key=f"fichier_{at.session_state['compteur']}").set_value(("essai.wav", octets or wav(), "audio/wav")).run()


def analyser(at):
    next(b for b in at.button if b.label == "🔍 Analyser").click().run()
    assert not at.exception, at.exception


def test_recitation_juste_les_deux_moteurs():
    FauxModele.transcriptions = {"tarteel-ai/whisper-base-ar-quran": "الحمد لله رب العالمين",
                                 "openai/whisper-base": "الحمد لله رب العالمون"}
    at = lancer()
    choisir(at)
    envoyer_audio(at)
    analyser(at)
    essais = at.session_state["essais"]
    assert [(e["moteur"], e["type"], e["fausses_alertes"]) for e in essais] == [("tarteel", "juste", 0), ("whisper", "juste", 1)]
    textes = " ".join(m.value for m in at.markdown)
    assert "aucune erreur signalée" in textes and "1 fausse(s) alerte(s)" in textes
    assert at.session_state["compteur"] == 1                        # micro vidé pour l'essai suivant


def test_erreur_volontaire_detectee_ou_masquee():
    """Le modèle spécialisé « entend » le bon verset (erreur masquée) ; le généraliste repère l'oubli."""
    FauxModele.transcriptions = {"tarteel-ai/whisper-base-ar-quran": "الحمد لله رب العالمين",
                                 "openai/whisper-base": "الحمد لله العالمين"}
    at = lancer()
    choisir(at)
    at.button_group(key="mode").set_value("⚠️ Avec erreurs volontaires").run()
    at.button_group(key="mots_1_2").set_value([2]).run()            # « رَبِّ » sera oublié
    envoyer_audio(at)
    analyser(at)
    tarteel, whisper = at.session_state["essais"]
    assert (tarteel["detectees"], tarteel["manquees"]) == (0, 1)
    assert (whisper["detectees"], whisper["manquees"], whisper["fausses_alertes"]) == (1, 0, 0)
    assert any('class="oublie declare"' in m.value for m in at.markdown)


def test_mode_erreurs_sans_erreur_choisie_bloque_l_analyse():
    at = lancer()
    at.button_group(key="mode").set_value("⚠️ Avec erreurs volontaires").run()
    envoyer_audio(at)
    assert next(b for b in at.button if b.label == "🔍 Analyser").disabled
    assert any("au moins une erreur" in i.value for i in at.info)


def test_audio_silencieux_refuse_sans_appeler_les_moteurs():
    at = lancer()
    t = io.BytesIO()
    with wave.open(t, "wb") as w:
        w.setnchannels(1), w.setsampwidth(2), w.setframerate(16000), w.writeframes(b"\x00\x00" * 32000)
    envoyer_audio(at, t.getvalue())
    analyser(at)
    assert any("Je n'entends rien" in e.value for e in at.error)
    assert FauxModele.charges == [] and at.session_state["essais"] == []


def test_moteur_en_panne_n_empeche_pas_l_autre(monkeypatch):
    def creer(modele):
        if "tarteel" in modele:
            raise MO.MoteurIndisponible("téléchargement impossible")
        return FauxModele(modele)
    monkeypatch.setattr(MO, "creer_pipeline", creer)
    FauxModele.transcriptions = {"openai/whisper-base": "الحمد لله رب العالمين"}
    at = lancer()
    choisir(at)
    envoyer_audio(at)
    analyser(at)
    assert [e["moteur"] for e in at.session_state["essais"]] == ["whisper"]


def test_synthese_et_modele_charge_une_seule_fois():
    FauxModele.transcriptions = {"tarteel-ai/whisper-base-ar-quran": "الحمد لله العالمين", "openai/whisper-base": "الحمد لله العالمين"}
    at = lancer()
    choisir(at)
    for _ in range(2):
        envoyer_audio(at)
        analyser(at)
    assert sorted(FauxModele.charges) == ["openai/whisper-base", "tarteel-ai/whisper-base-ar-quran"]   # cache
    vue = at.dataframe[0].value
    assert list(vue["Essais"]) == [2, 2] and list(vue["Fausses alertes (récitations justes)"]) == ["2 sur 2", "2 sur 2"]


def test_reprise_d_une_serie_csv():
    csv = pd.DataFrame([{"date": "2026-11-16 10:00", "sourate": 112, "verset": 1, "moteur": "tarteel", "type": "erreurs",
                         "erreurs_declarees": 2, "detectees": 1, "manquees": 1, "fausses_alertes": 0,
                         "transcription": "قل هو الله", "duree_audio_s": 2.0, "temps_calcul_s": 1.2}]).to_csv(index=False)
    at = lancer()
    at.sidebar.file_uploader(key="reprise").set_value(("serie.csv", csv.encode(), "text/csv")).run()
    assert not at.exception, at.exception
    assert len(at.session_state["essais"]) == 1
    assert at.dataframe[0].value.iloc[0]["Taux de détection"] == "50 %"
