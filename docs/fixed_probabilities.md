# Paramètres fixes de la phase 3

## 1. Rôle de ces paramètres

Les profils de joueur ne contiennent que les axes `risk`, `morality` et `action`. Les
mécaniques qui ne varient pas entre profils sont regroupées dans
`data/for_graph_model/LW01_compilation_settings.json` :

| Paramètre | Valeur LW01 | Statut |
| :--- | ---: | :--- |
| `kai_availability` | 0,5 | Hypothèse marginale |
| `combat_win_probability` | **0,833** | Calibration fondée sur les règles |
| `escape_probability` | **0,5** | Hypothèse neutre subjective |
| `has_condition` | **0,5** | Hypothèse neutre subjective |
| Affinités `matching / neutral / opposed` | 2 / 1 / 0,5 | Choix expérimental retenu pour cette itération |

Cette séparation garantit que les 27 profils ont exactement le même schéma. Une valeur
fixe peut être recalibrée sans créer un nouveau type de joueur.

Les affinités 2 / 1 / 0,5 produisent une préférence souple : face à une option
correspondante et une option directement opposée, identiques sur les autres axes, les
parts valent 80 % et 20 %. La compilation complète montre néanmoins un contraste fort
des probabilités de victoire ; ces coefficients sont donc conservés pour cette
itération.

## 2. Disponibilité des disciplines Kai

Le personnage choisit cinq disciplines parmi dix. Pour cette itération, chaque
discipline est donc considérée comme marginalement disponible avec une probabilité de
0,5. Cette valeur ne représente pas un personnage qui posséderait « la moitié » d'une
discipline, mais une population abstraite dans laquelle chaque discipline apparaît une
fois sur deux.

La comparaison de configurations Kai particulières est reportée après l'itération de
présentation.

## 3. Victoire au combat

Les règles officielles donnent une Combat Skill initiale de 10 à 19, une Endurance de
20 à 29 et une résolution par rounds à partir du Combat Ratio et de la Combat Results
Table. Elles permettent donc de calibrer le combat plus directement que les autres
paramètres. Sources : [création du personnage](https://www.projectaon.org/en/xhtml/lw/01fftd/gamerulz.htm),
[disciplines](https://www.projectaon.org/en/xhtml/lw/01fftd/discplnz.htm),
[équipement de LW01](https://www.projectaon.org/en/xhtml/lw/01fftd/equipmnt.htm) et
[combat](https://www.projectaon.org/en/xhtml/lw/01fftd/cmbtrulz.htm).

Le protocole est volontairement résumé :

1. simuler 300 000 parcours reproductibles sous le profil neutre ;
2. tirer les caractéristiques, cinq disciplines sur dix et l'équipement initial ;
3. appliquer la table de combat et les modificateurs relus dans les 29 paragraphes ;
4. conserver les blessures de combat et les soins entre les affrontements ;
5. regrouper toutes les défaites parmi les combats effectivement engagés.

Avec $D$ défaites sur $N$ combats, la probabilité lissée est :

$$
q=\frac{D}{N},\qquad v=1-q.
$$

Sur 463 609 combats, la perte moyenne vaut 0,1151 si l'Endurance est artificiellement
remise au maximum avant chaque affrontement et 0,1672 lorsque les blessures sont
conservées. L'Endurance moyenne au départ passe de 25,11 au premier combat à 20,77 au
deuxième, 17,73 au troisième et 16,50 au quatrième. La configuration retient donc les
valeurs arrondies :

$$
P(\text{perte})=0{,}167,
\qquad
\texttt{combat\_win\_probability}=0{,}833.
$$

Le script `scripts/3.2_calibrate_combat.py`, la configuration
`LW01_combat_calibration.json` et le rapport `combat_calibration.json` conservent les
détails nécessaires à la reproduction et à l'audit. La calibration reste une
approximation L2 : elle ne suit pas exactement les dégâts narratifs, l'inventaire acquis
ou les rounds précédant une fuite.

## 4. Probabilité de prendre la fuite

`escape_probability` mesure la décision de prendre une sortie de fuite lorsqu'elle est
proposée ; ce n'est pas une probabilité physique de réussir la fuite. Puisque la
propension individuelle à fuir a été exclue des profils, aucune donnée du modèle ne
permet de préférer objectivement une valeur basse ou haute.

La valeur 0,5 est retenue comme hypothèse d'indifférence entre fuir et continuer le
combat. Elle évite d'ajouter implicitement une psychologie commune à tous les profils.
Dans LW01, ce paramètre ne concerne que sept paragraphes de combat.

## 5. Probabilité de satisfaire une condition persistante

`has_condition` est un unique paramètre commun à la possession d'un objet, à un seuil de
Gold Crowns et à un seuil d'Endurance. Ces événements ont des probabilités réelles très
différentes, mais les distinguer exigerait de suivre l'état du personnage.

La valeur 0,5 est retenue comme prior binaire neutre. Elle ne prétend pas que chaque
objet est réellement possédé une fois sur deux : elle exprime l'absence d'information
dans le modèle L2 et évite une précision artificielle. Dans LW01, ce paramètre intervient
dans cinq paragraphes.

## 6. Contrôle de sensibilité

Les valeurs subjectives 0,5 sont le scénario central. Les valeurs 0,25 et 0,75 servent
de contrôle de robustesse, sans créer de profils supplémentaires. Avec
`combat_win_probability = 0.833`, la probabilité d'atteindre `Win` depuis le §1 vaut :

| Paramètre variable | 0,25 | 0,50 | 0,75 |
| :--- | ---: | ---: | ---: |
| `escape_probability`, avec `has_condition = 0.5` | 11,906 % | 11,981 % | 12,033 % |
| `has_condition`, avec `escape_probability = 0.5` | 11,666 % | 11,981 % | 12,265 % |

La variation reste faible sur LW01 : environ 0,13 point de pourcentage pour la fuite et
0,60 point pour les conditions entre les deux scénarios extrêmes. Pour la présentation,
les valeurs centrales suffisent ; le tableau de sensibilité peut rester en annexe.

## 7. Interprétation à conserver

- 0,833 est une valeur **calibrée**, mais lissée et dépendante des hypothèses décrites ;
- 0,5 pour la fuite et les conditions sont des **priors neutres**, non des observations ;
- la sensibilité sert à vérifier que les conclusions ne dépendent pas fortement de ces
  choix subjectifs ;
- une future simulation L3 pourra remplacer ces scalaires sans modifier le schéma des
  profils comportementaux.
