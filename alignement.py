"""Comparer mot à mot la récitation transcrite au texte officiel du verset.

Le texte officiel est en écriture uthmanie (avec signes de pause, alef suscrit, alef wasla…) ; les moteurs de
reconnaissance écrivent plutôt en orthographe courante (« العالمين » pour « ٱلۡعَٰلَمِينَ »). On compare donc des
« squelettes » de mots : sans voyelles ni signes coraniques, hamzas et alefs unifiés. Le niveau visé est le MOT
(oublié, ajouté, remplacé, déplacé) : ni les voyelles ni le tajwid ne sont jugés ici.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from difflib import SequenceMatcher

# Les lettres arabes sont écrites par leur code Unicode pour rester lisibles et sans ambiguïté.
ALEF, ALEF_WASLA, ALEF_SUSCRIT, ALEF_MAQSURA = chr(0x0627), chr(0x0671), chr(0x0670), chr(0x0649)
WAW, YA, HA, NOUN, PETIT_YA_SUSCRIT = chr(0x0648), chr(0x064A), chr(0x0647), chr(0x0646), chr(0x06E7)

# Écriture uthmanie → orthographe courante, avant de retirer les signes (ordre important).
_UTHMANI = [
    (WAW + ALEF_SUSCRIT, ALEF),              # ٱلصَّلَوٰةَ → الصلاة
    (ALEF_MAQSURA + ALEF_SUSCRIT, ALEF_MAQSURA),  # مُوسَىٰ, عَلَىٰ → موسى, على
    (ALEF_SUSCRIT, ALEF),                    # ٱلۡعَٰلَمِينَ → العالمين
    (ALEF_WASLA, ALEF),                      # alef wasla
    (PETIT_YA_SUSCRIT, YA),                  # إِبۡرَٰهِـۧمَ → ابراهيم
]
# Hamzas sur alef unifiées ; alef maqsûra, hamza seule et hamzas sur yâ ou wâw retirées (écrites de plusieurs façons).
_LETTRES = str.maketrans(
    {chr(c): ALEF for c in (0x0623, 0x0625, 0x0622, 0x0672, 0x0673)}          # أ إ آ ٲ ٳ
    | {chr(c): "" for c in (0x0649, 0x0621, 0x0624, 0x0626)}                 # ى ء ؤ ئ
    | {chr(0x0629): HA}                                                      # ة → ه
)
# Voyelles, signes coraniques (pause, petits wâw et yâ…), tatweel.
_PLAGES_SIGNES = ((0x0610, 0x061A), (0x064B, 0x065F), (0x06D6, 0x06ED), (0x0640, 0x0640), (0x08D3, 0x08FF))
_SIGNES = re.compile("[" + "".join(f"{chr(a)}-{chr(b)}" for a, b in _PLAGES_SIGNES) + "]")
_HORS_LETTRES = re.compile(f"[^{chr(0x0621)}-{chr(0x064A)}]")


def squelette(mot: str) -> str:
    """Lettres de base d'un mot : sans voyelles ni signes, hamzas unifiées, sans alef (écrit de plusieurs façons)."""
    mot = unicodedata.normalize("NFC", mot)
    for a, b in _UTHMANI:
        mot = mot.replace(a, b)
    mot = _HORS_LETTRES.sub("", _SIGNES.sub("", mot).translate(_LETTRES))
    return mot.replace(ALEF, "")


def cle(mot: str) -> str:
    """Clé de comparaison : le squelette sans lettre doublée (ٱلَّيۡلِ / الليل) ni yâ ou wâw à l'intérieur du mot
    (voyelles longues et sièges de hamza : أولئك / اولايك, داود / داوود). La première et la dernière lettre sont
    gardées, ainsi que les terminaisons ـين / ـون : يعلمون ≠ تعلمون, العالمين ≠ العالمون. Choix assumé : قال et قيل ont la même clé (écart de voyelle, hors du niveau
    « mot » visé ; l'enseignant reste le juge)."""
    sq = squelette(mot)
    fin = 2 if sq.endswith((YA + NOUN, WAW + NOUN)) else 1   # ـين / ـون : marque du cas grammatical, gardée
    if len(sq) > fin + 1:
        sq = sq[0] + re.sub(f"[{YA}{WAW}]", "", sq[1:-fin]) + sq[-fin:]
    return re.sub(r"(.)\1+", r"\1", sq)


