# Pipeline DCSR-LLM : Extraction de Graphes Narratifs (Gamebooks)

Ce document centralise les procédures pour extraire automatiquement la topologie (choix et transitions) des paragraphes d'un livre interactif vers un format JSON structuré, en utilisant l'outil `dcsr-llm` sur le cluster Curnagl.

## 1. Environnement et Installation (Curnagl)

### Initialisation de l'environnement virtuel

À lancer depuis le nœud d'accès pour configurer l'espace de travail :
```bash
cd /scratch/$USER/dcsr-llm
Sinteractive -m 20G -G 1
module load python/3.11.14
source .venv/bin/activate
```

### Installation des dépendances

```bash
pip install -U pip
pip install -e ".[cuda]" --extra-index-url https://download.pytorch.org/whl/cu128
pip install -e ".[dev]"
pip install -e ".[tutorial]"
```

### Vérification 

```bash
dcsr-llm check-installation
```

## Configuration du Token Hugging Face (Modèles restreints)

```bash
# 1. Crée le dossier de configuration
mkdir -p ~/.config/dcsr-llm
# 2. Sauvegarde ton token (sans guillemets ni espaces supplémentaires)
printf "%s" "ton-token-ici" > ~/.config/dcsr-llm/hf_token
# 3. Restreint les permissions de lecture à toi seul pour des raisons de sécurité
chmod 600 ~/.config/dcsr-llm/hf_token
```

## 2. Gestion des Modèles Locaux

À exécuter avec l'environnement virtuel `.venv` activé.

### Télécharger un modèle

```bash
cd /scratch/$USER/dcsr-llm
source .venv/bin/activate

dcsr-llm download --model-name Qwen/Qwen3-8B
```

Si un token est nécessaire :
```bash
export HF_TOKEN="mon_token"
dcsr-llm download --model-name nom-du-createur/nom-du-modele --use-hf-token
```

### Supprimer un modèle (Nettoyage de l'espace)

Il faut nettoyer à la fois le dossier du projet et le cache système de Hugging Face :
```bash
cd /scratch/$USER/dcsr-llm
rm -rf models/Qwen_Qwen3-8B
```

```bash
# 1. Liste les modèles présents dans ton cache pour vérifier leur nom exact
ls ~/.cache/huggingface/hub/

# 2. Supprime le dossier du modèle ciblé 
# (Note : Hugging Face remplace le "/" par "--" dans les noms de dossiers)
rm -rf ~/.cache/huggingface/hub/models--Qwen--Qwen3-8B
```

Tout désinstaller :
```bash
rm -rf ~/.cache/huggingface/hub/*
```

## 3. Architecture et Fichiers de Données

L'outil `dcsr-llm` s'exécute à la racine, mais l'architecture cible se base sur 4 fichiers clés séparés de la logique de code.

Corpus "dcsr-llm/data/extract/LW01_calibration.json"
Corpus_gold "dcsr-llm/data/extract/LW01_calibration_gold.json"
Config: "dcsr-llm/configs/LW01_calibration_config.yaml"
Preprompt: "dcsr-llm/configs/LW01_calibration_prepompt"

### Les Données (JSON)

Doivent aller dans `dcsr-llm/data/extract/` :

- `LW01_calibration.json` : Les paragraphes bruts d'entrée. Les choix sont encadrés par des balises <choice>...</choice>.

```json
[
  {
    "id": "21",
    "text": "Le texte du paragraphe avec <choice>le premier choix</choice> et <choice>le second choix</choice>."
  }
]
```

- `LW01_calibration_gold.json` : La "vérité terrain" utilisée uniquement pour le benchmark. Structure exacte : identifiant id et objet output contenant les edges.

```json
[
  {
    "id": "339",
    "output": {
      "edges": [
        {
          "source_id": "339",
          "target_id": "7",
          "edge_text": "You may evade combat by escaping through the front door at any stage of the fight, by turning to 7.",
          "transition_type": "explicit_choice",
          "realisation_value": null,
          "semantic_risk": "cautious",
          "semantic_morality": "neutral",
          "semantic_action": "physical",
          "parsing_confidence": 3
        }
      ]
    }
  }
]
```

### La Configuration (YAML)

Ce fichier va dans `dcsr-llm/configs/` : 

