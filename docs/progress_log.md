# Journal d'avancement

> Journal chronologique du projet. Les nouvelles entrées sont ajoutées sans réécrire les
> précédentes. Une correction factuelle ultérieure doit être consignée dans une nouvelle
> entrée.

## État synthétique au 25.08.2026

| Chantier | État | Résultat actuel |
| :--- | :--- | :--- |
| Corpus LW01 | Terminé | 350 sections HTML. |
| Extraction des nœuds | Terminée | `LW01_nodes.csv`, 350 nœuds. |
| Extraction des arêtes | Terminée | `LW01_e_edges.csv`, 556 arêtes. |
| Calibration LLM | Terminée | Structure validée ; le rapport final versionné contient 3 divergences sémantiques douces. |
| Contrôle qualité | Terminé | Choix complets, IDs valides, 350 nœuds atteignables, 17 fins explicites. |
| Spécification du pré-graphe | Terminée | Multigraphe direct L0–L2 indépendant des profils, avec les deux issues `Death` et `Win`. |
| Audit pour la phase 2 | Terminé | Les conditions persistantes simples sont automatisées et les 14 exceptions sont supervisées. |
| Construction du pré-graphe | Terminée pour LW01 | 352 nœuds, 602 arêtes et aucune transition de phase 1 non classée. |
| Compilation de \(W\) | Terminée pour LW01 | 27 matrices valides ; résultats par profil et par axe synthétisés. |
| Bag-of-Paths et indices | Terminée pour LW01 | Calcul, synthèses et package de trois diapositives validés. |
| Analyse des histoires par LLM | Phase 5 — à faire | Position méthodologique et protocole local documentés ; implémentation à faire. |

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
- Séparation du parseur de nœuds, désormais nommé `scripts/1.2_parse_node.py`.
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
- Regroupement alors projeté des transformations automatiques et de la
  fusion/compilation en deux scripts.
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
  `scripts/2.1_prepare_pregraph.py`, puis consommé automatiquement lors de la
  finalisation.
- La phase 3 compile le pré-graphe pour plusieurs profils. Chaque profil fournit
  notamment ses affinités, ses disciplines et ses probabilités de victoire au combat.
- Remplacement des scripts précédemment projetés par `2.1_prepare_pregraph.py`,
  `2.2_finalize_pregraph.py` et, en phase 3, `3.1_compile_w.py`.

### 19.08.2026 — Nommage des scripts par phase

- Adoption de la convention `<phase>.<ordre>_<action>.py` pour rendre la place de
  chaque script explicite dans la feuille de route.
- Renommage des scripts existants en `scripts/1.1_parse_for_edge_extraction.py` et
  `scripts/1.2_parse_node.py`.
- Alignement des scripts projetés des phases 2 et 3 sur la même convention.

### 19.08.2026 — Implémentation des scripts de phase 2

- Ajout de `scripts/2.1_prepare_pregraph.py` : conversion des cas ordinaires, ajout des
  issues de combat et des pré-terminaux, production de la file de supervision et création
  non destructive du tableau d'annotation.
- Ajout de `scripts/2.2_finalize_pregraph.py` : contrôle de la couverture de la
  supervision, fusion des arêtes, création des deux tables du pré-graphe et du rapport de
  conversion.
- Vérification statique de la qualité du code. À la demande du chercheur, les scripts
  n'ont pas été exécutés et aucun fichier de données de phase 2 n'a encore été produit.

### 19.08.2026 — Séparation production / contrôles par corpus

- Paramétrage de tous les scripts numérotés des phases 1 et 2 avec
  `--book <BOOK_ID>` et adoption d'une convention de chemins commune aux livres
  *Lone Wolf*.
- Retrait de la liste des 18 paragraphes LW01 du script de production 2.1 : les
  exceptions sont uniquement détectées à partir de la structure des données.
- Remplacement de la liste fermée des dix disciplines Kai par une détection textuelle
  commune aux disciplines Kai, Magnakai et Grand Master.
- Création de `scripts/tests/test_2_1_prepare_pregraph.py`, qui contient le contrôle
  propre à LW01 et quelques invariants généraux de la préparation.