def mots(texte: str) -> list[str]:
    """Mots d'un texte. Les signes isolés (۞, une marque de pause seule) ne sont pas des mots, et le vocatif
    « يا » écrit à part (orthographe courante) est rattaché au mot suivant, comme dans l'écriture uthmanie
    (« يا أيها » ↔ « يَٰٓأَيُّهَا »)."""
    brut = [m for m in texte.split() if squelette(m)]
    sortie: list[str] = []
    i = 0
    while i < len(brut):
        if squelette(brut[i]) in (YA, WAW + YA, HA) and i + 1 < len(brut):   # يا, ويا, ها (ها أنتم)
            sortie.append(f"{brut[i]} {brut[i + 1]}")
            i += 2
        else:
            sortie.append(brut[i])
            i += 1
    return sortie


@dataclass
class Ecart:
    type: str             # "oublie", "ajoute", "remplace", "deplace"
    indice: int | None    # position du mot dans le verset (None pour un mot ajouté)
    attendu: str = ""
    entendu: str = ""


@dataclass
class Analyse:
    attendus: list[str]
    entendus: list[str]
    ecarts: list[Ecart] = field(default_factory=list)

    @property
    def indices_signales(self) -> set[int]:
        return {e.indice for e in self.ecarts if e.indice is not None}

    @property
    def nb_ajouts(self) -> int:
        return sum(e.type == "ajoute" for e in self.ecarts)

    @property
    def juste(self) -> bool:
        return not self.ecarts

    def etat_mot(self, i: int) -> Ecart | None:
        return next((e for e in self.ecarts if e.indice == i), None)


def analyser(texte_verset: str, transcription: str) -> Analyse:
    """Aligne la transcription sur le verset et liste les écarts au niveau du mot."""
    attendus, entendus = mots(texte_verset), mots(transcription)
    sa, se = [cle(m) for m in attendus], [cle(m) for m in entendus]
    ecarts: list[Ecart] = []
    for op, i1, i2, j1, j2 in SequenceMatcher(None, sa, se, autojunk=False).get_opcodes():
        if op == "equal":
            continue
        if op == "delete":
            ecarts += [Ecart("oublie", i, attendus[i]) for i in range(i1, i2)]
        elif op == "insert":
            ecarts += [Ecart("ajoute", None, entendu=entendus[j]) for j in range(j1, j2)]
        else:  # replace : on apparie mot à mot, une variante d'orthographe n'est pas une erreur
            n = max(i2 - i1, j2 - j1)
            for k in range(n):
                i, j = i1 + k, j1 + k
                if i < i2 and j < j2:
                    if sa[i] != se[j]:
                        ecarts.append(Ecart("remplace", i, attendus[i], entendus[j]))
                elif i < i2:
                    ecarts.append(Ecart("oublie", i, attendus[i]))
                else:
                    ecarts.append(Ecart("ajoute", None, entendu=entendus[j]))
    return Analyse(attendus, entendus, _deplacements(ecarts, sa))


def _deplacements(ecarts: list[Ecart], sa: list[str]) -> list[Ecart]:
    """Un mot « oublié » ici et « ajouté » ailleurs est un mot déplacé (ordre inversé)."""
    ajouts = [e for e in ecarts if e.type == "ajoute"]
    for e in ecarts:
        if e.type != "oublie":
            continue
        double = next((a for a in ajouts if cle(a.entendu) == sa[e.indice]), None)
        if double:
            e.type, e.entendu = "deplace", double.entendu
            ajouts.remove(double)
            ecarts = [x for x in ecarts if x is not double]
    return ecarts


# ───────────── Mesure du banc d'essai ─────────────

@dataclass
class Verdict:
    erreurs_declarees: int      # mots modifiés volontairement + ajouts déclarés
    detectees: int              # parmi elles, celles que le moteur a signalées
    fausses_alertes: int        # écarts signalés là où l'élève n'a rien changé

    @property
    def manquees(self) -> int:
        return self.erreurs_declarees - self.detectees


def comparer(analyse: Analyse, mots_modifies: set[int], ajouts_declares: int = 0) -> Verdict:
    """Compare ce que le moteur signale à ce que l'élève a réellement fait (déclaré avant d'enregistrer)."""
    signales = analyse.indices_signales
    detectees = len(mots_modifies & signales) + min(ajouts_declares, analyse.nb_ajouts)
    fausses = len(signales - mots_modifies) + max(analyse.nb_ajouts - ajouts_declares, 0)
    return Verdict(len(mots_modifies) + ajouts_declares, detectees, fausses)
