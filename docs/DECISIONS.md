# Décisions — Tuteur Coran

Agent pour aider des adolescents à apprendre le Coran : pour chaque verset à apprendre, l'élève s'enregistre et
l'on indique s'il y a une erreur.

| # | Question | Décision |
|---|----------|----------|
| 1 | Qui indique l'erreur ? | **L'IA puis l'enseignant** : l'IA signale tout de suite les erreurs probables ; l'enseignant écoute, confirme ou corrige. L'enseignant reste le juge. |
| 2 | Quelles erreurs ? | **Les mots** : oubliés, ajoutés, remplacés, déplacés, versets sautés. Ni les voyelles ni le tajwid (détection automatique pas assez fiable aujourd'hui). |
| 3 | Forme | **Application web Streamlit**, utilisable sur téléphone (micro du navigateur). |
| 4 | Enregistrements | **Gardés jusqu'à la correction** par l'enseignant, puis supprimés (au plus tard après 30 jours). Seul le résultat reste. |
| 5 | Texte du Coran | **Embarqué, jamais produit par une IA** : texte uthmani de The Noble Qur'an Encyclopedia (paquet quran-json, CC BY-SA 4.0). |
| 6 | Première étape | **Banc d'essai** : mesurer si la reconnaissance vocale repère vraiment les erreurs (risque : un modèle spécialisé « entend » le bon verset quand l'élève se trompe) avant de construire l'application. |

## Comparaison mot à mot

Le texte officiel est en écriture uthmanie, les moteurs écrivent en orthographe courante. On compare des clés de
mots (`alignement.cle`) : sans voyelles ni signes coraniques, hamzas unifiées, sans alef, sans yâ/wâw à
l'intérieur du mot, sans lettre doublée ; vocatif « يا » rattaché au mot suivant. On garde la première lettre et
les terminaisons ـين / ـون, pour distinguer يعلمون de تعلمون et العالمين de العالمون.

Validation sur tout le Coran (`outils/valider_normalisation.py`, orthographe courante de QUL) : 205 écarts sur
77 420 mots, presque tous des hamzas que ce jeu de données écrit sans hamza (لين pour لئن). Choix assumé : des mots
qui ne diffèrent que par une voyelle longue (قال / قيل) ont la même clé.