- Aucun script de production ni contrôle sur les données n'a été exécuté.

### 20.08.2026 — Automatisation des conditions persistantes simples

- Ajout dans `scripts/2.1_prepare_pregraph.py` d'une conversion générique pour la
  possession d'un objet, un montant minimal de Gold Crowns et un seuil minimal
  d'Endurance.
- Conservation de ces conditions sous forme de `condition_available(type, value)` et de
  sa formule complémentaire, sans simuler l'état persistant du personnage.
- Maintien en supervision des conditions composées, ambiguës ou mêlées à d'autres
  mécaniques.
- Ajout de contrôles propres à LW01 pour les §9, 12, 173 et 203.
- Exécution de la préparation et de son contrôle : 558 arêtes automatiques et réduction
  de la file de supervision de 18 à 14 paragraphes.

### 20.08.2026 — Supervision et finalisation du pré-graphe LW01

- Annotation complète des 14 paragraphes de `review_queue.csv` en 44 arêtes
  supervisées.
- Aplatissement exact des tirages successifs du §21 : 0,60 vers le §189, 0,04 vers le
  §312 et 0,36 vers `Death`.
- Adoption de parts normalisées entre choix disponibles pour les conditions composées,
  de choix conditionnés par la victoire pour les décisions post-combat et de
  distributions catégorielles pour les combats avec fuite ou issues particulières.
- Alignement du validateur 2.2 sur le type automatique `state_condition`.
- Finalisation réussie : 352 nœuds, 602 arêtes, 14 sources supervisées et zéro arête de
  phase 1 non classée.

### 20.08.2026 — Périmètre expérimental de la phase 3

- Adoption d'un schéma unique de profil composé seulement de `profile_id`, `risk`,
  `morality` et `action`.
- Décision de compiler les 27 combinaisons des trois niveaux de chacun des trois axes,
  tout en ne montrant dans la présentation qu'un profil neutre, quelques archétypes et
  des résultats agrégés par axe.
- Retrait des disciplines Kai, du combat, de la fuite et des ressources de la définition
  du profil.
- Fixation globale de `kai_availability` à 0,5 et adoption d'un paramètre unique pour la
  victoire au combat, la fuite et la satisfaction d'une condition persistante.
- Adoption du nom générique `has_condition` pour ce dernier paramètre, appliqué de la
  même manière aux objets, à la monnaie et aux seuils d'Endurance.
- Report des variantes de disciplines, des capacités de combat, de la propension à fuir,
  du suivi d'état et de leurs analyses de sensibilité au-delà de l'itération de
  présentation.

### 20.08.2026 — Première compilation de la phase 3

- Ajout de `scripts/3.0_generate_profiles.py`, qui produit déterministement les 27
  combinaisons du schéma comportemental unique.
- Ajout de `scripts/3.1_compile_w.py`, qui reconnaît explicitement toutes les formes
  symboliques présentes dans le pré-graphe sans exécuter de code arbitraire.
- Séparation des profils génériques dans `behavioral_profiles.json` et des hypothèses
  propres à LW01 dans `LW01_compilation_settings.json`.
- Adoption provisoire des valeurs 0,5 pour `kai_availability`,
  `combat_win_probability`, `escape_probability` et `has_condition`, avec des
  distributions fixes pour les trois combats à issues particulières.
- Ajout de `scripts/tests/test_3_1_compile_w.py`, qui contrôle la couverture des 602
  arêtes, leur agrégation, les sommes de lignes, les seuls absorbants `Death` et `Win` et
  l'absorption éventuelle de tous les nœuds.
- Compilation et validation de `neutral_neutral_neutral` : 352 nœuds, 602 arêtes,
  erreur maximale de somme de ligne de $1{,}11\times10^{-15}$ ; depuis le §1,
  $P(Death)=0{,}963805$ et $P(Win)=0{,}036195$ sous les hypothèses provisoires.
- Compilation temporaire réussie des 27 profils afin de vérifier également les
  affinités non neutres ; seule la matrice neutre est conservée comme premier artefact
  du dépôt avant calibration.

### 21.08.2026 — Généralisation des issues de combat

