"""Banc d'essai : la reconnaissance vocale repère-t-elle les erreurs de récitation d'un verset ?

On récite un verset juste, ou avec des erreurs volontaires déclarées à l'avance ; un ou plusieurs moteurs
transcrivent ; l'app compare mot à mot au texte officiel et compte les erreurs détectées, manquées et les
fausses alertes. Rien n'est conservé : l'audio reste en mémoire le temps de l'analyse, et les résultats ne vivent
que dans la session (à télécharger en CSV).
"""

from __future__ import annotations

import base64
import html
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

import alignement as A
import audio as AU
import coran as C
import moteurs as MO

st.set_page_config(page_title="Banc d'essai — récitation", page_icon="🎙️", layout="centered")

# Police Amiri Quran (licence OFL) embarquée : elle affiche correctement tous les signes coraniques, même sans
# accès à Google Fonts ; les polices système en oublient certains (sukun coranique, petits wâw et yâ…).
_POLICE = base64.b64encode((Path(__file__).resolve().parent / "polices" / "amiri-quran-arabic-400-normal.woff2").read_bytes()).decode()

st.markdown(
    """
<style>
@font-face { font-family: 'Amiri Quran'; font-display: swap;
             src: url(data:font/woff2;base64,__POLICE__) format('woff2'); }
.verset { font-family: 'Amiri Quran', 'Amiri', serif; direction: rtl; text-align: right; font-size: 2rem;
          line-height: 2.8; color: inherit; }
.verset span { padding: 0 .15em; border-radius: .3em; }
.verset .oublie   { background: #fecaca; color: #111; text-decoration: line-through; }
.verset .remplace { background: #fed7aa; color: #111; }
.verset .deplace  { background: #bfdbfe; color: #111; }
.verset .declare  { border-bottom: 3px dotted #7c3aed; }
.legende span { display: inline-block; padding: 0 .5em; border-radius: .3em; margin-right: .4em; color: #111; }
.arabe { font-family: 'Amiri Quran', 'Amiri', serif; direction: rtl; text-align: right; font-size: 1.4rem; }
.st-key-choix_mots [data-testid="stButtonGroup"] { direction: rtl; }
.st-key-choix_mots button { height: auto; min-height: 3.4rem; padding: .2rem .9rem; overflow: visible; }
.st-key-choix_mots button p { font-family: 'Amiri Quran', 'Amiri', serif; font-size: 1.3rem; line-height: 2.4;
                              overflow: visible; white-space: nowrap; }
</style>
""".replace("__POLICE__", _POLICE),
    unsafe_allow_html=True,
)

TYPE_JUSTE, TYPE_ERREURS = "✅ Récitation juste", "⚠️ Avec erreurs volontaires"
LIBELLES = {"oublie": "oublié", "remplace": "remplacé", "deplace": "déplacé"}


@st.cache_resource(show_spinner=False)
def pipeline_de(modele: str):
    return MO.creer_pipeline(modele)


def etat():
    st.session_state.setdefault("essais", [])
    st.session_state.setdefault("compteur", 0)
    st.session_state.setdefault("dernier", None)


# ───────────── Affichage d'une analyse ─────────────

def verset_colore(analyse: A.Analyse, declares: set[int]) -> str:
    morceaux = []
    for i, mot in enumerate(analyse.attendus):
        e = analyse.etat_mot(i)
        classes = ([e.type] if e else []) + (["declare"] if i in declares else [])
        titre = f' title="entendu : {html.escape(e.entendu)}"' if e and e.entendu else ""
        morceaux.append(f'<span class="{" ".join(classes)}"{titre}>{html.escape(mot)}</span>')
    return f'<div class="verset">{" ".join(morceaux)}</div>'


def phrase_verdict(r: dict) -> str:
    if r["erreurs_declarees"] == 0:
        if r["fausses_alertes"] == 0:
            return "✅ Récitation juste, et aucune erreur signalée : correct."
        return f"⚠️ Récitation juste, mais **{r['fausses_alertes']} fausse(s) alerte(s)**."
    texte = f"**{r['detectees']} erreur(s) détectée(s) sur {r['erreurs_declarees']}**"
    if r["manquees"]:
        texte += f" · {r['manquees']} manquée(s)"
    if r["fausses_alertes"]:
        texte += f" · {r['fausses_alertes']} fausse(s) alerte(s)"
    return ("✅ " if r["manquees"] == 0 and r["fausses_alertes"] == 0 else "⚠️ ") + texte


def afficher_resultat(r: dict, analyse: A.Analyse, declares: set[int]):
    st.markdown(f"#### {MO.MOTEURS[r['moteur']].nom} · {r['temps_calcul_s']:.1f} s")
    st.markdown(phrase_verdict(r))
    st.markdown(verset_colore(analyse, declares), unsafe_allow_html=True)
    ajoutes = [e.entendu for e in analyse.ecarts if e.type == "ajoute"]
    if ajoutes:
        st.markdown(f'Mots en plus entendus : <span class="arabe">{html.escape(" · ".join(ajoutes))}</span>',
                    unsafe_allow_html=True)
    with st.expander("Transcription du moteur"):
        st.markdown(f'<div class="arabe">{html.escape(r["transcription"]) or "(rien)"}</div>', unsafe_allow_html=True)


