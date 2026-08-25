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

## Synthèses pour l'analyse et la présentation

Le script 4.2 relit uniquement les tables de 4.1 : il ne recharge pas les matrices $W$
et ne recalcule aucun indice BoP.

```bash
uv run python scripts/4.2_summarize_bop_indices.py --book LW01
uv run python scripts/tests/test_4_2_summarize_bop_indices.py --book LW01
```

Les sorties sont écrites dans `data/processed/bop/LW01/presentation/` :

| Fichier | Rôle |
| :--- | :--- |
| `global_summary.csv` | Pour chacun des 15 indices globaux : profil neutre, moyenne et écart-type équilibrés, minimum, maximum et étendue sur les 27 profils. |
| `axis_summary.csv` | 135 lignes axe–niveau–indice avec moyenne marginale, dispersion et différence par rapport au niveau neutre du même axe. |
| `controlled_risk.csv` | Comparaison longue des trois profils qui ne diffèrent que par `risk`, avec différence au profil entièrement neutre. |
| `node_presentation_metrics.csv` | Une ligne par paragraphe avec les valeurs neutres, moyennes et sensibilités nécessaires aux cartes locales. |
| `edge_presentation_metrics.csv` | Une ligne par arête avec les flux neutres, moyens et conditionnés à chaque issue. |
| `node_rankings.csv` | Dix premiers paragraphes pour six classements : visite neutre, visite moyenne, sensibilité au profil, mortalité, impact des choix et contraste victoire–mort. |
| `summary.json` | Schémas, nombres de lignes, paramètres de sélection et valeurs principales. |

La « moyenne équilibrée » est toujours la moyenne arithmétique des 27 résultats déjà
calculés. Les effets marginaux d'un niveau sont des moyennes sur les neuf combinaisons
des deux autres axes. L'écart-type décrit ici la dispersion du plan factoriel complet :
ce n'est ni une incertitude d'échantillonnage ni un intervalle de confiance.

Le vérificateur 4.2 reconstruit indépendamment toutes ces agrégations depuis les tables
4.1, contrôle les extrêmes et les différences, puis reproduit l'ordre exact des six
classements locaux. Ces fichiers deviennent ainsi l'entrée des figures, qui pourront
changer de forme sans modifier les calculs scientifiques.

Le script `4.3_build_bop_presentation.py` réalise cette dernière mise en forme. La
sélection des figures, leur ordre recommandé et les phrases proposées sont documentés
séparément dans [`phase4_presentation.md`](phase4_presentation.md).
