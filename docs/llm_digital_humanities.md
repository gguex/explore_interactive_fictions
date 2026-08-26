# Note méthodologique — Utilisation critique des LLM en Humanités numériques

> Statut : position de travail pour la phase 5, arrêtée le 26.08.2026. Cette note fixe
> les principes à respecter avant l'implémentation ; elle ne prétend pas résoudre à elle
> seule les débats éthiques et épistémologiques sur l'IA générative.

## 1. Position générale

Le choix d'utiliser un modèle local à poids ouverts est légitime et cohérent avec ce
projet. Il permet de limiter la dépendance à une API propriétaire, de conserver le corpus
sur une infrastructure universitaire et de figer plus précisément l'environnement
d'inférence. Il devient surtout intéressant scientifiquement lorsqu'il est présenté comme
une **contrainte méthodologique explicite**, et non comme une garantie automatique de
neutralité, de transparence ou de qualité.

La position retenue est donc la suivante :

> Le LLM n'est ni un lecteur souverain ni un critique littéraire autonome. C'est un
> instrument d'annotation interprétative, situé et imparfait, employé pour appliquer une
> grille définie par la recherche, signaler des phénomènes narratifs et proposer des
> hypothèses que la lecture humaine doit contrôler.

Cette position évite deux écueils symétriques : refuser tout calcul au motif que
l'interprétation serait irréductible, ou confondre la fluidité d'une réponse générée avec
une preuve de validité. Elle rejoint une conception des méthodes computationnelles où le
corpus, l'instrument et l'interprétation ne peuvent pas être séparés.

## 2. Ce que « local », « ouvert » et « transparent » veulent dire

Ces termes ne doivent pas être employés comme des synonymes.

| Terme | Ce qu'il autorise à dire | Ce qu'il n'autorise pas à dire |
| :--- | :--- | :--- |
| **Local** | L'inférence est exécutée sur une machine contrôlée par l'université ; les textes ne sont pas envoyés à une API commerciale. | Le modèle est sobre, neutre ou explicable. |
| **Poids ouverts** | Les poids peuvent être téléchargés, archivés et réexécutés selon leur licence. | Le code, les données d'entraînement et tout le processus de construction sont ouverts. |
| **Open source** | À réserver aux systèmes satisfaisant effectivement les conditions de leur licence et de leur documentation. | À utiliser automatiquement pour tout modèle téléchargeable. |
| **Reproductible** | Un tiers dispose des artefacts et paramètres nécessaires pour tenter de refaire l'expérience. | Les sorties seront nécessairement identiques sur tout matériel. |
| **Explicable** | Une méthode permet d'étudier certains facteurs contribuant à un résultat. | Une justification textuelle produite par le LLM révèle son raisonnement interne réel. |

Les poids ouverts apportent ici une **transparence procédurale** supérieure : choix du
modèle stable, version contrôlable, possibilité d'archiver les poids, absence de changement
silencieux d'une API et inspection complète des entrées et sorties. Ils ne rendent pas les
mécanismes internes du réseau intrinsèquement intelligibles. Cette distinction doit être
dite clairement pendant la présentation.

L'exécution locale ne garantit pas non plus un meilleur bilan environnemental. Le calcul
sur cluster devra être décrit en heures-GPU et, si l'infrastructure le fournit, en énergie
consommée. La sobriété revendiquée portera d'abord sur la petitesse du corpus, le nombre
limité d'inférences et le refus d'utiliser un modèle plus grand que nécessaire.

## 3. Pourquoi cette démarche convient au projet

Le pipeline répartit volontairement les responsabilités :

1. la phase 1 emploie un petit LLM local pour extraire des annotations vérifiables ;
2. les phases 2 à 4 reposent sur des transformations explicites, des probabilités
   documentées et des calculs déterministes ;
3. la phase 5 réintroduit un LLM local pour une lecture qualitative bornée des histoires ;
4. l'interprétation finale, la sélection des exemples et les conclusions restent humaines.

La phase 4 décrit l'architecture des possibles : accessibilité, centralité, mortalité,
sensibilité aux profils et diversité structurelle. Elle ne peut pas déterminer si les
orientations probabilistes deviennent perceptibles dans les histoires complètes, ni si
deux chemins structurellement différents produisent une impression narrative différente.
La phase 5 confronte donc les structures mesurées au texte effectivement lu le long des
trajectoires. Elle complète la phase 4 ; elle ne la valide pas rétroactivement et ne
remplace pas la lecture rapprochée.

