# Le plan de nettoyage pour la présentation sur l'étude des fictions interactives

## Contexte

Il s'agit de construire une présentation, qui va être suivie par un article, pour la conférence COMHUM2026.
L'abstract, contenu `docs/infict-llm_abstract.tex`, à été accépté. On peut dévier de ce qui a été présenté, mais l'idée 
générale reste la même.

Pour le moment, du travail a été effectué, mais plusieurs fichiers de notes ne sont plus à jour et le code est un peu en désordre. 
Il s'agit donc de faire un petit nettoyage de la manière suivante :

   1. (fait, 14.07.2026) Dans un premier temps, on revoit ce qu'on va faire globalement. On prend du recule et on note le plan global dans `docs/gamebook_global_plan.md` 
   2. (fait, 14.07.2026) On nettoye toutes les notes pour qu'elle soient propres : `gamebook_data_schema.md` réécrit autour du pipeline actuel (ancien schéma d'arêtes → `docs/archives/legacy_edges_schema.md`), `gamebook_mechanics.md` aligné sur le plan global, `utilisation_dcsr-llm.md` archivé (pipeline remplacé par `cluster_scripts/`).
   3. (fait, 14.07.2026) On met à jour les scripts, on archive et on nettoye le repo : partie "nodes" de `2_parse_simple_gamebook.py` extraite dans `scripts/2_parse_nodes.py` (l'original et `gold_json_to_csv.py` → `scripts/archives/`), `1_parse_for_edge_extraction.py` nettoyé (JSON indenté reproductible), chemins de `eval_diff.py` corrigés, `LW01_edges.csv` (ancien schéma) archivé, README réécrit. Sorties régénérées et vérifiées identiques.

Cela nous permettra de repartir sur des bonnes bases.

### Fichiers à créer et à revoir 

- (à créer) `docs/gamebook_global_plan.md`.
- `docs/gamebook_data_schema.md`.
- `docs/gamebook_mechanics.md`.
- Potientiellement, les scripts dans `scripts/`.
- Archiver ce qui est superflu.

## Etapes de recherches

Pour le moment, dans l'idée il y a trois étapes globales dans le recherche. C'est surtout la première qui a été faite :

1. (partiellement fait) Extraire les edges et les noeuds, avec plusieurs caractéristiques sur ces derniers choix. Cela a été fait de la manière suivante :
   - Les fichiers html pour les différentes sections du premier livre du "Lone Wolf" ont été extraites dans `data/raw/LW01/sections`.
   - Grâce au script `scripts/1_parse_for_edge_extraction.py`, on extrait les noeuds sous format json avec les choix notés entre balises, dans `data/processed/nodes_edges/LW01/LW01_for_edges_extraction.json`.
   - Les fichiers `for_edge_extraction/LW01_calibration.json` et `for__edge_extraction/LW01_calibration_edges_gold.csv` ont été créé manuellement à partir de ``data/processed/nodes_edges/LW01/LW01_for_edges_extraction.json`.
   - On bascule sur le cluster de calcul, où des scripts et un prompt (voir `cluster_scripts/`) sont utilisés avec un modèle local pour extraire des informations sur les edges. On rappatrie les résultats dans `results/curnagl_results/csv`. Plusieurs essais on été fait pour calibrer le prompt au mieux (les itérations inclues l'étapes suivante)
   - On regarde l'adéquation entre les résultats du cluster et le gold avec `scripts/utils/eval_diff.py`, les résultats sont stocké sous `results/curnagl_results/csv/rapport_erreurs_final.csv`. On garde un historique pour présenter les "progrès" effectués.
   - (à faire) Une fois qu'on est content (c'est le cas), on parse toutes les edges pour avoir nos données
   - Le script `script/2_parse_simple_gamebook.py` est une ancienne version pour extraire noeuds et arêtes à partir des fichiers html. La partie "nodes" et à garder, mais edge est maintenant superflu. C'est du code à revoir.
2. (à faire, mais voir avec le nouveau plan) Modéliser l'histoire par un graphe et des chaînes de Markov. Certaines méchaniques sont incluses, d'autres non. Le but de cette étape est d'obtenir un graphe qui nous permettera de faire des calculs.
3. (à revoir selon le nouveau plan) Calculer des indices sur l'histoire, les différents chemins, les liens et les noeuds. On va utiliser deux outils : le formalisme "Bag-of-Path" pour des indices mathématiques rigoureux, mais également des LLM pour analyse le contenu textuel. On peut utiliser les deux de manière indépendante ou une mixture des deux.
