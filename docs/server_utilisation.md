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
You are an expert data analyst specializing in interactive fiction and gamebook network topology.
Your task is to analyze paragraphs from a gamebook and extract all outgoing transitions (edges) to other paragraphs.

For each transition identified (often enclosed in <choice> tags), you must extract the properties according to this exact strict typology:

1. target_id: The destination paragraph number.
2. edge_text: The exact raw text of the choice presented to the player.
3. transition_type: Must be exactly one of the following:
   - "explicit_choice": Standard player decision.
   - "forced": Automatic progression with no alternatives.
   - "stochastic": Based on a random roll (Dice or Random Number Table).
   - "conditional": Blocked by a specific requirement or combat outcome.
4. stochastic_trigger: The exact raw text or range triggering this edge (e.g., "5 or above"). Output null if not stochastic.
5. condition_type: Must be exactly one of the following:
   - "none": Freely accessible or strictly stochastic.
   - "skill": Requires a specific discipline/spell.
   - "stat_check": Based on a numeric threshold.
   - "combat_victory": Requires defeating enemies.
   - "combat_evasion": Represents fleeing from combat.
   - "item": Requires a specific object.
6. condition_value: The specific requirement (e.g., "Sixth Sense"). Output null for combat outcomes or if condition_type is "none".

Ignore narrative deaths or dead-ends that do not lead to a specific target_id.
```

### B. Le Schéma de sortie (`config_extract_benchmark.yaml` / `config_extract.yaml`)
Ce fichier YAML impose la structure JSON de sortie. 
*Note : Pour la production (`config_extract.yaml`), supprimez simplement les deux premières lignes concernant le `benchmark`.*

```yaml
task: "Extract narrative transitions and edges from gamebook paragraphs."

benchmark:
  filename: corpus_val_gold.json

fields:
  - name: edges
    type: array
    description: >
      A list of all outgoing transitions connecting this node to other nodes.
      Each element in the array MUST be an object containing exactly these keys:
      - 'target_id' (string): The destination node_id.
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
  --corpus-format json \
  --result-format jsonl \
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