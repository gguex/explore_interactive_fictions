# Journal d'avancement

> Journal chronologique du projet. Les nouvelles entrées sont ajoutées sans réécrire les
> précédentes. Une correction factuelle ultérieure doit être consignée dans une nouvelle
> entrée.

## État synthétique au 13.08.2026

| Chantier | État | Résultat actuel |
| :--- | :--- | :--- |
| Corpus LW01 | Terminé | 350 sections HTML. |
| Extraction des nœuds | Terminée | `LW01_nodes.csv`, 350 nœuds. |
| Extraction des arêtes | Terminée | `LW01_e_edges.csv`, 556 arêtes. |
| Calibration LLM | Terminée | Structure validée ; le rapport final versionné contient 3 divergences sémantiques douces. |
| Contrôle qualité | Terminé | Choix complets, IDs valides, 350 nœuds atteignables, 17 fins explicites. |
| Spécification du graphe | Terminée | L0–L3, périmètre des mécaniques et compilation définis dans `graph_model.md`. |
| Modèle probabiliste | À implémenter | Aucun graphe de calcul ni matrice encore produits. |
| Bag-of-Paths et indices | À définir | Rôle méthodologique et indices non arrêtés. |
| Analyse des histoires par LLM | À faire | Principe retenu, protocole non développé. |

## Historique

### Avant juin 2026 — Première extraction

- Constitution du corpus LW01 à partir des sections HTML de Project Aon.
- Développement des premiers parseurs de nœuds et d'arêtes.
- Préparation manuelle d'un jeu de calibration et d'un gold standard.

### Juin 2026 — Calibration de l'extraction LLM

- Mise en place de l'extraction structurée sur le cluster Curnagl avec vLLM.
- Itérations du prompt et comparaison systématique avec le gold standard.
- Conservation des sorties intermédiaires et des rapports d'erreurs dans
  `results/curnagl_results/`.
- Stabilisation du prompt final sur Qwen3.6-27B.

### 14.07.2026 — Nettoyage et finalisation de la phase 1

- Reprise du périmètre de recherche et rédaction d'un premier plan global.
- Réorganisation du dépôt et archivage des scripts devenus inactifs.
- Séparation du parseur de nœuds dans `scripts/2_parse_nodes.py`.
- Régénération des sorties et vérification de leur stabilité.
- Extraction complète des 350 sections de LW01 : 556 arêtes.
- Ajout de `scripts/utils/qc_extraction.py`.
- Contrôle final : aucune balise de choix manquante, aucun ID invalide, aucun nœud
  inaccessible depuis la section 1 et aucune violation des règles du schéma contrôlées.

### 13.08.2026 — Audit de reprise

- Vérification du dépôt, de l'historique Git, des données et des scripts.
- Nouvelle exécution du contrôle qualité : résultats de la phase 1 confirmés.
- Vérification statique : Ruff et mypy passent sans erreur.
- Constat que les phases de modélisation, de calcul BoP et d'analyse globale ne sont pas
  encore implémentées.
- Identification de la dépendance excessive de l'ancien projet à l'expansion d'endurance
  et aux mécaniques propres à *Lone Wolf*.

### 13.08.2026 — Recentrage méthodologique et documentaire

- Adoption d'une question de recherche centrée sur le distant reading hybride des
  fictions interactives.
- Retrait de l'expansion d'endurance du socle général ; elle devient une extension d'état
  optionnelle.
- Adoption d'un modèle à niveaux L0–L3 et d'un multigraphe dirigé simple par défaut.
- Principe de nœuds virtuels limité aux actions possédant plusieurs conséquences.
- Séparation explicite entre disponibilité, décision du joueur et conséquence.
- Conservation intégrale de la phase 1 ; la suite passera par une couche d'adaptation.
- Archivage daté des anciens documents de planification, de nettoyage, de schéma et de
  mécaniques.
- Création du présent journal et du nouveau plan global.

### 13.08.2026 — Spécification de la modélisation en graphe

- Création de `docs/graph_model.md`, qui acte la représentation retenue.
- Définition précise de L0–L3 ; L0–L2 forment le socle et L3 reste une extension.
- Adoption des objets canoniques `nodes`, `actions`, `outcomes` et d'un multigraphe
  dirigé compilé.
- Décision de créer un nœud virtuel seulement lorsqu'une action possède plusieurs
  conséquences.
- Revue de toutes les mécaniques LW01 : hasard et conditions retenus ; combats et évasion
  abstraits ; ressources persistantes non simulées ; liens cachés ajoutables avec une
  provenance vérifiable.
- Abandon de la probabilité moyenne automatique pour les compétences : leur disponibilité
  est fixée par des scénarios explicites.
- Définition de l'interface BoP (`P_ref`, caractéristiques de coûts, types de nœuds), sans
  présélectionner les indices.
- Définition du pipeline de compilation depuis la phase 1, qui reste inchangée : règles
  sûres, table d'adaptation auditée, tables canoniques, scénarios, graphe et validations.

## Prochaine étape

Construire la table d'adaptation LW01 et les tables canoniques prévues par
`graph_model.md`. Le choix des indices BoP peut être mené en parallèle à partir de cette
spécification désormais stable.
