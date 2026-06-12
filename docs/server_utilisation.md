# Documentation : Extraction de Graphes Narratifs avec DCSR-LLM

Ce document décrit la procédure pour extraire automatiquement les choix et les transitions depuis les paragraphes d'un "Livre dont vous êtes le héros" vers un format structuré (JSON) en utilisant l'outil `dcsr-llm` et le modèle `Qwen/Qwen2.5-7B-Instruct`.

## 1. Architecture du projet

L'outil `dcsr-llm` exige d'être exécuté depuis son dossier racine. Pour garder notre espace de travail propre, nous utilisons un dossier séparé (`mon_projet_livre`) et un script SLURM qui crée des liens symboliques temporaires vers l'outil.

```text
/scratch/utilisateur/
├── dcsr-llm/                  <-- Dépôt Git de l'outil
└── mon_projet_livre/          <-- Espace de travail du projet
    ├── corpus_val.json        (Échantillon de test)
    ├── corpus_val_gold.json   (Corrigé du test)
    ├── corpus.json            (Données complètes de production)
    ├── config_extract_benchmark.yaml
    ├── config_extract.yaml
    ├── preprompt_corpus
    ├── run_extract.sh         (Script pour le test)
    └── run_extract_full.sh    (Script pour la production)
```

## 2. Description des fichiers de configuration

### A. Le System Prompt (`preprompt_corpus`)
Ce fichier contient les instructions pour le LLM. Il définit le rôle de l'IA et les règles strictes de classification des choix.

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
   - "stochastic": Based on a random roll (e.g., the Random Number Table).
   - "conditional": Blocked by a specific requirement (skill, stat, or item) or combat outcome.
   - "complex": When choices in the paragraph do not enter the other categories.
5. realisation_value: If transition_type= "stochastic" or "conditional", the exact raw text triggering this edge. Output null if not stochastic or conditional.
6. semantic_risk: If transition_type="explicit_choice", the subjective risk level of taking this choice. If unclear, output "neutral". If not an explicit choice, output null.
7. semantic_morality: If transition_type="explicit_choice", the subjective moral stance of taking this choice. If unclear, output "neutral". If not an explicit choice, output null.
8. semantic_action: If transition_type="explicit_choice", the cognitive level of taking this choice. If unclear, output "neutral". If not an explicit choice, output null.
9. parsing_confidence: Your confidence level in accurately extracting this edge based on the schema constraints. From 1="low confidence" to 5="completely certain".

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

### B. Le Schéma de sortie (`config_extract_benchmark.yaml` / `config_extract.yaml`)
Ce fichier YAML impose la structure JSON de sortie. 
*Note : Pour la production (`config_extract.yaml`), supprimez simplement les deux premières lignes concernant le `benchmark`.*

```yaml
task: "Extract narrative transitions and edges from gamebook paragraphs."

benchmark:
  filename: LW01.calibration_gold.json

generation:
  max_new_tokens: 1500

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

## 3. Format des données

Les textes doivent être au format JSON. Les choix sont préalablement mis en évidence avec des balises `<choice>` pour aider le modèle.

### Fichier d'entrée (`corpus_val.json` / `corpus.json`)
```json
[
  {
    "id": "21",
    "text": "Le texte du paragraphe avec <choice>le premier choix</choice> et <choice>le second choix</choice>."
  }
]
```

### Fichier de validation ("Vérité Terrain") (`corpus_val_gold.json`)
Utilisé uniquement lors de la phase de test pour évaluer le modèle. Il contient la sortie parfaite attendue.
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

## 4. Script SLURM d'exécution (`run_extract.sh`)

Ce script configure l'environnement sur Curnagl, crée les liens symboliques vers les dossiers de l'outil `dcsr-llm`, et lance l'extraction.

```bash
#SBATCH --mem 64G
#SBATCH --time 1:00:00

#SBATCH --partition gpu
#SBATCH --gres gpu:1

module purge
module load python/3.11
module load gcc
module load cuda

nvidia-smi

# Définition des chemins
PROJECT_DIR="/users/$USER/edge_extraction"
DCSR_DIR="/users/$USER/dcsr-llm"

# 1. Création de liens symboliques dans dcsr-llm vers vos fichiers
# Cela permet de respecter l'arborescence attendue par l'outil sans déplacer vos fichiers
mkdir -p "$DCSR_DIR/data/extract"
mkdir -p "$DCSR_DIR/configs"

ln -sf "$PROJECT_DIR/corpus_val.json" "$DCSR_DIR/data/extract/corpus_val.json"
ln -sf "$PROJECT_DIR/corpus_val_gold.json" "$DCSR_DIR/data/extract/corpus_val_gold.json"
ln -sf "$PROJECT_DIR/config_extract_benchmark.yaml" "$DCSR_DIR/configs/config_extract_benchmark.yaml"
ln -sf "$PROJECT_DIR/preprompt_corpus" "$DCSR_DIR/configs/preprompt_corpus"

# 2. On se déplace à la racine de l'outil (obligatoire)
cd "$DCSR_DIR"

# 3. Activation de l'environnement Python
source .venv/bin/activate

# 4. Lancement de l'extraction avec évaluation (benchmark)
dcsr-llm extract \
  --model-name Qwen/Qwen2.5-7B-Instruct \
  --corpus-name corpus_val \
  --config-file-name config_extract_benchmark \
  --preprompt-file-name preprompt_corpus \
  --think-mode off
```

Place des fichiers :

Corpus "dcsr-llm/data/extract/LW01_calibration.json"
Corpus_gold "dcsr-llm/data/extract/LW01_calibration_gold.json"
Config: "dcsr-llm/configs/LW01_calibration_config.yaml"
Preprompt: "dcsr-llm/configs/LW01_calibration_prepompt"


```bash
#SBATCH --mail-type ALL 
#SBATCH --mail-user guillaume.guex@unil.ch
#SBATCH --job-name edge_extraction
#SBATCH --output edge_extraction_%j.out
#SBATCH --nodes 1
#SBATCH --ntasks 1
#SBATCH --cpus-per-task 12
#SBATCH --mem 64G
#SBATCH --time 12:00:00
#SBATCH --partition gpu
#SBATCH --gres gpu:1

module purge
module load python/3.11.14
module load gcc
module load cuda

cd /scratch/$USER/dcsr-llm
source .venv/bin/activate

# Lancement de l'extraction SANS l'option benchmark
dcsr-llm extract \
  --model-name Qwen/Qwen3-8B \
  --corpus-name LW01_calibration.json \
  --config-file-name LW01_calibration_config \
  --preprompt-file-name LW01_calibration_prepompt \
  --think-mode off
```

## 5. Méthodologie (Workflow)

1. **Phase de Calibration (Benchmark) :**
   - Annoter manuellement ~20 paragraphes dans `corpus_val.json` et leurs corrigés dans `corpus_val_gold.json`.
   - Lancer `run_extract.sh`.
   - Analyser les erreurs dans le dossier `results/extract/`.
   - Ajuster le fichier `preprompt_corpus` si le modèle se trompe systématiquement, puis relancer.

2. **Phase de Production :**
   - Placer l'ensemble des 350 paragraphes dans `corpus.json`.
   - Utiliser `config_extract.yaml` (sans paramètre de benchmark).
   - Lancer le script SLURM de production. Le résultat final sera un fichier JSON généré contenant l'ensemble du graphe narratif prêt à être exploité.