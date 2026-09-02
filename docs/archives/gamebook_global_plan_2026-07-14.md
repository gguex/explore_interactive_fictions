# Plan global — Analyse computationnelle des fictions interactives (COMHUM2026)

> Document de référence du projet. Mis à jour le 14.07.2026.
> Voir `docs/infict-llm_abstract.tex` pour l'abstract accepté.

## 1. Objectif et livrables

Construire un cadre hybride **Bag-of-Paths (BoP) + LLMs** pour l'analyse "distante" des
fictions interactives, appliqué au premier livre de la série *Lone Wolf* (Project Aon).

Deux livrables, dans l'ordre :

1. **Présentation COMHUM2026** (échéance : ~1–2 mois).
2. **Article** développant la présentation (peut inclure les extensions écartées ci-dessous).

## 2. Décisions de périmètre (14.07.2026)

| Question | Décision | Conséquence |
| :--- | :--- | :--- |
| Corpus | **LW01 uniquement** pour la présentation | Pas de re-validation LLM sur d'autres livres ; le pipeline reste générique (préfixes `LWXX`). |
| Mécaniques | **Expansion d'état (Node, EP) complète** | Endurance, combats et évasion modélisés selon `docs/gamebook_mechanics.md` ; c'est le gros morceau de la phase 2. |
| Axes LLM | **(1) Playstyles** et **(3) Critique IA** pour la présentation | L'axe (2) corrélation structurelle vs similarité sémantique est reporté à l'article. |

**Risque assumé :** l'expansion EP complète dans un délai de 1–2 mois est ambitieuse.
Plan de repli si le BoP sur graphe étendu pose problème : revenir au graphe topologique
simple (nœud = paragraphe) où les combats deviennent des probabilités de mort sur les
arêtes, et garder l'expansion EP pour l'article.

## 3. Les trois phases de recherche

### Phase 1 — Extraction des données (quasi terminée)

Produire, à partir des HTML de Project Aon, les tables `LW01_nodes.csv` et
`LW01_edges.csv` (schémas dans `docs/gamebook_data_schema.md`).

- [x] Parsing HTML des nœuds avec choix balisés `<choice>` (`scripts/1_parse_for_edge_extraction.py`).
- [x] Jeu de calibration manuel (gold) : `data/for_edge_extraction/LW01_calibration*.{json,csv}`.
- [x] Calibration du prompt d'extraction sur le cluster (Qwen3.6-27B + vLLM, sorties structurées) :
      6 itérations, de ~35 divergences à **4 divergences "douces"** (axes sémantiques uniquement,
      aucune erreur structurelle). Historique dans `results/curnagl_results/`.
- [x] **Extraction complète** des 350 sections de LW01 sur le cluster → 556 arêtes,
      `LW01_edges.csv` (brut dans `results/curnagl_results/csv/LW01_edges_extraction.csv`).
- [x] **Contrôle qualité** (14.07.2026) : zéro écart balises `<choice>` ↔ arêtes, IDs valides,
      graphe entièrement atteignable depuis la section 1, 17 nœuds absorbants cohérents avec
      `LW01_nodes.csv`, zéro violation des règles du schéma. Notes pour la phase 2 : la
      catégorie `complex` n'est jamais utilisée (combats = `forced`/`conditional` + warning) ;
      les morts implicites (défaites de combat, échecs RNT fatals) ne sont pas des arêtes et
      devront être réinjectées via l'expansion EP (53 warnings les signalent).
- [x] Table des nœuds définitive (`scripts/2_parse_nodes.py`, partie "nodes" de l'ancien
      `2_parse_simple_gamebook.py`).

### Phase 2 — Modélisation : graphe, mécaniques et Bag-of-Paths

Construire le graphe pondéré sur lequel les calculs sont possibles.

1. **Graphe de base** : probabilités de transition par nœud —
   `forced` = 1 ; `explicit_choice` = uniforme (baseline) ; `stochastic` = probabilité exacte
   dérivée de la plage RNT (`realisation_value`) ; `conditional` (skill gates) = probabilité
   du "joueur statistique moyen" (p = proportion de disciplines choisies).