- Remplacement des libellés détaillés de combat par trois rôles génériques : `survive`,
  `escape` et `death`.
- Suppression de `special_combat_outcomes` et de toutes les distributions configurées
  pour des paragraphes particuliers de LW01.
- Adoption d'une répartition automatique : la masse de chaque rôle est divisée à parts
  égales entre les arêtes qui le portent. Sans fuite, `survive` reçoit $v$ et `death`
  reçoit $1-v$ ; avec fuite, les masses deviennent $(1-f)v$, $f$ et
  $(1-f)(1-v)$.
- Simplification explicite des §227, 231 et 339 : les différences de perte d'Endurance
  ou de durée du combat restent dans les notes, tandis que leurs continuations non
  fatales partagent le rôle `survive`.
- Cette perte volontaire de finesse locale évite toute règle codée pour un livre et rend
  le compilateur directement réutilisable pour d'autres corpus respectant les trois
  rôles génériques.
- Régénération réussie du pré-graphe et de la matrice neutre, dont les résultats restent
  inchangés : 352 nœuds, 602 arêtes, $P(Death)=0{,}963805$ et
  $P(Win)=0{,}036195$ depuis le §1.
- Nouvelle compilation temporaire réussie des 27 profils avec cette représentation
  générique.

### 21.08.2026 — Calibration de la probabilité globale de combat

- Relecture des règles officielles de création, d'équipement, de disciplines et de
  combat de *Flight from the Dark*, ainsi que des 29 paragraphes de combat de LW01.
- Ajout de `scripts/3.2_calibrate_combat.py` et de la configuration déclarative
  `LW01_combat_calibration.json`. Les modificateurs propres aux paragraphes restent hors
  du compilateur générique.
- Simulation reproductible de 300 000 parcours neutres avec les caractéristiques 10–19
  et 20–29, cinq disciplines sur dix, l'équipement initial, la table de combat complète,
  Healing et les blessures conservées entre combats.
- Sur 463 609 combats engagés, estimation d'une perte à 0,115149 avec Endurance remise
  au maximum et à 0,167242 avec attrition. L'Endurance moyenne passe de 25,11 au premier
  combat à 20,77 au deuxième, 17,73 au troisième et 16,50 au quatrième.
- Lissage par risque groupé $D/N$ et adoption de
  `combat_win_probability = 0.833`, soit une probabilité de perte arrondie à 0,167.
- Conservation du rapport complet par rang et par paragraphe dans
  `data/processed/graph/LW01/combat_calibration.json`; synthèse méthodologique dans
  `docs/fixed_probabilities.md`.
- Ajout d'un contrôle indépendant des cellules de table utilisées dans les exemples
  officiels, des agrégations du rapport, de l'effet d'attrition et de la couverture des
  29 paragraphes de combat.
- Recompilation et validation de la matrice neutre avec $v=0{,}833$ : 352 nœuds,
  602 arêtes, erreur maximale de somme de ligne de $1{,}11\times10^{-15}$ et, depuis le
  §1, $P(Death)=0{,}880189$, $P(Win)=0{,}119811$ sous les autres hypothèses fixes.

### 21.08.2026 — Justification des paramètres fixes subjectifs

- Regroupement de la calibration du combat et des choix subjectifs dans
  `docs/fixed_probabilities.md`, avec une présentation plus concise du calcul détaillé du
  combat.
- Adoption explicite de `escape_probability = 0.5` comme hypothèse d'indifférence entre
  fuir et poursuivre, et de `has_condition = 0.5` comme prior binaire neutre commun aux
  objets, à l'argent et à l'Endurance.
- Contrôle de sensibilité aux valeurs 0,25 et 0,75 : variation de $P(Win)$ de 0,13 point
  de pourcentage pour la fuite et de 0,60 point pour les conditions entre les scénarios
  extrêmes.
- Les deux valeurs sont consignées comme hypothèses subjectives, et non comme
  estimations empiriques ; elles restent communes aux 27 profils.

### 21.08.2026 — Finalisation de la phase 3 pour LW01

- Extension du validateur 3.1 avec `--all-profiles` et contrôle exhaustif des 27 matrices
  contre le même pré-graphe de 352 nœuds et 602 arêtes.
