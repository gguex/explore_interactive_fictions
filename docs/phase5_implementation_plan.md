# Phase 5 — Découpage des scripts et échanges avec le cluster

> **Statut au 26.08.2026 : étapes 5.0 et 5.1 implémentées et validées ; étapes 5.2–5.5 à créer.**
> Le protocole scientifique reste défini dans `docs/phase5_protocol.md`. Cette note décrit
> les étapes techniques et les fichiers qui circuleront entre la machine locale et le
> serveur universitaire.

## 1. Principe général

```text
matrices et textes locaux
        ↓
5.0 échantillonner et sélectionner les médoïdes conditionnels
        ↓
5.1 reconstruire les histoires et préparer l'annotation humaine
        ↓
5.2 construire un paquet aveugle et autonome
        ↓ upload
exécuter Qwen3.6-27B sur le cluster
        ↓ download
5.3 importer et valider les sorties
        ↓
5.4 calculer les résultats de phase 5
        ↓
5.5 produire la diapositive et les tableaux
```

Les données cachées — profil générateur, probabilités, indices BoP et annotations
humaines — restent locales. Le cluster reçoit uniquement les histoires, les identifiants
opaques, les prompts, les schémas et les paramètres nécessaires à l'inférence.

## 2. Scripts locaux proposés

| Script | Rôle | Entrées principales | Sorties principales |
| :--- | :--- | :--- | :--- |
| `scripts/5.0_select_medoid_trajectories.py` — **fait** | Tirer 2 000 trajectoires conditionnelles par cellule avec la transformation de Doob et sélectionner le chemin observé minimisant la distance LCS moyenne. | Matrices, multiarêtes compilées, profils et probabilités d'absorption. | `medoid_trajectories.jsonl`, `conditional_path_counts.jsonl` et `medoid_selection_report.json`. |
| `scripts/5.1_build_trajectory_corpus.py` — **fait** | Reconstituer chaque histoire complète avec paragraphes, choix disponibles, choix suivi et type de transition ; former les six paires dans les deux ordres. | Médoïdes, nœuds, arêtes originales et compilées, métriques BoP. | Corpus aveugle, métadonnées privées, paires A/B et B/A, gabarits humains, distances structurelles et rapport. |
| `scripts/5.2_build_phase5_bundle.py` | Produire un paquet autonome sans fuite des profils ou résultats BoP. | Corpus, prompts figés, schémas et configuration du modèle. | Paquet `pilot` ou `final` avec manifeste et empreintes. |
| `scripts/5.3_import_phase5_annotations.py` | Importer les sorties revenues du cluster, contrôler les schémas et normaliser les résultats valides. | Dossier de sortie du cluster et manifeste du paquet. | Annotations canoniques, quarantaine et rapport de validation. |
| `scripts/5.4_compute_phase5_results.py` | Réunir annotations Qwen, métadonnées cachées, annotations humaines et distances structurelles ; calculer les indicateurs. | Sorties 5.0–5.3 et fichiers humains. | Tables individuelles, pairwise, qualité et synthèse. |
| `scripts/5.5_build_phase5_presentation.py` | Extraire uniquement les résultats stables et produire les supports présentables. | Tables canoniques de 5.4. | Figures PNG/SVG, tableau de chiffres clés et manifeste. |

Chaque script doit relire les fichiers de l'étape précédente plutôt que réimplémenter son
calcul. Les validateurs indépendants suivent les conventions existantes :

```text
scripts/tests/test_5_0_select_medoid_trajectories.py
scripts/tests/test_5_1_build_trajectory_corpus.py  # fait
scripts/tests/test_5_2_build_phase5_bundle.py
scripts/tests/test_5_3_import_phase5_annotations.py
scripts/tests/test_5_4_compute_phase5_results.py
scripts/tests/test_5_5_build_phase5_presentation.py
```

## 3. Étape humaine et calibration

`5.1` produit deux gabarits ciblés dans `data/for_trajectory_annotation/LW01/` :

- `human_trajectory_annotations.jsonl` pour `T0001`, `T0004`, `T0009` et `T0014` ;
- `human_pairwise_annotations.jsonl` pour `C002`, `C003` et `C006`.

Il produit aussi `TRAJECTORIES_FOR_ANNOTATION.md`, une annexe aveugle et lisible contenant
uniquement les sept histoires qu'il faut lire : les quatre histoires annotées
individuellement et `T0006`, `T0007`, `T0012`, nécessaires comme seconds membres des
trois paires. Les paragraphes, choix, actions suivies et références y sont mis en page.

Les annotations humaines sont remplies avant de consulter Qwen. Il n'existe pas de jeu
humain de validation dans cette itération : les quatre histoires et trois paires servent
uniquement à calibrer la grille et les prompts. Le paquet produit par
`5.2 --stage pilot` contient ces entrées sans leurs réponses humaines.

Les deux fichiers humains sont des artefacts éditables : `5.1` les crée s'ils n'existent
pas, puis vérifie leurs identifiants sans jamais écraser des annotations déjà remplies.

Après examen du pilote, le codebook et les prompts sont figés et empreintés. Le paquet
`final` contient alors :

- 14 annotations individuelles ;
- six comparaisons A/B ;
- six comparaisons B/A.

Les dix histoires individuelles et trois paires sans annotation humaine ne sont pas
appelées « validation ». Les résultats complets restent exploratoires ; les comparaisons
avec l'humain sont des concordances de calibration.

## 4. Fichiers envoyés au serveur

