"""Comparaison mot à mot : écriture uthmanie (texte officiel) contre transcription en orthographe courante."""

import pytest

import alignement as A
import coran

FATIHA_2 = "الحمد لله رب العالمين"
BAQARA_3 = "الذين يؤمنون بالغيب ويقيمون الصلاة ومما رزقناهم ينفقون"


def texte(s, v):
    return coran.verset(s, v)["texte"]


@pytest.mark.parametrize("ref, transcription", [
    ((1, 1), "بسم الله الرحمن الرحيم"),
    ((1, 2), FATIHA_2),
    ((1, 2), "الْحَمْدُ لِلَّهِ رَبِّ الْعَالَمِينَ"),                  # avec voyelles
    ((1, 7), "صراط الذين أنعمت عليهم غير المغضوب عليهم ولا الضالين"),
    ((2, 3), BAQARA_3),                                                 # الصلاة / ٱلصَّلَوٰةَ
    ((2, 21), "يا أيها الناس اعبدوا ربكم الذي خلقكم والذين من قبلكم لعلكم تتقون"),   # vocatif séparé
    ((2, 5), "أولئك على هدى من ربهم وأولئك هم المفلحون"),               # hamza sur yâ, alef maqsûra
    ((2, 164), "إن في خلق السماوات والأرض واختلاف الليل والنهار والفلك التي تجري في البحر بما ينفع الناس وما أنزل الله من السماء من ماء فأحيا به الأرض بعد موتها وبث فيها من كل دابة وتصريف الرياح والسحاب المسخر بين السماء والأرض لآيات لقوم يعقلون"),
    ((2, 255), "الله لا إله إلا هو الحي القيوم لا تأخذه سنة ولا نوم له ما في السماوات وما في الأرض من ذا الذي يشفع عنده إلا بإذنه يعلم ما بين أيديهم وما خلفهم ولا يحيطون بشيء من علمه إلا بما شاء وسع كرسيه السماوات والأرض ولا يئوده حفظهما وهو العلي العظيم"),
    ((20, 9), "وهل أتاك حديث موسى"),
    ((2, 251), "فهزموهم بإذن الله وقتل داوود جالوت وآتاه الله الملك والحكمة وعلمه مما يشاء ولولا دفع الله الناس بعضهم ببعض لفسدت الأرض ولكن الله ذو فضل على العالمين"),
    ((112, 4), "ولم يكن له كفوا أحد"),
])
def test_recitation_juste_sans_alerte(ref, transcription):
    a = A.analyser(texte(*ref), transcription)
    assert a.juste, [(e.type, e.attendu, e.entendu) for e in a.ecarts]


def test_mot_oublie():
    a = A.analyser(texte(1, 2), "الحمد لله العالمين")
    assert [(e.type, e.indice) for e in a.ecarts] == [("oublie", 2)]
    assert A.squelette(a.ecarts[0].attendu) == A.squelette("رب")


def test_mot_remplace():
    a = A.analyser(texte(2, 3), "الذين يؤمنون بالغيب ويقيمون الصلاة ومما رزقناهم يعملون")
    assert [(e.type, e.indice, e.entendu) for e in a.ecarts] == [("remplace", 7, "يعملون")]


def test_mot_ajoute():
    a = A.analyser(texte(1, 2), "الحمد لله رب العالمين جميعا")
    assert [(e.type, e.indice, e.entendu) for e in a.ecarts] == [("ajoute", None, "جميعا")]
    assert a.nb_ajouts == 1 and a.indices_signales == set()


def test_mots_inverses_signales_comme_deplaces():
    a = A.analyser(texte(1, 1), "بسم الله الرحيم الرحمن")
    assert [e.type for e in a.ecarts] == ["deplace"] and a.indices_signales <= {2, 3}


def test_lettre_initiale_differente_est_une_erreur():
    """تعلمون récité à la place de يعلمون : un autre mot, même si une seule lettre change."""
    assert A.cle("يعلمون") != A.cle("تعلمون")
    assert A.cle("العالمين") != A.cle("العالمون")
    a = A.analyser(texte(1, 2), "الحمد لله رب العالمون")
    assert [(e.type, e.indice) for e in a.ecarts] == [("remplace", 3)]


def test_fin_de_verset_oubliee():
    a = A.analyser(texte(1, 7), "صراط الذين أنعمت عليهم")
    assert {e.type for e in a.ecarts} == {"oublie"} and a.indices_signales == {4, 5, 6, 7, 8}


def test_signes_isoles_ne_sont_pas_des_mots():
    assert A.mots("۞ إِنَّ ٱللَّهَ ۚ") == ["إِنَّ", "ٱللَّهَ"]


def test_transcription_vide_tout_oublie():
    a = A.analyser(texte(112, 1), "")
    assert len(a.ecarts) == len(a.attendus) == 4


# ───────────── Mesure du banc d'essai ─────────────

def test_verdict_erreur_declaree_detectee():
    a = A.analyser(texte(1, 2), "الحمد لله العالمين")
    v = A.comparer(a, {2})
    assert (v.erreurs_declarees, v.detectees, v.fausses_alertes, v.manquees) == (1, 1, 0, 0)


def test_verdict_erreur_manquee_par_le_moteur():
    """Le moteur « corrige » l'élève : il transcrit le bon verset alors qu'un mot a été oublié."""
    a = A.analyser(texte(1, 2), FATIHA_2)
    v = A.comparer(a, {2})
    assert (v.detectees, v.manquees, v.fausses_alertes) == (0, 1, 0)


def test_verdict_fausse_alerte_sur_recitation_juste():
    a = A.analyser(texte(1, 2), "الحمد لله رب العالمون")
    v = A.comparer(a, set())
    assert (v.erreurs_declarees, v.fausses_alertes) == (0, 1)


def test_verdict_ajout_declare():
    a = A.analyser(texte(1, 2), "الحمد لله رب العالمين جميعا")
    assert A.comparer(a, set(), ajouts_declares=1).detectees == 1