Un sous-ensemble contrôlé des trajectoires sera lu humainement. Le bénéfice du LLM n'est
pas de supprimer cette lecture : il est de rendre la grille explicite, répétable et
réutilisable sur un corpus un peu plus large, tout en donnant accès aux accords et
désaccords entre plusieurs annotations.

## 4. Statut épistémologique des sorties

Un score produit par le modèle n'est pas « la cohérence » ou « la variation narrative ».
C'est une observation générée par un instrument particulier, sous un prompt, une version
et des paramètres particuliers. La validation doit donc porter sur le construit visé :
mesure-t-on bien ce que la grille prétend mesurer ?

Les tâches retenues exigent des preuves contrôlables dans le texte : inférer les trois axes
du profil depuis plusieurs décisions, signaler une rupture causale en citant les passages
qui se contredisent et déterminer si les décisions dessinent un profil interne stable.
Le modèle doit pouvoir s'abstenir lorsque les preuves sont insuffisantes.

Les jugements d'équité, d'adéquation choix–conséquence, de tension, de richesse et de
qualité littéraire sont exclus de cette itération. Pour la variation narrative, une
histoire isolée ne suffit pas : les profils extrêmes seront comparés par paires, tandis que
les chevauchements et distances de chemins seront calculés indépendamment. Les embeddings
sont également écartés, car ils ajouteraient un second modèle et une distance sémantique
difficile à interpréter dans ce petit plan contrôlé.

## 5. Protocole adopté pour la phase 5

La spécification complète et canonique se trouve dans `docs/phase5_protocol.md`. Les
décisions centrales sont :

- 14 histoires complètes : sept profils contrôlés et deux issues ;
- sélection sans lecture préalable du médoïde empirique de 2 000 trajectoires par cellule,
  tirées depuis la chaîne conditionnée par l'issue et comparées par distance LCS ;
- annotation locale par `Qwen/Qwen3.6-27B`, sans accès aux profils, annotations d'arêtes,
  probabilités ou indices BoP ;
- grille individuelle limitée à `risk`, `morality`, `action`, `causal_continuity` et
  `profile_coherence` ;
- six comparaisons des profils extrêmes à issue identique, évaluées dans les deux ordres ;
- quatorze histoires et six paires préannotées humainement ;
- mesures structurelles calculées séparément, puis confrontées aux annotations globales ;
- une seule diapositive éventuelle, centrée sur les résultats les plus stables.

Le prompt est traité comme un instrument de mesure : définitions, abstention, preuves et
contre-exemples courts sont fixés avant le run principal. Aucune trajectoire complète déjà
annotée n'est placée dans le prompt. Une variante prédéfinie est testée sur le sous-ensemble
humain pour estimer la sensibilité à la formulation.

## 6. Journal de reproductibilité à conserver

Pour chaque campagne d'inférence, archiver :

- identifiant exact du modèle, révision, licence, carte du modèle et empreinte des poids ;
- moteur d'inférence et versions des bibliothèques ;
- GPU, précision, quantification, fenêtre de contexte et stratégie de troncature ;
- prompt système, prompt utilisateur, schéma JSON et exemples fournis ;
- température, `top_p`, limite de tokens et graine si elle est effectivement respectée ;
- corpus d'entrée, trajectoires sélectionnées et empreintes des fichiers ;
- sorties brutes, sorties invalides et transformations de post-traitement ;
- chronologie des essais, changements de grille et raison de chaque changement ;
- annotations humaines, protocole d'arbitrage et désaccords ;
- durée, heures-GPU et énergie lorsque disponible.

La publication des réussites seules produirait une fausse impression de stabilité. Les
échecs, changements de prompt et sorties rejetées font partie de la méthode.

## 7. Formulations à employer ou à éviter

| Formulation trop forte | Formulation défendable |
| :--- | :--- |
| « Le LLM comprend ou évalue l'histoire. » | « Le modèle applique une grille définie par la recherche à une histoire reconstruite. » |
| « Le modèle local est transparent. » | « L'exécution locale et les poids ouverts améliorent l'auditabilité procédurale ; le fonctionnement interne reste opaque. » |
| « Le score mesure la cohérence. » | « Le score est une observation du modèle sur un construit opérationnalisé par la grille. » |
| « Le LLM remplace la lecture humaine. » | « Le LLM signale et annote ; la chercheuse ou le chercheur vérifie et interprète. » |
| « Le LLM confirme les indices BoP. » | « Les lectures de trajectoires sont mises en relation avec les résultats structurels de la phase 4. » |
| « Les résultats sont objectifs. » | « Les résultats sont situés, documentés, contrôlés humainement et soumis à des tests de stabilité de l'instrument. » |

Phrase courte proposée pour la présentation :