- `LW01_calibration_config.yaml` : Dois contenir le paramètre `benchmark: filename: ...` si c'est un benchmark. Peut contenir des modifications des paramètres du modèles (par exemple : `generation: max_new_tokens: 1500`). 

```yaml
task: "Extract narrative transitions and edges from gamebook paragraphs."

benchmark:
  filename: LW01.calibration_gold.json

generation:
  max_new_tokens: 2000

fields:
  - name: edges
    type: array
    description: >
      A list of all outgoing transitions connecting this node to other nodes.
      Each element in the array MUST be an object containing exactly these keys:
      - 'source_id' (string): The source paragraph number.
      - 'target_id' (string): The destination paragraph number.
      - 'edge_text' (string): The exact raw text of the choice presented to the player (between <choice> tags).
      - 'transition_type' (string): Must be exactly explicit_choice, forced, stochastic, conditional, or complex.
      - 'realisation_value' (string | null): If transition_type is stochastic or conditional, the exact raw text triggering this edge. Otherwise, null.
      - 'semantic_risk' (string | null): Must be cautious, neutral, reckless, or null.
      - 'semantic_morality' (string | null): Must be selfish, neutral, noble, or null.
      - 'semantic_action' (string | null): Must be physical, neutral, tactical, or null.
      - 'parsing_confidence' (int): A confidence score from 1 (low) to 5 (certain).
```

### Le Pré-prompt (TXT - non obligatoire)

Ce fichier va dans `dcsr-llm/configs/` :

- `LW01_calibration_prepompt` contient le System Prompt. C'est ici que l'on définit l'expertise (analyste de fiction interactive), le schéma JSON attendu (transition type, sémantique, etc.), les consignes strictes (gestion des null), et les exemples Few-Shot.