2. **Expansion EP** : état = (paragraphe, points d'endurance). Dégâts/soins statiques déplacent
   l'EP ; EP ≤ 0 route vers l'état absorbant `Death`. Les combats sont compressés en blocs
   probabilistes (distribution des pertes d'EP calculée depuis le ratio de CS et la table RNT),
   avec l'évasion comme arête de sortie alternative.
3. **Playstyles (axe LLM 1)** — décision méthodologique (14.07.2026) :
   - **Playstyle = fonction de coût** sur les arêtes `explicit_choice`, dérivée des axes
     sémantiques (`semantic_risk`, `semantic_morality`, `semantic_action`). P. ex. pour le
     joueur *prudent* : `cautious` = 0, `neutral` = 1, `reckless` = 2 (symétrique pour le
     téméraire, le noble, l'égoïste, etc.). Les transitions mécaniques (`forced`,
     `stochastic`, `conditional`) gardent leur probabilité de référence : ce ne sont pas
     des choix du joueur.
   - **θ = degré d'adhésion au playstyle** : θ = 0 donne le lecteur aléatoire uniforme,
     θ grand le joueur caricatural. Chaque playstyle définit donc une *famille continue*
     de lecteurs, pas un point.
   - Méthodologie reproductible : une grille fixe (playstyles × valeurs de θ), chaque
     indice devient une **courbe en fonction de θ, par playstyle**.
   - Les profils explorés sont définis en **section 7**.
4. **Bag-of-Paths** : implémentation du formalisme (matrice fondamentale) sur le graphe étendu,
   avec le paramètre de température θ. Vérifications numériques (absorption, normalisation).

### Phase 3 — Indices et analyses

Grille de lecture générale : percevoir le livre à trois échelles — **micro** (les arêtes,
phase 1), **méso** (nœuds et régions, indices BoP), **macro** (histoires complètes,
chemins + LLM). Le catalogue complet des indices est en **section 6** ; on retient ici le
noyau pour la présentation.

1. **Indices structurels retenus** (courbes en θ, par playstyle) :
   - *Probabilité de survie/victoire* (I1) — question associée : jouer prudemment
     augmente-t-il vraiment la survie dans ce livre ?
   - *Fonction de hasard narrative* (I2) — la courbe de danger du livre.
   - *Entropie des trajectoires* (I4) — le "sentiment de liberté" et sa décroissance en θ.
   - *Probabilité de visite, couverture espérée et rejouabilité* (I7).
   - *Carte de divergence entre playstyles* (I10) — la "réactivité" du livre.
   - Produit final : une **"fiche du livre"** (courbe de danger, profil d'EP, carte des
     régions, divergences entre playstyles), transposable telle quelle à d'autres livres.
2. **Sélection des chemins à analyser** — méthodologie à deux étages :
   - *Étage A — chemins archétypaux* (déterministes, ~5–8) : chemin le plus probable par
     (playstyle, θ élevé), plus les conditionnements *sachant la victoire* et *sachant la
     mort* (la "tragédie typique"). Zéro aléa ; pour l'analyse rapprochée en présentation.
   - *Étage B — échantillon statistique* (N ≈ 200–500, graine fixée) : tirage i.i.d.
     stratifié par issue. N choisi par critère de stabilité (bootstrap). Réduction en
     **k ≈ 10 familles d'histoires** par k-médoïdes sur distance de Jaccard (nœuds
     visités) — "les k histoires que ce livre raconte".
   - Grâce à l'expansion EP, un chemin tiré est une **vraie partie** : on interpole les
     événements mécaniques dans le texte concaténé ("tu perds 4 EP contre le Gourgaz")
     pour que le critique perçoive la tension.
3. **Critique IA (axe LLM 3)** — trois modes d'intervention du LLM :
   - *Embeddings* (déterministes, cheap) : distance pour le clustering de l'étage B ;
     dispersion sémantique des histoires (diversité narrative réelle, à comparer à
     l'entropie topologique) ; dérive sémantique le long d'un chemin (proxy de cohérence).
   - *Critique structuré* : même infrastructure que la phase 1 (vLLM, sorties structurées,
     prompt versionné, température 0). Grille : cohérence causale, arc de tension,
     motivation, rythme, qualité de la fin. **Comparaisons par paires** (ordre randomisé)
     plutôt que notes absolues, agrégées en échelle Bradley–Terry — sur un sous-ensemble
     pour la présentation, complet pour l'article. Boucle de calibration identique à la
     phase 1 : gold manuel (~10–15 histoires), mesure d'accord, itérations de prompt.
   - *Résumés structurés* (support, pas indice) : pour les slides et comme représentation
     intermédiaire si nécessaire.
   - Contrainte pratique : une histoire ≈ 5–10k mots → augmenter `max_model_len`
     (8192 actuellement) sur le cluster.
4. **Croisement structure × sémantique** — le cœur de l'argument hybride : corréler, sur
   l'échantillon B, les indices structurels par chemin (longueur, danger cumulé, EP minimal
   atteint, playstyle générateur) avec les scores du critique. Figure clé visée : tension
   structurelle (profil d'EP) vs tension perçue par le LLM.
5. *(Article, pas présentation)* Axe LLM 2 : corrélation structurelle des nœuds vs
   similarité sémantique (fondé sur I9).

### Phase 4 — Présentation

- Figures clés : visualisation du graphe (et du graphe étendu), courbes indices vs θ,
  comparaison des playstyles, exemples d'histoires générées + verdicts du critique IA.
- Slides : problème → formalisme BoP → limites (topologie seule) → apport des LLM aux
  niveaux 1 et 3 → résultats LW01 → perspectives (axe 2, autres livres).

## 4. Calendrier indicatif (8 semaines)

| Semaines | Contenu |
| :--- | :--- |
| S1 | Nettoyage du repo (cf. `docs/cleaning_plan.md`) + extraction complète LW01 + contrôle qualité. |
| S2–S4 | Phase 2 : graphe de base, expansion EP, playstyles, BoP. Point de décision fin S4 : si l'expansion EP bloque, activer le plan de repli. |
| S5–S6 | Phase 3 : indices structurels, comparaisons de playstyles, protocole et exécution de la critique IA. |
| S7–S8 | Figures, slides, marge de sécurité. |

## 5. Organisation cible du repo

```
docs/            notes de référence (ce plan, schéma de données, mécaniques, abstract)
scripts/         pipeline numéroté : 1_parse..., 2_build_graph..., 3_bop..., ...
scripts/utils/   outils transverses (éval, conversions)
cluster_scripts/ scripts d'extraction LLM (Curnagl)
data/raw/        HTML Project Aon (non versionné si volumineux)
data/processed/  tables nodes/edges finales
results/         sorties de calculs et de calibration
*/archives/      tout ce qui est conservé pour historique mais plus actif
```

## 6. Catalogue des indices constructibles

Liste complète des indices identifiés (discussion du 14.07.2026). Ceux marqués
**[présentation]** forment le noyau ; les autres sont des extensions pour l'article.
Tous se déclinent en courbes (θ, playstyle).

### Difficulté et survie (exploitent l'expansion EP)

- **I1 — Probabilité de survie/victoire** **[présentation]** : probabilité d'absorption
  en `win` vs `death`, par playstyle et θ. Croisement éventuel des courbes entre
  playstyles = résultat en soi.
- **I2 — Fonction de hasard narrative** **[présentation]** : probabilité de mourir *à*
  chaque paragraphe (ou tranche de progression). La "courbe de danger" du livre : pics de
  mortalité, boss final vs mort distribuée.
- **I3 — Profil d'endurance** : distribution de l'EP conditionnée au passage en chaque
  nœud. Courbe de tension objective : usure progressive vs récupération avant le final.
  (Utilisé dans la "fiche du livre" et le croisement de phase 3.)

### Liberté et agentivité

- **I4 — Entropie des trajectoires** **[présentation]** : calculable exactement pour une
  chaîne absorbante (Σᵢ nᵢ·Hᵢ : visites espérées × entropie locale). Le "sentiment de
  liberté" ; sa décroissance en θ mesure ce qu'un tempérament affirmé coûte en variété.
- **I5 — Pertinence des choix (agentivité)** : pour chaque nœud de décision, divergence
  entre les distributions de chemins futurs conditionnées à chaque option (ou information
  mutuelle option ↔ issue finale). Détecte les **faux choix** (reconvergence immédiate)
  vs les choix pivots. Indice potentiellement inédit — bon candidat pour l'article.
- **I6 — Frontière survie–liberté** : en variant θ, courbe survie vs entropie. Le livre
  comme objet de game design : combien de liberté sacrifier pour survivre ?

### Structure et contenu

- **I7 — Visite, couverture, rejouabilité** **[présentation]** : probabilité de visite de
  chaque nœud (colonne vertébrale vs contenu rare) ; couverture espérée (fraction du texte
  vue en une lecture) ; chevauchement espéré entre deux lectures indépendantes =
  **indice de rejouabilité**.
- **I8 — Betweenness BoP et goulots** : les "scènes obligatoires". À croiser avec les
  dominateurs du graphe (nœuds par lesquels tout chemin gagnant passe) : l'un
  probabiliste, l'autre logique.
- **I9 — Covariance/corrélation de présence entre nœuds** (formalisme BoP 2021) : les
  clusters de nœuds co-présents = **régions narratives**. Fondation de l'axe LLM 2
  (article).

### Comparatif inter-playstyles

- **I10 — Cartes et divergence entre playstyles** **[présentation]** : différence de
  probabilité de visite entre deux playstyles projetée sur le graphe ("où vit le prudent /
  où vit le téméraire") ; en global, divergence de Jensen-Shannon entre distributions de
  chemins = **réactivité du livre** (différencie-t-il réellement les tempéraments ?).

### Indices sémantiques et hybrides (côté LLM)

- **I11 — Dispersion sémantique des histoires** : spread des embeddings des histoires
  échantillonnées = diversité narrative réelle, à confronter à l'entropie topologique I4
  (un livre peut être topologiquement libre mais sémantiquement répétitif).
- **I12 — Dérive sémantique le long d'un chemin** : cosinus moyen entre nœuds consécutifs
  vs paires aléatoires ; proxy de cohérence à coût nul.
- **I13 — Scores du critique IA** : cohérence causale, arc de tension, motivation, rythme,
  qualité de la fin — par comparaisons par paires agrégées (Bradley–Terry).
  **[présentation]** sur un sous-ensemble, complet pour l'article.
- **I14 — Indices croisés structure × sémantique** **[présentation]** : corrélations entre
  indices structurels par chemin et scores I13 (la structure prédit-elle la qualité
  narrative ?).

## 7. Profils de joueurs ("playstyles caricaturaux")

### 7.1 Formalisation

Un profil `p` est défini par : un **pôle préféré** sur un ou plusieurs axes, et des
**poids** `w_axe ≥ 0` avec `Σ w_axe = 1`. Le coût d'une arête `explicit_choice` `e`,
étiquetée `ℓ_axe(e)` sur chaque axe, est :

```
c_p(e) = Σ_axe  w_axe · κ(ℓ_axe(e))      avec κ = 0 si pôle préféré,
                                               κ = 1 si neutral,
                                               κ = 2 si pôle opposé
```

Propriétés :

- Les coûts de **tous** les profils vivent dans `[0, 2]` → une même valeur de θ est
  comparable d'un profil à l'autre.
- Re-pondération : à chaque nœud, `P(e) ∝ P_ref(e) · exp(−θ · c_p(e))` **au sein de la
  masse de probabilité des choix libres** ; les arêtes mécaniques (`forced`, `stochastic`,
  `conditional`) ne sont jamais re-pondérées.
- θ = 0 redonne le lecteur aléatoire uniforme quel que soit le profil (= la baseline).

### 7.2 Les profils retenus

**Six profils purs** (poids 1 sur un axe, 0 ailleurs) — trois paires antagonistes :

| # | Profil | Axe | Pôle préféré (κ=0) | Pôle évité (κ=2) |
| :--- | :--- | :--- | :--- | :--- |
| P1 | Le Prudent | risk | `cautious` | `reckless` |
| P2 | Le Téméraire | risk | `reckless` | `cautious` |
| P3 | Le Chevaleresque | morality | `noble` | `selfish` |
| P4 | Le Mercenaire | morality | `selfish` | `noble` |
| P5 | Le Guerrier | action | `physical` | `tactical` |
| P6 | Le Rusé | action | `tactical` | `physical` |

**Deux profils composites** (poids ⅓ sur chaque axe), antagonistes sur les trois axes —
la divergence P7↔P8 (I10) est donc maximale par construction :

| # | Profil | risk | morality | action | Lecture narrative |
| :--- | :--- | :--- | :--- | :--- | :--- |
| P7 | Le Héros | `reckless` | `noble` | `physical` | Fonce, se sacrifie, combat de front. |
| P8 | Le Survivant | `cautious` | `selfish` | `tactical` | Veut juste finir le livre vivant. |

**P0 — Le Lecteur aléatoire** (θ = 0) sert de référence à tous les indices.

### 7.3 Constat empirique et précautions (calibration, 14.07.2026)

Distribution des étiquettes sur le jeu de calibration (59 `explicit_choice`) :

| Axe | Pôle A | neutral | Pôle B | Verdict |
| :--- | :--- | :--- | :--- | :--- |
| risk | cautious : 20 | 18 | reckless : 21 | Équilibré — axe fort. |
| action | physical : 22 | 23 | tactical : 14 | Équilibré — axe fort. |
| morality | noble : 5 | 49 | selfish : 5 | **Très creux** — ~17 % de choix non neutres. |

Conséquence : P3/P4 se distingueront peu du lecteur aléatoire. On les calcule quand même
(coût nul), mais les figures de la présentation se concentrent sur **P1/P2 et P7/P8** ;
P3–P6 et d'autres composites passent dans l'article. La moralité reste présente via les
composites P7/P8.

À vérifier après l'extraction complète (~350 sections) :

1. ✔ (14.07.2026) Fréquences sur tout le livre (291 `explicit_choice`) : risk
   95/84/112 et action 101/126/64 équilibrés ; **morality 11 noble / 262 neutral /
   18 selfish — le creux se confirme** (10 % non neutre). La stratégie de figures
   P1/P2 + P7/P8 est maintenue.
2. Corrélations entre axes (si `reckless` ≈ `physical`, certains profils sont redondants).
3. Courbe d'**adhésion effective** : masse de probabilité espérée sur les choix préférés
   en fonction de θ — sert à choisir la grille de θ de manière non arbitraire.