> We use a locally hosted open-weight model not as an autonomous literary critic, but as
> a reproducible annotation instrument: every claim must cite the relevant paragraphs and
> is checked against human reading.

Complément oral utile :

> Open weights improve procedural transparency and reproducibility; they do not make the
> model's internal reasoning intrinsically explainable.

## 8. Portée et limites assumées

Cette phase ne permettra pas de démontrer une qualité littéraire objective, une réception
réelle par des lecteurs, ni la diversité de toutes les expériences possibles. Elle portera
sur un livre, 14 médoïdes empiriques conditionnels, une grille et un modèle local fixé.
Chaque médoïde est reproductible avec l'échantillon et la graine archivés, mais dépend de
la distance LCS et d'un échantillon fini ; il ne représente ni une majorité de lecteurs,
ni toute la masse des chemins possibles. Les conclusions devront demeurer descriptives et
exploratoires.

Cette modestie n'affaiblit pas la recherche. Elle en constitue l'apport : montrer comment
un LLM peut être inséré dans une chaîne de preuve où ses décisions sont bornées,
référencées, contestables et comparées aux mesures structurelles comme à la lecture
humaine. Les désaccords et les échecs ne sont pas seulement des défauts techniques ; ils
peuvent révéler l'instabilité d'une catégorie, une ambiguïté du texte ou un biais de
l'instrument.

## 9. Sources et lectures mobilisées

- Andrew Piper, « [A theory-first approach toward using generative AI for humanities
  research](https://doi.org/10.1017/chr.2026.10039) », *Computational Humanities
  Research*, 2, e18, 2026. Source principale pour considérer les prompts comme des
  instruments de mesure, distinguer fluidité et validité du construit, et tester la
  robustesse plutôt que retenir seulement la configuration la plus favorable.
- Béatrice Joyeux-Prunel, « [Digital humanities in the era of digital reproducibility:
  towards a fairest and post-computational framework](https://doi.org/10.1007/s42803-023-00079-6) »,
  *International Journal of Digital Humanities*, 6, 23–43, 2024. Articule reproductibilité,
  expertise, sources, temporalité et confirmation par des méthodes non computationnelles.
- Hassan El-Hajj et al., « [Explainability and transparency in the realm of digital
  humanities: toward a historian XAI](https://doi.org/10.1007/s42803-023-00070-1) »,
  *International Journal of Digital Humanities*, 5, 299–331, 2023. Défend une interaction
  entre modèle explicable et expertise de domaine plutôt qu'une classification opaque.
- Spencer Dean Stewart et Sanskriti Sinha, « [Retrieving information from unstructured
  historical sources using large language models](https://doi.org/10.1017/chr.2025.10019) »,
  *Computational Humanities Research*, 1, e17, 2025. Étude de cas utile sur l'extraction
  structurée, la comparaison de modèles ouverts et propriétaires, les contraintes de
  contexte et la nécessité d'une validation experte.
- Songhee Han, Jueun Shin, Jiyoon Han, Bung-Woo Jun et Hilal Ayan Karabatman,
  « [How Trustworthy Are LLM-as-Judge Ratings for Interpretive Responses? Implications
  for Qualitative Research Workflows](https://arxiv.org/abs/2604.00008) », arXiv:2604.00008,
  2026. Les jugements automatiques retrouvent certaines tendances agrégées, mais divergent
  sur les nuances ; ils conviennent mieux au tri qu'au remplacement du jugement humain.
- Lianmin Zheng et al., « [Judging LLM-as-a-Judge with MT-Bench and Chatbot
  Arena](https://arxiv.org/abs/2306.05685) », NeurIPS Datasets and Benchmarks, 2023.
  Documente notamment les biais de position, de verbosité et d'auto-préférence.
- Lin Shi, Chiyu Ma, Wenhua Liang, Xingjian Diao, Weicheng Ma et Soroush Vosoughi,
  « [Judging the Judges: A Systematic Study of Position Bias in
  LLM-as-a-Judge](https://arxiv.org/abs/2406.07791) », AACL-IJCNLP, 2025. Motive
  l'inversion de l'ordre dans les comparaisons par paires et la mesure de leur stabilité.
- Dibyadyuti Roy et Aditya Deshbandhu, « [Digital
  Humanities](https://doi.org/10.1093/ywcct/mbaf019) », *The Year's Work in Critical and
  Cultural Theory*, 33(1), 36–55, 2025. Replace les débats sur l'IA, les infrastructures,
  les archives et le pouvoir dans une critique plus large de l'échelle et des métriques
  dominantes en Humanités numériques.

Liens et informations bibliographiques vérifiés le 26.08.2026.