```text
[SYSTEM PROMPT]
You are an expert data analyst specializing in interactive fiction and gamebook network topology.
Your task is to analyze paragraphs or sections from a gamebook and extract all outgoing transitions (edges) to other paragraphs, which are enclosed in <choice> tags.

You must output ONLY a valid JSON array containing one object per identified transition (enclosed in <choice> tags). Do not add any conversational text. The JSON array must match this exact schema:

[
  {
    "source_id": string,
    "target_id": string,
    "edge_text": string,
    "transition_type": "explicit_choice" | "forced" | "stochastic" | "conditional" | "complex",
    "realisation_value": string | null,
    "semantic_risk": "cautious" | "neutral" | "reckless" | null,
    "semantic_morality": "selfish" | "neutral" | "noble" | null,
    "semantic_action": "physical" | "neutral" | "tactical" | null,
    "parsing_confidence": 1 | 2 | 3 | 4 | 5
  }
]

With the following meaning:
1. source_id: The source paragraph number (as a string).
2. target_id: The destination paragraph number (as a string).
3. edge_text: The exact raw text of the choice presented to the player (between <choice> tags).
4. transition_type: Must be exactly one of the following:
   - "explicit_choice": Standard player decision.
   - "forced": Automatic progression with no alternatives.
   - "stochastic": there is a condition based on a random roll (e.g., the Random Number Table).
   - "conditional": there is a condition with a Kai discipline, an objet, the endurence level, or a combat outcome.
   - "complex": When choices in the paragraph do not enter the other categories.
5. realisation_value: ONLY if transition_type is "stochastic" or "conditional", extract the exact raw text triggering it. CRITICAL: If the type is anything else, you MUST output null.
6. semantic_risk: CRITICAL: If transition_type is NOT "explicit_choice", you MUST output null. Otherwise, evaluate the risk: cautious, neutral, or reckless.
7. semantic_morality: CRITICAL: If transition_type is NOT "explicit_choice", you MUST output null. Otherwise, evaluate the morality: selfish, neutral, or noble.
8. semantic_action: CRITICAL: If transition_type is NOT "explicit_choice", you MUST output null. Otherwise, evaluate the cognitive level: physical, neutral, or tactical.
9. parsing_confidence: Your confidence level from 1 (low) to 5 (certain).

Ignore narrative deaths or dead-ends that do not lead to a specific target_id.

[EXAMPLES (Few-Shot)]
INPUT 1:
{
    "id": 1,
    "text": "You must make haste for you sense it is not safe to linger by the smoking remains of the ruined monastery. The black-winged beasts could return at any moment. You must set out for the Sommlending capital of Holmgard and tell the King the terrible news of the massacre: that the whole élite of Kai warriors, save yourself, have been slaughtered. Without the Kai Lords to lead her armies, Sommerlund will be at the mercy of their ancient enemy, the Darklords. Fighting back tears, you bid farewell to your dead kinsmen. Silently, you promise that their deaths will be avenged. You turn away from the ruins and carefully descend the steep track. At the foot of the hill, the path splits into two directions, both leading into a large wood. <choice>If you wish to use your Kai Discipline of Sixth Sense, turn to 141.</choice> <choice>If you wish to take the right path into the wood, turn to 85.</choice> <choice>If you wish to follow the left track, turn to 275.</choice>"
}

OUTPUT 1:
[
  {
    "source_id": "1",
    "target_id": "141",
    "edge_text": "If you wish to use your Kai Discipline of Sixth Sense, turn to 141.",
    "transition_type": "conditional",
    "realisation_value": "If you wish to use your Kai Discipline of Sixth Sense", 
    "semantic_risk": null,
    "semantic_morality": null,
    "semantic_action": null,
    "parsing_confidence": 4
  },
  {
    "source_id": "1",
    "target_id": "85",
    "edge_text": "If you wish to take the right path into the wood, turn to 85.",
    "transition_type": "explicit_choice",
    "realisation_value": null,
    "semantic_risk": "neutral",
    "semantic_morality": "neutral",
    "semantic_action": "neutral",
    "parsing_confidence": 4
  },
  {
    "source_id": "1",
    "target_id": "275",
    "edge_text": "If you wish to follow the left track, turn to 275.",
    "transition_type": "explicit_choice",
    "realisation_value": null,
    "semantic_risk": "neutral",
    "semantic_morality": "neutral",
    "semantic_action": "neutral",
    "parsing_confidence": 4
  }
]

INPUT 2:
{
    "id": 2,
    "text": "As you dash through the thickening trees, the shouts of the Giaks begin to fade behind you. You have nearly outdistanced them completely, when you crash headlong into a tangle of low branches. Pick a number from the Random Number Table. <choice>If you have picked a number 0–4, turn to 343.</choice> <choice>If you have picked a number 5–9, turn to 276.</choice>"
}

OUTPUT 2:
[
  {
    "source_id": "2",
    "target_id": "343",
    "edge_text": "If you have picked a number 0–4, turn to 343.",
    "transition_type": "stochastic",
    "realisation_value": "If you have picked a number 0–4",
    "semantic_risk": null,
    "semantic_morality": null,
    "semantic_action": null,
    "parsing_confidence": 5
  },
  {
    "source_id": "2",
    "target_id": "276",
    "edge_text": "If you have picked a number 5–9, turn to 276.",
    "transition_type": "stochastic",
    "realisation_value": "If you have picked a number 5–9",
    "semantic_risk": null,
    "semantic_morality": null,
    "semantic_action": null,
    "parsing_confidence": 5
  }
]

INPUT 97:
{
    "id": 97,
    "text": "Ahead of you, you can see a fierce battle raging across a stone bridge. The clash of steel and the cries of men and beasts echo through the forest. In the midst of the fighting, you see Prince Pelathar, the King’s son. He is in combat with a large grey Gourgaz who is wielding a black axe above his scaly head. Suddenly, the Prince falls wounded—a black arrow in his side. <choice>If you wish to defend the fallen Prince, turn to 255.</choice> <choice>If you wish to run into the forest, turn to 306.</choice>"
}

OUTPUT 97:
[
  {
    "source_id": "97",
    "target_id": "255",
    "edge_text": "If you wish to defend the fallen Prince, turn to 255.",
    "transition_type": "explicit_choice",
    "realisation_value": null, 
    "semantic_risk": "reckless",
    "semantic_morality": "noble",
    "semantic_action": "physical",
    "parsing_confidence": 4
  },
  {
    "source_id": "97",
    "target_id": "306",
    "edge_text": "If you wish to run into the forest, turn to 306.",
    "transition_type": "explicit_choice",
    "realisation_value": null, 
    "semantic_risk": "cautious",
    "semantic_morality": "selfish",
    "semantic_action": "neutral",
    "parsing_confidence": 4
  }
]

INPUT 276:
{
    "id": 276,
    "text": "Reaching for your weapon you manage to hack your way through the tangle of wood and twisted branches to the clearer forest beyond. Your cloak is torn in several places and your right leg is badly bruised above the knee. <choice>Lose 1 ENDURANCE point and turn to 213.</choice>"
}

OUTPUT 276:
[
  {
    "source_id": "276",
    "target_id": "213",
    "edge_text": "Lose 1 ENDURANCE point and turn to 213.",
    "transition_type": "forced",
    "realisation_value": null, 
    "semantic_risk": null,
    "semantic_morality": null,
    "semantic_action": null,
    "parsing_confidence": 5
  }
]

INPUT 339:
{
    "id": 339,
    "text": "You quickly sidestep just as a long dagger shatters the glass top of the counter. A swarthy youth is attacking you and you must fight him. Robber: COMBAT SKILL 13   ENDURANCE 20 <choice>If you kill him within 4 rounds of Combat, turn to 94.</choice> <choice>If you are still fighting after 4 rounds of Combat, turn to 203.</choice> <choice>You may evade combat by escaping through the front door at any stage of the fight, by turning to 7.</choice>"
}

OUTPUT 339:
[
  {
    "source_id": "339",
    "target_id": "94",
    "edge_text": "If you kill him within 4 rounds of Combat, turn to 94.",
    "transition_type": "complex",
    "realisation_value": null, 
    "semantic_risk": null,
    "semantic_morality": null,
    "semantic_action": null,
    "parsing_confidence": 3
  },
  {
    "source_id": "339",
    "target_id": "203",
    "edge_text": "If you are still fighting after 4 rounds of Combat, turn to 203.",
    "transition_type": "complex",
    "realisation_value": null, 
    "semantic_risk": null,
    "semantic_morality": null,
    "semantic_action": null,
    "parsing_confidence": 3
  },
  {
    "source_id": "339",
    "target_id": "7",
    "edge_text": "You may evade combat by escaping through the front door at any stage of the fight, by turning to 7.",
    "transition_type": "explicit_choice",
    "realisation_value": null,
    "semantic_risk": "cautious",
    "semantic_morality": "neutral",
    "semantic_action": "physical",
    "parsing_confidence": 3
  }
]
```

