# Phase 5 — Découpage des scripts et échanges avec le cluster

> **Statut au 26.08.2026 : note d'implémentation, scripts à créer.** Le protocole
> scientifique reste défini dans `docs/phase5_protocol.md`. Cette note décrit seulement
> les étapes techniques et les fichiers qui circuleront entre la machine locale et le
> serveur universitaire.

## 1. Principe général

```text
matrices et textes locaux
        ↓
5.0 calculer les trajectoires conditionnelles MAP
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
| `scripts/5.0_compute_map_trajectories.py` | Transformer chaque `compiled_weight` en coût $-\log w(e)$ et calculer les 14 trajectoires MAP, une par profil et par issue. | Tables de multiarêtes compilées, profils, probabilités d'absorption. | Trajectoires, probabilités MAP, métadonnées cachées et rapport de sélection. |
| `scripts/5.1_build_trajectory_corpus.py` | Reconstituer chaque histoire complète avec paragraphes, choix disponibles, choix suivi et type de transition ; former les six paires dans les deux ordres. | Trajectoires, nœuds, arêtes et textes. | Corpus individuel, corpus pairwise, gabarits humains et mesures de longueur. |
| `scripts/5.2_build_phase5_bundle.py` | Produire un paquet autonome sans fuite des profils ou résultats BoP. | Corpus, prompts figés, schémas et configuration du modèle. | Paquet `pilot` ou `final` avec manifeste et empreintes. |
| `scripts/5.3_import_phase5_annotations.py` | Importer les sorties revenues du cluster, contrôler les schémas et normaliser les résultats valides. | Dossier de sortie du cluster et manifeste du paquet. | Annotations canoniques, quarantaine et rapport de validation. |
| `scripts/5.4_compute_phase5_results.py` | Réunir annotations Qwen, métadonnées cachées, annotations humaines et distances structurelles ; calculer les indicateurs. | Sorties 5.0–5.3 et fichiers humains. | Tables individuelles, pairwise, qualité et synthèse. |
| `scripts/5.5_build_phase5_presentation.py` | Extraire uniquement les résultats stables et produire les supports présentables. | Tables canoniques de 5.4. | Figures PNG/SVG, tableau de chiffres clés et manifeste. |

Chaque script doit relire les fichiers de l'étape précédente plutôt que réimplémenter son
calcul. Les validateurs indépendants suivent les conventions existantes :

```text
scripts/tests/test_5_0_compute_map_trajectories.py
scripts/tests/test_5_1_build_trajectory_corpus.py
scripts/tests/test_5_2_build_phase5_bundle.py
scripts/tests/test_5_3_import_phase5_annotations.py
scripts/tests/test_5_4_compute_phase5_results.py
scripts/tests/test_5_5_build_phase5_presentation.py
```

## 3. Étape humaine et calibration

`5.1` produit deux gabarits dans `data/for_trajectory_annotation/LW01/` :

- `human_trajectory_annotations.jsonl` pour les 14 histoires sélectionnées ;
- `human_pairwise_annotations.jsonl` pour les six paires.

Les annotations humaines sont remplies avant de consulter Qwen. Quatre histoires sont
marquées `calibration` et dix `validation`. Le premier paquet produit par
`5.2 --stage pilot` ne contient que les quatre histoires de calibration, sans leurs
réponses humaines.

Après examen du pilote, le codebook et les prompts sont figés et empreintés. Le paquet
`final` contient alors :

- 14 annotations individuelles primaires ;
- 14 annotations individuelles avec la variante prédéfinie du prompt ;
- six comparaisons A/B ;
- six comparaisons B/A.

## 4. Fichiers envoyés au serveur

`5.2` matérialise un seul dossier transférable :

```text
data/for_trajectory_annotation/LW01/server_bundle/<RUN_ID>/
├── bundle_manifest.json
├── run_phase5.py
├── schemas.py
├── prompts/
│   ├── individual_primary.txt
│   ├── individual_variant.txt
│   └── pairwise.txt
├── inputs/
│   ├── individual_primary.jsonl
│   ├── individual_variant.jsonl
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
├── individual_primary.jsonl
├── individual_variant.jsonl
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
├── trajectories.jsonl
├── trajectory_private_metadata.jsonl
├── map_selection_report.json
├── trajectory_annotations.jsonl
├── pairwise_annotations.jsonl
├── pair_structural_metrics.csv
├── human_annotations.jsonl
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
ligne de validation. `causal_continuity` et `profile_coherence` sont ajoutés seulement si
les contrôles définis dans `docs/phase5_protocol.md` les déclarent suffisamment stables.

## 8. Contrôles bloquants

Le pipeline s'arrête notamment si :

- les 14 trajectoires MAP ou les six paires attendues ne sont pas présentes ;
- une trajectoire n'est pas le plus court chemin selon les coûts $-\log w(e)$ ;
- sa probabilité recomposée ne correspond pas au produit de ses `compiled_weight` ou sa
  probabilité conditionnelle ne correspond pas à $P(\pi)/P(o)$ ;
- plusieurs chemins optimaux sont à égalité sans départage canonique consigné ;
- un cycle atteignable de coût nul rend la sélection modale ambiguë ;
- une trajectoire n'atteint pas l'issue demandée ;
- une histoire est tronquée ou dépasse la fenêtre configurée ;
- une donnée cachée apparaît dans le paquet serveur ;
- une empreinte du paquet ou du retour ne correspond pas ;
- un identifiant de preuve n'existe pas dans l'histoire concernée ;
- une sortie manque, ne respecte pas le schéma ou appartient au mauvais prompt ;
- une comparaison A/B n'a pas sa contrepartie B/A.

## 9. Ordre d'implémentation

1. Implémenter et valider `5.0` puis `5.1`.
2. Remplir les annotations humaines de calibration.
3. Créer l'exécuteur du cluster et `5.2`, puis lancer le paquet `pilot`.
4. Figer les prompts après le pilote et produire le paquet `final`.
5. Récupérer les sorties et implémenter `5.3`.
6. Implémenter `5.4` seulement lorsque toutes les annotations sont valides.
7. Construire la diapositive avec `5.5` en dernier.