- Ajout de `scripts/3.3_summarize_profiles.py` et de son contrôle indépendant, produisant
  `profile_summary.csv`, `axis_summary.csv` et `profile_summary.json`.
- Validation réussie des 27 matrices, avec absorption garantie et une erreur maximale
  de somme de ligne de $1{,}11\times10^{-15}$.
- Pour le profil neutre : $P(Win)=0{,}119811$ et 27,21 transitions attendues avant
  absorption.
- Étendue de $P(Win)$ de 0,054397 pour `reckless_selfish_tactical` à 0,258347 pour
  `cautious_selfish_physical`, soit 20,40 points de pourcentage et un rapport d'environ
  4,75 entre les deux extrêmes.
- L'axe du risque est le plus contrasté : moyennes de 0,211973 pour `cautious`, 0,119682
  pour `neutral` et 0,067321 pour `reckless`. Les affinités 2 / 1 / 0,5 sont conservées
  pour cette itération.
- Documentation complète des résultats et de leur interprétation dans
  `docs/phase3_results.md`. La phase 3 est terminée pour LW01.

### 21.08.2026 — Séparation des analyses structurelles et narratives

- Limitation de la phase 4 au calcul et à l'interprétation des indices BoP.
- Création d'une phase 5 distincte pour sélectionner des trajectoires, reconstruire leurs
  histoires complètes et les faire évaluer par un LLM.
- Adoption provisoire d'un protocole hybride : distances structurelles pour le contrôle,
  embeddings pour la diversité et la sélection, puis évaluation LLM structurée pour la
  cohérence et les qualités narratives.
- Report de la généralisation à la phase 6.

### 25.08.2026 — Visualisation commune des phases 3 et 4

- Adoption d'un layout longitudinal stable, de gauche à droite selon la progression
  narrative, inspiré du diagramme de Project Aon.
- Implémentation de `scripts/4.0_visualize_graph.py`, qui calcule des coordonnées
  indépendantes du profil et rend les poids compilés du profil demandé.
- Ajout de `scripts/utils/extract_project_aon_layout.py` : les 350 centres du SVG officiel
  sont appariés exactement aux paragraphes `1`–`350`, avec URL et empreinte SHA-256.
- Adoption du layout Project Aon par défaut pour LW01 et conservation du layout
  algorithmique comme solution de repli.
- Production pour le profil neutre d'un SVG complet zoomable, d'un SVG 16:9 et d'un PNG
  2880 × 1620 destiné aux diapositives.
- Passage de toute la figure en anglais avec le titre unique `LW01 - graph` ; ajout des
  losanges orange de combat, croix rouges de fin mortelle et étoile verte de victoire.
- Ajout d'un validateur indépendant couvrant les 350 paragraphes, les composantes
  fortement connexes, la progression des couches et les trois fichiers graphiques.
- Conservation du graphe canonique à deux absorbants dans les calculs, avec une projection
  locale des morts dans la figure pour éviter les longues arêtes convergeant vers `Death`.

### 25.08.2026 — Protocole de comparaison des indices

- Décision de calculer les indices séparément pour les 27 profils et de ne jamais
  calculer un indice sur une moyenne préalable des matrices $W$.
- Distinction entre le profil neutre et la moyenne équilibrée des 27 profils, qui ne
  représente pas une population empirique de joueurs.
- Adoption des effets marginaux des axes et du contraste contrôlé
  prudent–neutre–téméraire pour interpréter les profils sans confondre leurs dimensions.
- Conservation des extrêmes observés comme illustration de l'étendue et calcul de flux
  conditionnés à `Win` ou `Death` pour préparer les trajectoires de phase 5.
- Limitation de la présentation à une figure globale, une synthèse des axes et une
  comparaison locale sur le layout longitudinal commun.

### 25.08.2026 — Calcul exhaustif des indices BoP

- Implémentation de `scripts/4.1_compute_bop_indices.py` à la borne Random Walk pour les
  27 matrices de profils, sans moyenne préalable de $W$.