## 4. Lancement : Script SLURM

Le script SLURM pour lancer les calculs. Il est dans `~/edge_extraction/` et doit être soumis avec `sbatch LW01_calibration.sh` :

```bash
#!/bin/bash -l

#SBATCH --mail-type ALL 
#SBATCH --mail-user guillaume.guex@unil.ch
#SBATCH --job-name edge_extraction
#SBATCH --output edge_extraction_%j.out
#SBATCH --nodes 1
#SBATCH --ntasks 1
#SBATCH --cpus-per-task 32
#SBATCH --mem 250G
#SBATCH --time 12:00:00
#SBATCH --partition gpu-h100
#SBATCH --gres=gpu:1

module purge
module load python/3.11.14
module load gcc
module load cuda

cd /scratch/$USER/dcsr-llm
source .venv/bin/activate

dcsr-llm extract \
  --model-name Qwen/Qwen3.6-27B \
  --corpus-name LW01_calibration \
  --config-file-name LW01_calibration_config \
  --preprompt-file-name LW01_calibration_preprompt \
  --think-mode off
```

## 5. Méthodologie (Workflow)

1. **Phase de Calibration (Benchmark) :**
   - Annoter manuellement ~20 paragraphes dans `LW01_calibration.json` et leurs corrigés dans `LW01_calibration_gold.json`.
   - Lancer `LW01_calibration.sh`.
   - Analyser les erreurs dans le dossier `results/extract/`.
   - Ajuster le fichier `LW01_calibration_prepompt` si le modèle se trompe systématiquement, puis relancer.

2. **Phase de Production :**
   - Placer l'ensemble des 350 paragraphes dans `LW01_full.json`.
   - Utiliser `LW01_full_config.yaml` (sans paramètre de benchmark)
   - Lancer le script SLURM de production. Le résultat final sera un fichier JSON généré contenant l'ensemble du graphe narratif prêt à être exploité.


## 6. Aide-mémoire SLURM 

Trouver les jobs :
```bash
Squeue
```

Arrêter un job :
```bash
scancel <job_id>
``` 

Arrêter tout :
```bash
scancel -u $USER
```