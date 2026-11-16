# Tuteur Coran — banc d'essai de la reconnaissance de récitation

Première étape du projet (voir `docs/DECISIONS.md`) : vérifier qu'une IA de reconnaissance vocale repère vraiment
les erreurs de récitation **au niveau des mots** (mot oublié, ajouté, remplacé, déplacé) avant de construire
l'application pour les élèves et l'espace enseignant.

## Ce que fait le banc d'essai

1. On choisit un verset (texte uthmani embarqué, traduction de Hamidullah, récitation de référence d'Alafasy).
2. On déclare si on va le réciter juste, ou avec des erreurs volontaires (mots choisis à l'avance).
3. On s'enregistre avec le micro du téléphone ou de l'ordinateur.
4. Deux moteurs transcrivent, et l'app compare mot à mot au texte officiel :
   - **Spécialisé Coran** : [`tarteel-ai/whisper-base-ar-quran`](https://huggingface.co/tarteel-ai/whisper-base-ar-quran) (Apache-2.0)
   - **Généraliste** : [`openai/whisper-base`](https://huggingface.co/openai/whisper-base) (MIT)
5. L'onglet Résultats calcule, par moteur, le taux d'erreurs détectées et les fausses alertes. Export CSV.

Les enregistrements ne sont **jamais conservés** : analysés en mémoire, puis oubliés. Les résultats restent dans la
session (télécharger le CSV pour les garder).

## Déployer sur Streamlit Cloud

1. https://share.streamlit.io → **Create app** → dépôt `tuteur_coran`, branche `main`, fichier `app.py`.
2. **Advanced settings** → Python **3.12**. Aucun secret nécessaire.
3. Premier lancement : quelques minutes (installation de PyTorch). Première analyse : environ une minute par moteur
   (téléchargement des modèles, ~300 Mo chacun), ensuite quelques secondes.

## Développement

```
pip install -r requirements.txt
python -m pytest            # tests (moteurs simulés)
streamlit run app.py
```

```
app.py          # Interface du banc d'essai
alignement.py   # Comparaison mot à mot uthmani / orthographe courante, mesure des détections
audio.py        # Micro ou fichier → mono 16 kHz (ffmpeg pour MP3/M4A…)
moteurs.py      # Moteurs de reconnaissance (Hugging Face transformers, CPU)
coran.py        # Accès au texte embarqué
data/coran.json # 114 sourates, 6 236 versets
polices/        # Amiri Quran (OFL) : affiche tous les signes coraniques
outils/         # Validation de la normalisation sur tout le Coran
```

## Sources et licences

- Texte uthmani : The Noble Qur'an Encyclopedia (quranenc.com), via le paquet npm `quran-json` 3.1.2 (CC BY-SA 4.0).
- Traduction française : Muhammad Hamidullah (tanzil.net), via le même paquet.
- Récitation de référence : Mishary Alafasy, servie par everyayah.com (lue directement par le navigateur).
- Police : Amiri Quran (SIL Open Font License 1.1), via `@fontsource/amiri-quran`.