- Production des métriques globales, des 9 450 lignes profil–nœud, des 16 254 lignes
  profil–arête, des 350 synthèses locales et des 351 paires de profils dans
  `data/processed/bop/LW01/`.
- Calcul analytique des visites et flux non conditionnels et conditionnés à `Death` ou
  `Win`, des entropies en nats, de la couverture, du chevauchement, de la rejouabilité,
  de l'impact des choix, de l'agentivité et des divergences de Jensen–Shannon.
- Ajout d'un validateur indépendant qui recharge chaque matrice $W$, reconstruit sa
  matrice fondamentale et contrôle les identités locales et globales ainsi que l'accord
  avec les absorptions de la phase 3.
- Validation complète réussie. Pour le profil neutre : $P(Win)=0{,}119811$, durée
  attendue de 27,211670 transitions et entropie de 15,478212 nats.
- Documentation des formules, conventions et schémas dans `docs/phase4_indices.md`.

### 25.08.2026 — Synthèses 4.2 pour la présentation

- Implémentation de `scripts/4.2_summarize_bop_indices.py`, qui relit exclusivement les
  sorties canoniques de 4.1 et ne recalcule ni $W$ ni les matrices fondamentales.
- Production d'une synthèse des 15 indices globaux, de 135 effets axe–niveau–indice et
  des 45 valeurs du contraste contrôlé prudent–neutre–téméraire.
- Production de tables prêtes pour les figures couvrant les 350 paragraphes et les 602
  arêtes, avec valeurs neutres, moyennes équilibrées, sensibilités et contrastes entre
  les trajectoires conditionnées à la victoire et à la mort.
- Sélection déterministe des dix premiers paragraphes selon six classements locaux.
- Ajout et passage du validateur 4.2, qui recalcule indépendamment les agrégations,
  extrêmes, différences et classements à partir des tables de 4.1.
- Pour contrôle : victoire neutre de 0,119811 contre une moyenne équilibrée de 0,132992 ;
  couverture neutre de 0,072789 et rejouabilité neutre de 0,795552.

### 25.08.2026 — Package de présentation 4.3 et fin de la phase 4

- Sélection finale de trois messages pour la présentation de 20 minutes : paysage
  difficulté–liberté des 27 profils, effets marginaux des axes et trois cartes locales du
  même graphe longitudinal.
- Ajout de `scripts/4.3_build_bop_presentation.py`, produisant quatre supports en anglais
  dans des versions PNG 1920 × 1080 et SVG éditable, ainsi qu'un tableau CSV et un
  manifeste avec empreintes SHA-256.
- Mise en évidence d'une association descriptive positive entre victoire et entropie de
  trajectoire ($r=0{,}826$) sur le plan factoriel complet, sans interprétation causale ou
  inférentielle.
- Présentation des effets marginaux sur la victoire, l'entropie, la couverture et la
  rejouabilité ; l'axe du risque est le contraste principal.
- Réunion sur une seule diapositive des probabilités de visite, contributions à la
  mortalité et sensibilités au profil, avec le layout Project Aon fixé entre les panneaux.
- Ajout d'un validateur couvrant les formats, dimensions, titres, valeurs arrondies,
  points mis en avant, provenance et empreintes de tous les artefacts.
- Documentation des choix, des phrases proposées et des résultats volontairement laissés
  en annexe dans `docs/phase4_presentation.md`. La phase 4 est terminée pour LW01.

### 26.08.2026 — Position méthodologique pour les LLM en Humanités numériques

- Adoption pour la phase 5 d'un LLM local à poids ouverts comme instrument d'annotation
  interprétative, sans l'assimiler à un lecteur autonome ni à un système intrinsèquement
  explicable.
- Définition d'un protocole court et auditable : petit échantillon de trajectoires,
  pré-annotation humaine, calibration comparative, répétitions, preuves par paragraphes et
  contrôle humain complet.
- Consignation des exigences de reproductibilité, des formulations pour la présentation
  et des sources dans `docs/llm_digital_humanities.md`.

## Prochaine étape

Implémenter la sélection des trajectoires représentatives et préparer le pilote humain de
la phase 5 selon `docs/llm_digital_humanities.md`, en réutilisant notamment les flux
conditionnés produits en phase 4.