def legende():
    st.markdown(
        '<div class="legende"><span style="background:#fecaca">oublié</span><span style="background:#fed7aa">'
        'remplacé</span><span style="background:#bfdbfe">déplacé</span>'
        '<span style="border-bottom:3px dotted #7c3aed">erreur que tu as déclarée</span></div>',
        unsafe_allow_html=True,
    )


# ───────────── Onglet : tester un verset ─────────────

def onglet_test(moteurs_choisis: list[str]):
    c1, c2 = st.columns([3, 1])
    s = c1.selectbox("Sourate", range(1, 115), format_func=lambda n: C.libelle_sourate(C.sourate(n)), key="sourate")
    nb = len(C.sourate(s)["versets"])
    v = c2.number_input("Verset", 1, nb, 1, key=f"verset_{s}")
    verset = C.verset(s, v)
    mots = A.mots(verset["texte"])
    st.markdown(f'<div class="verset">{html.escape(verset["texte"])}</div>', unsafe_allow_html=True)
    st.caption(f"Traduction (Hamidullah) : {verset['fr']}")
    st.audio(C.url_audio_reference(s, v))
    st.caption("Récitation de référence : Mishary Alafasy (everyayah.com).")

    st.subheader("1. Ce que tu vas réciter")
    mode = st.segmented_control("Type d'essai", [TYPE_JUSTE, TYPE_ERREURS], default=TYPE_JUSTE, key="mode") or TYPE_JUSTE
    declares, ajouts = set(), 0
    if mode == TYPE_ERREURS:
        with st.container(key="choix_mots"):
            choix = st.pills("Mots que tu vas oublier, remplacer ou déplacer", list(range(len(mots))),
                             format_func=lambda i: mots[i], selection_mode="multi", key=f"mots_{s}_{v}")
        declares = set(choix or [])
        ajouts = st.number_input("Mots que tu vas ajouter", 0, 5, 0, key=f"ajouts_{s}_{v}")
        st.caption("Pour inverser deux mots, sélectionne seulement le mot que tu déplaces.")
    sans_erreur_choisie = mode == TYPE_ERREURS and not declares and not ajouts
    if sans_erreur_choisie:
        st.info("Choisis au moins une erreur à faire, puis enregistre-toi.")

    st.subheader("2. Enregistre-toi")
    n = st.session_state.compteur
    micro = st.audio_input("Récite le verset", key=f"micro_{n}")
    with st.expander("…ou envoie un fichier audio"):
        fichier = st.file_uploader("Fichier audio", type=["wav", "mp3", "m4a", "ogg", "webm", "aac"], key=f"fichier_{n}")
    source = micro or fichier

    st.subheader("3. Analyse")
    if not moteurs_choisis:
        st.warning("Choisis au moins un moteur dans le panneau de gauche.")
    if st.button("🔍 Analyser", type="primary", use_container_width=True,
                 disabled=source is None or not moteurs_choisis or sans_erreur_choisie):
        analyser(source.getvalue(), s, v, verset["texte"], declares, int(ajouts), moteurs_choisis)

    dernier = st.session_state.dernier
    if dernier and dernier["ref"] == (s, v):
        st.divider()
        legende()
        for r in dernier["resultats"]:
            afficher_resultat(r, A.analyser(verset["texte"], r["transcription"]), set(dernier["declares"]))


def analyser(octets: bytes, s: int, v: int, texte: str, declares: set[int], ajouts: int, moteurs_choisis: list[str]):
    try:
        x = AU.preparer(octets)
    except AU.AudioInvalide as ex:
        st.error(str(ex))
        return
    del octets  # l'enregistrement n'est jamais conservé
    resultats = []
    for cle in moteurs_choisis:
        m = MO.MOTEURS[cle]
        with st.spinner(f"{m.nom} : chargement du modèle (la première fois, environ une minute), puis écoute…"):
            try:
                t = MO.transcrire(pipeline_de(m.modele), x)
            except MO.MoteurIndisponible as ex:
                st.error(f"{m.nom} : {ex}")
                continue
        verdict = A.comparer(A.analyser(texte, t.texte), declares, ajouts)
        resultats.append({
            "date": datetime.now().strftime("%Y-%m-%d %H:%M"), "sourate": s, "verset": v, "moteur": cle,
            "type": "erreurs" if verdict.erreurs_declarees else "juste",
            "erreurs_declarees": verdict.erreurs_declarees, "detectees": verdict.detectees,
            "manquees": verdict.manquees, "fausses_alertes": verdict.fausses_alertes,
            "transcription": t.texte, "duree_audio_s": round(AU.duree(x), 1), "temps_calcul_s": round(t.secondes, 1),
        })
    if resultats:
        st.session_state.essais.extend(resultats)
        st.session_state.dernier = {"ref": (s, v), "resultats": resultats, "declares": sorted(declares)}
        st.session_state.compteur += 1   # micro vidé pour l'essai suivant
        st.rerun()


