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
Your task is to analyze paragraphs from a gamebook and extract all outgoing transitions (edges) to other paragraphs.

You must output ONLY a valid JSON array containing one object per identified transition (enclosed in <choice> tags). Do not add any conversational text. The JSON array must match this exact schema:

[
  {
    "target_id": string,
    "edge_text": string,
    "transition_type": "explicit_choice" | "forced" | "stochastic" | "conditional",
    "stochastic_value": string | null,
    "condition_value": string | null, 
    "semantic_risk_level": 1 | 2 | 3 | 4 | 5 | null,
    "semantic_moral_stance": 1 | 2 | 3 | 4 | 5 | null,
    "semantic_cognitive_approach": 1 | 2 | 3 | 4 | 5 | null
  }
]

With the following meaning:
1. target_id: The destination paragraph number (as a string).
2. edge_text: The exact raw text of the choice presented to the player (between <choice> tags).
3. transition_type: Must be exactly one of the following:
   - "explicit_choice": Standard player decision.
   - "forced": Automatic progression with no alternatives.
   - "stochastic": Based on a random roll (e.g., the Random Number Table).
   - "conditional": Blocked by a specific requirement (skill, stat, or item) or combat outcome.
4. stochastic_value: If transition_type="stochastic", the exact raw text or range triggering this edge (e.g., "5 or above"). Output null if not stochastic.
5. condition_value: If transition_type="conditional", the exact raw text describing the condition (e.g., "If you have the golden key"). Output null if not conditional.
6. semantic_risk_level: If transition_type="explicit_choice", the subjective risk level of taking this choice. From 1="very careful choice" to 5="reckless choice". Output null otherwise.
7. semantic_moral_stance: If transition_type="explicit_choice", the subjective moral stance of taking this choice. From 1="selfish choice" to 5="Noble or altruistic choice". Output null otherwise.
8. semantic_cognitive_approach: If transition_type="explicit_choice", the cognitive level of taking this choice. From 1="instinctive/physical choice" to 5="well-thought/analytical choice". Output null otherwise.

Ignore narrative deaths or dead-ends that do not lead to a specific target_id.

[EXAMPLES (Few-Shot)]


```

Option 2 :

```text 
[SYSTEM PROMPT]
You are an expert data extraction algorithm specializing in interactive fiction and gamebooks. 
Your task is to analyze a specific choice (Edge) presented to a player, using the narrative context (Node) to determine the mechanical rules of that transition.

You must output ONLY a valid JSON object matching this schema:
{
  "transition_type": "explicit_choice" | "forced" | "stochastic" | "conditional",
  "stochastic_trigger": string or null,
  "condition_type": "none" | "skill" | "stat_check" | "combat_victory" | "combat_evasion" | "item",
  "condition_value": string or null
}

[EXAMPLES (Few-Shot)]
Input: 
Node Context: "You have ridden into the tangle of trees... Pick a number from the Random Number Table."
Edge Text: "If it is below 5, your horse has suddenly plunged into thick mud..."
Output:
{
  "transition_type": "stochastic",
  "stochastic_trigger": "below 5",
  "condition_type": "none",
  "condition_value": null
}

Input:
Node Context: "Anxious to leave this evil tomb, you examine the door for a latch."
Edge Text: "If you have the Kai Discipline of Mind Over Matter, turn to 151."
Output:
{
  "transition_type": "conditional",
  "stochastic_trigger": null,
  "condition_type": "skill",
  "condition_value": "Mind Over Matter"
}

Input:
Node Context: "Suddenly, you are faced by two snarling Giaks intent on your death."
Edge Text: "If you win, you may explore the cave further by turning to 33."
Output:
{
  "transition_type": "conditional",
  "stochastic_trigger": null,
  "condition_type": "combat_victory",
  "condition_value": null
}

[USER INPUT]
Node Context: {insérer le texte du noeud ici}
Edge Text: {insérer le texte de l'arête ici}
```

### B. Le Schéma de sortie (`config_extract_benchmark.yaml` / `config_extract.yaml`)
Ce fichier YAML impose la structure JSON de sortie. 
*Note : Pour la production (`config_extract.yaml`), supprimez simplement les deux premières lignes concernant le `benchmark`.*

```yaml
task: "Extract narrative transitions and edges from gamebook paragraphs."

benchmark:
  filename: corpus_val_gold.json

generation:
  max_new_tokens: 1500

fields:
  - name: edges
    type: array
    description: >
      A list of all outgoing transitions connecting this node to other nodes.
      Each element in the array MUST be an object containing exactly these keys:
      - 'target_id' (int): The destination node_id.
      - 'edge_text' (string): The exact raw text of the choice presented to the player.
      - 'transition_type' (string): Must be exactly explicit_choice, forced, stochastic, or conditional.
      - 'stochastic_trigger' (string): The exact raw text triggering this edge, or null if not stochastic.
      - 'condition_type' (string): Must be exactly none, skill, stat_check, combat_victory, combat_evasion, or item.
      - 'condition_value' (string): The specific requirement, or null if not applicable.
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
    "id": "21",
    "output": {
      "edges": [
        {
          "target_id": "189",
          "edge_text": "Texte du choix",
          "transition_type": "stochastic",
          "stochastic_trigger": "5 or above",
          "condition_type": "none",
          "condition_value": null
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