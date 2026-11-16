"""Vérifie la normalisation sur tout le Coran : écriture uthmanie (data/coran.json) contre orthographe courante.

Données de comparaison : paquet npm quran-validator (MIT), fichier data/quran-verses.min.json (champ textSimple,
source QUL). Usage :
    npm pack quran-validator@1.3.0 && tar xzf quran-validator-1.3.0.tgz
    python outils/valider_normalisation.py package/data/quran-verses.min.json

Résultat de référence (16/11/2026) : 88 écarts sur 77 420 mots, presque tous dus aux hamzas que ce jeu de
données écrit sans hamza (ايتوا pour ائتوا), ce que ne font pas les moteurs de reconnaissance.
"""

import collections
import json
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE))
import alignement as A  # noqa: E402

simple = json.load(open(sys.argv[1]))
coran = json.load(open(RACINE / "data" / "coran.json"))
ecarts, exemples, nb_mots, versets = collections.Counter(), {}, 0, 0
for v in simple:
    a = A.analyser(coran[v["surah"] - 1]["versets"][v["ayah"] - 1]["texte"], v["textSimple"])
    nb_mots += len(a.attendus)
    versets += not a.juste
    for e in a.ecarts:
        k = (e.type, e.attendu, e.entendu)
        ecarts[k] += 1
        exemples.setdefault(k, f'{v["surah"]}:{v["ayah"]}')
print(f"Versets en écart : {versets}/{len(simple)} ; écarts : {sum(ecarts.values())} sur {nb_mots} mots")
for k, n in ecarts.most_common(30):
    print(n, k, exemples[k])
