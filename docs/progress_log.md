# Journal d'avancement

> Journal chronologique du projet. Les nouvelles entrées sont ajoutées sans réécrire les
> précédentes. Une correction factuelle ultérieure doit être consignée dans une nouvelle
> entrée.

## État synthétique au 19.08.2026

| Chantier | État | Résultat actuel |
| :--- | :--- | :--- |
| Corpus LW01 | Terminé | 350 sections HTML. |
| Extraction des nœuds | Terminée | `LW01_nodes.csv`, 350 nœuds. |
| Extraction des arêtes | Terminée | `LW01_e_edges.csv`, 556 arêtes. |
| Calibration LLM | Terminée | Structure validée ; le rapport final versionné contient 3 divergences sémantiques douces. |
| Contrôle qualité | Terminé | Choix complets, IDs valides, 350 nœuds atteignables, 17 fins explicites. |
| Spécification du pré-graphe | Terminée | Multigraphe direct L0–L2 indépendant des profils, avec les deux issues `Death` et `Win`. |
| Audit pour la phase 2 | Terminé | Conversions automatiques recensées et file initiale de 18 paragraphes à superviser. |
| Construction du pré-graphe | Planifiée, à implémenter | Deux scripts courts encadrent une annotation manuelle ; aucun pré-graphe encore produit. |
| Compilation de \(W\) | Phase 3 planifiée | Une matrice par profil ; les probabilités de victoire au combat restent libres. |
| Bag-of-Paths et indices | Différé | Première analyse fixée à la borne RW ; indices à choisir après validation de \(W\). |
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

### 17.08.2026 — Simplification de la modélisation

- Vérification des règles de *Lone Wolf* sur Project Aon et de la structure des 556 choix
  du corpus local.
- Constat qu'aucun paragraphe de choix ne contient plusieurs liens de section et qu'aucun
  paragraphe stochastique ne mélange choix libre et tirage : le livre fournit déjà
  l'essentiel du découpage nécessaire.
- Abandon des nœuds intermédiaires de résolution, qui compliquaient longueurs, visites et
  interprétation des chemins sans apporter d'information narrative.
- Conservation des seuls terminaux synthétiques nécessaires aux issues implicites.
- Remplacement des tables séparées `nodes`, `actions`, `outcomes` par `model_nodes` et
  `model_edges`.
- Adoption de `action_id` pour regrouper les conséquences d'une même action dans le
  multigraphe.
- Définition du poids direct d'une arête :
  `P_ref(e) = π_s(a | i) × q_s(e | a)`.
- Archivage de la première spécification dans
  `docs/archives/graph_model_2026-08-13.md` et réécriture de la documentation active.

### 18.08.2026 — Adoption de la pondération directe par \(W\)

- Abandon du formalisme « action–conséquence » encore conservé dans la spécification du
  17.08.2026.
- Suppression de `action_id`, de la décomposition `π × q` et des objets intermédiaires de
  décision ou de résolution.
- Adoption d'un poids final directement porté par chaque arête, puis agrégation des
  multiarêtes par `W_ij = Σ w_e`.
- Décision de travailler d'abord uniquement à la borne Random Walk de BoP afin d'étudier
  un flux moyen d'aventures ; la matrice de coûts `C` et la borne SP sont écartées de la
  phase actuelle.
- Maintien des seuls terminaux synthétiques nécessaires aux issues sans paragraphe cible,
  notamment les morts implicites de combat.
- Adoption de deux traitements à comparer pour les disciplines Kai : matrice moyenne
  avec probabilité marginale `5/10`, et moyenne des flux sur les 252 configurations
  cohérentes de cinq disciplines.
- Les combats restent abstraits ; victoire, défaite et évasion reçoivent directement
  leurs poids dans \(W\).

### 18.08.2026 — Audit d'implémentation depuis la phase 1

- Confirmation des 350 nœuds, 556 arêtes, 17 fins écrites et de l'atteignabilité complète
  du corpus.
- Constat que la topologie peut être entièrement reprise automatiquement.
- Identification de 140 transitions forcées non combattantes, 283 arêtes de choix
  explicite non combattantes, 39 arêtes RNT simples et 18 combats compilables par des
  règles génériques.
- Identification de 41 arêtes Kai dans 32 paragraphes ; 30 paragraphes suivent une règle
  standard et les §23 et 334 demandent un traitement particulier.
- Identification d'une file initiale de 18 paragraphes à superviser : §9, 12, 21, 23,
  43, 112, 169, 173, 180, 191, 203, 208, 220, 227, 229, 231, 334 et 339.
- Constat que `health_modifier`, `special_mechanic` et `items_granted` ne sont pas assez
  exhaustifs pour modéliser L3 ; ces mécaniques restent exclues et signalées.
- Réécriture de `gamebook_global_plan.md` et `graph_model.md` selon le modèle \(W\)
  direct.

### 19.08.2026 — Simplification de la recette

- Abandon de l'approche applicative fondée sur des schémas stricts, quinze étapes et une
  batterie de tests.
- Adoption d'un processus de recherche court : conversion automatique, annotation des
  exceptions, puis compilation et contrôles intégrés.
- Regroupement des transformations automatiques dans `scripts/3_prepare_graph.py` et de
  la fusion/compilation dans `scripts/4_compile_graph.py`.
- Décision de superviser un paragraphe particulier dans son ensemble plutôt que de
  gérer des surcharges partielles complexes.
- Ajout d'un tableau « cas de figure / traitement » réutilisable directement dans la
  présentation.
- Conservation de la file connue de 18 paragraphes et réduction des validations à quatre
  contrôles essentiels sur les données réelles.

### 19.08.2026 — Séparation du pré-graphe et des profils

- Décision que la phase 2 produit un pré-graphe indépendant des profils et non une
  matrice de marche.
- Adoption de deux nœuds d'issue uniques, `Death` et `Win`, seuls nœuds absorbants ; les
  17 fins narratives deviennent des pré-terminaux reliés à leur issue.
- Abandon des autres terminaux techniques ; les morts implicites pointent directement
  vers `Death`.
- Définition précise du tableau `LW01_supervision.csv`, créé vide avec son en-tête par
  `scripts/3_prepare_pregraph.py`, puis consommé automatiquement lors de la finalisation.
- La phase 3 compile le pré-graphe pour plusieurs profils. Chaque profil fournit
  notamment ses affinités, ses disciplines et ses probabilités de victoire au combat.
- Remplacement des scripts précédemment projetés par `3_prepare_pregraph.py`,
  `4_finalize_pregraph.py` et, en phase 3, `5_compile_w.py`.

## Prochaine étape

Écrire `scripts/3_prepare_pregraph.py` : traiter les cas ordinaires, ajouter `Death` et
`Win`, produire `auto_edges.csv` et `review_queue.csv`, puis créer le tableau
`LW01_supervision.csv` vide. Les indices BoP et les trajectoires restent volontairement
hors de ce chantier.
