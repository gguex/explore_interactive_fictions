# Phase 4 — Calcul canonique des indices BoP

Ce document décrit les sorties scientifiques produites avant leur sélection et leur mise
en forme pour la présentation. La première analyse se place à la borne **Random Walk** du
formalisme Bag-of-Paths : elle utilise directement chacune des 27 matrices de transition
$W^{(p)}$ compilées en phase 3. Les matrices ne sont jamais moyennées avant le calcul.

## Calcul

Pour les 350 paragraphes transitoires, $Q$ est la sous-matrice transitoire de $W$ et

$$N=(I-Q)^{-1}.$$

Depuis le paragraphe initial $s=1$, le script calcule notamment :

- les visites attendues $N_{si}$ et la probabilité d'atteindre $i$,
  $h_i=N_{si}/N_{ii}$ ;
- les probabilités d'absorption vers `Death` et `Win`, ainsi que le potentiel de victoire
  ou de mort de chaque nœud ;
- les flux d'arête $N_{si}W_{ij}$ ;
- les visites et flux conditionnés à chacune des deux issues ;
- l'entropie locale $H(W_i)$ et l'entropie totale de trajectoire
  $\sum_i N_{si}H(W_i)$, avec le logarithme naturel et donc en nats ;
- la couverture attendue $\sum_i h_i/350$ ;
- le chevauchement attendu de deux lectures indépendantes
  $\sum_i h_i^2/\sum_i h_i$, et son complément appelé `replayability` ;
- l'impact local d'un choix, défini comme l'écart-type pondéré des potentiels de victoire
  de ses destinations, puis l'agentivité globale pondérée par les visites ;
- la divergence de Jensen–Shannon entre chaque paire de profils, séparément pour les
  distributions normalisées de visites de nœuds et de flux d'arêtes.

Ces quantités sont analytiques : elles n'introduisent pas d'erreur de Monte-Carlo. Les
indices conditionnés à une issue utilisent l'identité
$E[V_i\mid O]=E[V_i]P(O\mid i)/P(O\mid s)$.

## Fichiers de sortie

La commande

```bash
uv run python scripts/4.1_compute_bop_indices.py --book LW01
```

écrit dans `data/processed/bop/LW01/` :

| Fichier | Unité d'observation | Contenu principal pour LW01 |
| :--- | :--- | :--- |
| `manifest.json` | Un calcul | Version du schéma, conventions, définitions et nombres de lignes. |
| `profile_metrics.csv` | Un profil | 27 lignes : absorption, durée, entropie, couverture, chevauchement, rejouabilité et agentivité. |
| `node_metrics.csv` | Un profil × un paragraphe | 9 450 lignes : visites, potentiels, mortalité, entropie, impact des choix et versions conditionnelles. |
| `edge_metrics.csv` | Un profil × une arête canonique | 16 254 lignes : poids compilé et flux non conditionnel, conditionnel à `Death` et conditionnel à `Win`. |
| `node_profile_summary.csv` | Un paragraphe | 350 lignes : moyenne, écart-type, étendue et profils extrêmes de la visite sur les 27 profils. |
| `profile_pair_metrics.csv` | Une paire non ordonnée de profils | 351 lignes : divergences de visites et de flux, écarts de victoire et d'entropie. |

Les quatre champs `profile_id`, `risk`, `morality` et `action` sont répétés dans les
tables par profil afin que chaque ligne reste interprétable seule. Les arêtes parallèles
restent séparées dans `edge_metrics.csv`, tandis que l'entropie est calculée sur les
probabilités agrégées de $W$ par couple source–destination.

## Validation

Le validateur ne réutilise pas les fonctions du calculateur. Pour chaque profil, il
recharge `W.csv`, reconstruit $N$, les absorptions, les potentiels, les entropies et tous
les flux, puis vérifie :

- les schémas, ordres, couvertures et nombres de lignes ;
- $P(Death)+P(Win)=1$ ;
- la conservation du flux à chaque source et sa somme égale à la durée attendue ;
- les sommes des contributions directes à la mortalité et à la victoire ;
- les identités des indices globaux et conditionnels ;
- l'accord avec le résumé d'absorption de la phase 3 ;
- les 350 synthèses locales et les 351 divergences de Jensen–Shannon.

```bash
uv run python scripts/tests/test_4_1_compute_bop_indices.py --book LW01
```

Le calcul exhaustif constitue la source canonique. Les prochains scripts de phase 4
pourront en extraire la moyenne équilibrée, les effets marginaux, les profils contrôlés
et les figures sans recalculer les matrices fondamentales.