# ───────────── Onglet : résultats ─────────────

def synthese(essais: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(essais)
    lignes = []
    for cle, g in df.groupby("moteur", sort=False):
        justes, erreurs = g[g["erreurs_declarees"] == 0], g[g["erreurs_declarees"] > 0]
        declarees = int(g["erreurs_declarees"].sum())
        lignes.append({
            "Moteur": MO.MOTEURS[cle].nom if cle in MO.MOTEURS else cle,
            "Essais": len(g),
            "Erreurs détectées": f"{int(g['detectees'].sum())} / {declarees}" if declarees else "—",
            "Taux de détection": f"{round(100 * g['detectees'].sum() / declarees)} %" if declarees else "—",
            "Fausses alertes (récitations justes)": (
                f"{int((justes['fausses_alertes'] > 0).sum())} sur {len(justes)}" if len(justes) else "—"),
            "Fausses alertes (essais avec erreurs)": int(erreurs["fausses_alertes"].sum()) if len(erreurs) else "—",
            "Temps moyen": f"{g['temps_calcul_s'].mean():.1f} s",
        })
    return pd.DataFrame(lignes)


def onglet_resultats():
    essais = st.session_state.essais
    if not essais:
        st.info("Aucun essai pour l'instant. Fais quelques essais dans l'onglet « Tester un verset ».")
        return
    st.dataframe(synthese(essais), hide_index=True, use_container_width=True)
    st.caption("Repère proposé : un moteur utilisable détecte au moins 8 erreurs sur 10 et donne une fausse alerte "
               "sur moins de 2 récitations justes sur 10. Fais au moins 20 essais (10 justes, 10 avec erreurs) "
               "avant de conclure, si possible avec plusieurs voix.")
    st.dataframe(pd.DataFrame(essais), hide_index=True, use_container_width=True)


# ───────────── Panneau ─────────────

def panneau() -> list[str]:
    with st.sidebar:
        st.title("🎙️ Banc d'essai")
        st.caption("Reconnaissance de récitation du Coran : quelles erreurs sont repérées ?")
        choisis = st.multiselect("Moteurs à comparer", list(MO.MOTEURS), default=list(MO.MOTEURS),
                                 format_func=lambda k: MO.MOTEURS[k].nom)
        for k in choisis:
            st.caption(f"**{MO.MOTEURS[k].nom}** : {MO.MOTEURS[k].description}")
        st.divider()
        essais = st.session_state.essais
        st.metric("Essais dans cette session", len(essais))
        if essais:
            st.download_button("⬇️ Télécharger les résultats (CSV)", pd.DataFrame(essais).to_csv(index=False).encode(),
                               file_name="banc_essai_recitation.csv", mime="text/csv", use_container_width=True)
        reprise = st.file_uploader("Reprendre une série (CSV)", type=["csv"], key="reprise")
        if reprise is not None and st.session_state.get("_reprise_id") != reprise.file_id:
            try:
                lus = pd.read_csv(reprise).to_dict("records")
                st.session_state.essais = lus + [e for e in essais if e not in lus]
                st.session_state["_reprise_id"] = reprise.file_id
                st.rerun()
            except Exception:
                st.error("Ce fichier n'est pas un CSV de résultats du banc d'essai.")
        if essais and st.button("🗑️ Effacer les résultats", use_container_width=True):
            st.session_state.essais, st.session_state.dernier = [], None
            st.rerun()
        st.divider()
        st.caption("🔒 Les enregistrements ne sont jamais conservés : ils sont analysés en mémoire puis oubliés.")
    return choisis


def mode_emploi():
    st.markdown(
        """
**But** : savoir si la reconnaissance vocale repère vraiment les erreurs de récitation, avant de construire l'application
pour les élèves. Un modèle spécialisé dans le Coran reconnaît bien la récitation, mais il peut aussi « entendre » le bon
verset quand on se trompe : c'est ce qu'on mesure.

1. Choisis une sourate et un verset ; écoute la récitation de référence si besoin.
2. Indique si tu vas le réciter **juste** ou **avec des erreurs volontaires** (choisis les mots que tu vas oublier,
   remplacer ou déplacer, et combien de mots tu vas ajouter).
3. Enregistre-toi avec le micro, puis clique sur **Analyser**.
4. Regarde ce que chaque moteur a repéré, puis recommence avec d'autres versets.
5. L'onglet **Résultats** fait le bilan. Télécharge le CSV pour le garder ou continuer plus tard.

**Conseils** : environ 10 récitations justes et 10 avec erreurs ; varie les versets (courts, longs) et, si possible,
les voix (adulte, ado). Les erreurs de voyelles et de tajwid ne sont pas mesurées ici : seulement les mots.
"""
    )


def main():
    etat()
    choisis = panneau()
    t1, t2, t3 = st.tabs(["🎙️ Tester un verset", "📊 Résultats", "ℹ️ Mode d'emploi"])
    with t1:
        onglet_test(choisis)
    with t2:
        onglet_resultats()
    with t3:
        mode_emploi()


main()