`5.2` matérialise un seul dossier transférable :

```text
data/for_trajectory_annotation/LW01/server_bundle/<RUN_ID>/
├── bundle_manifest.json
├── run_phase5.py
├── schemas.py
├── prompts/
│   ├── individual.txt
│   └── pairwise.txt
├── inputs/
│   ├── individual.jsonl
│   ├── pairwise_ab.jsonl
│   └── pairwise_ba.jsonl
└── config/
    └── inference.json
```

Le manifeste contient les empreintes SHA-256, le nombre d'entrées attendu, la version des
schémas et la révision exacte de `Qwen/Qwen3.6-27B`. `inference.json` fixe notamment BF16,
la fenêtre 32k, `temperature=0`, la graine de décodage et l'absence de troncature.

Les identifiants transmis sont opaques (`T0001`, `C001`) et leur correspondance avec les
profils reste dans `trajectory_private_metadata.jsonl`, qui n'est jamais copié dans le
paquet.

## 5. Exécution sur le cluster

Le code source de l'exécuteur sera maintenu dans :

```text
cluster_scripts/phase5/run_phase5.py
cluster_scripts/phase5/schemas.py
cluster_scripts/phase5/prompts/
```

`5.2` copie les versions exactes de ces fichiers dans le paquet pour que chaque run reste
reproductible. `run_phase5.py` charge Qwen une seule fois, exécute tous les jobs du paquet
et applique les sorties structurées vLLM. Il accepte au minimum :

```text
--bundle-dir <DIR>
--output-dir <DIR>
--resume
```

Le mode `--resume` saute uniquement une entrée déjà produite et validée. Les erreurs ne
sont jamais supprimées ni remplacées silencieusement.

## 6. Fichiers récupérés du serveur

Le dossier complet suivant revient sur la machine locale :

```text
outputs/<RUN_ID>/
├── individual.jsonl
├── pairwise_ab.jsonl
├── pairwise_ba.jsonl
├── quarantine.jsonl
└── run_manifest.json
```

`run_manifest.json` consigne le modèle et sa révision, vLLM, le matériel, les paramètres,
les nombres de succès et d'échecs, les durées et les empreintes des entrées et sorties.
Les sorties brutes sont conservées telles quelles ; `5.3` écrit les versions normalisées
ailleurs et ne modifie jamais le retour du cluster.

## 7. Résultats locaux et présentation

Les sorties canoniques sont regroupées sous :

```text
data/processed/phase5/LW01/
├── medoid_trajectories.jsonl
├── conditional_path_counts.jsonl
├── trajectories.jsonl
├── trajectory_private_metadata.jsonl
├── trajectory_pairs.jsonl
├── pair_private_metadata.jsonl
├── medoid_selection_report.json
├── trajectory_corpus_report.json
├── trajectory_annotations.jsonl
├── pairwise_annotations.jsonl
├── pair_structural_metrics.csv
├── human_trajectory_annotations.jsonl
├── human_pairwise_annotations.jsonl
├── phase5_summary.csv
└── phase5_manifest.json
```

Les artefacts présentables sont écrits dans :

```text
results/phase5/LW01/presentation/
├── phase5_slide.png
├── phase5_slide.svg
├── profile_manifestation.png
├── structural_vs_narrative.png
├── key_results.csv
└── presentation_manifest.json
```

`5.5` ne choisit pas automatiquement le résultat le plus spectaculaire. Il applique une
règle fixée : manifestation des trois axes, confrontation structure–impression et une
ligne de calibration/stabilité. `causal_continuity` et `profile_coherence` sont ajoutés seulement si
les contrôles définis dans `docs/phase5_protocol.md` les déclarent suffisamment stables.

## 8. Contrôles bloquants

Le pipeline s'arrête notamment si :

- les 14 médoïdes ou les six paires attendues ne sont pas présents ;
- les effectifs archivés ne totalisent pas 2 000 tirages dans chaque cellule ;
- les tirages ne peuvent pas être régénérés à partir des graines consignées ;
- une trajectoire retenue ne minimise pas la distance LCS moyenne à son échantillon ;
- sa probabilité recomposée ne correspond pas au produit de ses `compiled_weight` ou sa
  probabilité conditionnelle ne correspond pas à $P(\pi)/P(o)$ ;
- plusieurs candidats sont à égalité sans départage canonique consigné ;
- une trajectoire n'atteint pas l'issue demandée ;
- une histoire est tronquée ou dépasse la fenêtre configurée ;
- une donnée cachée apparaît dans le paquet serveur ;
- une empreinte du paquet ou du retour ne correspond pas ;
- un identifiant de preuve n'existe pas dans l'histoire concernée ;
- une sortie manque, ne respecte pas le schéma ou appartient au mauvais prompt ;
- une comparaison A/B n'a pas sa contrepartie B/A.

## 9. Ordre d'implémentation

1. **Fait :** implémenter et valider `5.0`.
2. **Fait :** implémenter et valider `5.1` à partir des 14 médoïdes distincts.
3. Remplir les quatre annotations individuelles et les trois comparaisons humaines de
   calibration à partir des gabarits produits.
4. Créer l'exécuteur du cluster et `5.2`, puis lancer le paquet `pilot`.
5. Figer les prompts après le pilote et produire le paquet `final`.
6. Récupérer les sorties et implémenter `5.3`.
7. Implémenter `5.4` seulement lorsque toutes les annotations sont valides.
8. Construire la diapositive avec `5.5` en dernier.
