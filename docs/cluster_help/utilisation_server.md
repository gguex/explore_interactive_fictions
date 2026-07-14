# 🚀 Architecture & Workflow HPC : LLM & Git

Ce guide définit le standard de travail sur le cluster (Curnagl) pour garantir la reproductibilité du code tout en gérant les modèles IA massifs sans saturer les quotas de stockage.

## 1. La Philosophie des Dossiers

* **`/users/$USER/` (Le Cerveau - 50 GB, Sauvegardé) :** * Héberge les dépôts `Git`.
    * Contient les scripts Python (`.py`), les configurations (`.yaml`), les scripts SLURM (`.sh`).
    * Contient le dossier `boilerplates/` pour initialiser de nouveaux projets.
* **`/scratch/$USER/` (Le Muscle - Illimité, Volatil) :** * Héberge les environnements virtuels (`.venv` créés par `uv`).
    * Héberge les poids des modèles IA (Cache Hugging Face).
    * Héberge les bases de données et les résultats d'extraction.

## 2. Configuration Globale (À faire une seule fois)

Par défaut, les bibliothèques Python téléchargent les modèles dans le dossier utilisateur (`~/.cache`). Il faut forcer le système à utiliser le scratch pour éviter de saturer les 50 Go instantanément.

Ajouter ces lignes à la fin du fichier `~/.bashrc` :
```bash
# Rediriger le cache des modèles lourds vers le scratch
export HF_HOME="/scratch/$USER/.cache/huggingface"
# ou HF_HOME="/scratch/$USER/dcsr-llm/models
export UV_CACHE_DIR="/scratch/$USER/.cache/uv"
export PIP_CACHE_DIR="/scratch/$USER/.cache/pip" 

# Charger le token d'accès Hugging Face de manière sécurisée
export HF_TOKEN=$(cat /users/$USER/.config/dcsr-llm/hf_token)
```
*(Recharger le terminal avec `source ~/.bashrc` après l'ajout).*

## 3. Configuration de VS Code & Remote-SSH
Pour travailler directement sur le cluster depuis ton interface locale :

1. Ouvrir VS Code et cliquer sur l'icône verte en bas à gauche (`><`).
2. Sélectionner **Connect to Host...** -> **Add New SSH Host...**
3. Entrer la commande de connexion ciblant le nœud d'accès du cluster :
   ```bash
   ssh votre_identifiant@curnagl.dcsr.unil.ch
   ```
4. Une fois la connexion établie, cliquer sur **Open Folder** (Ouvrir le dossier).
5. **CRUCIAL :** Toujours ouvrir le dossier situé dans ton espace sécurisé `/users/` (le Cerveau), par exemple :
   ```text
   /users/votre_identifiant/projects/mon_projet_graphe
   ```
   *Ne jamais ouvrir directement le dossier du scratch dans VS Code, car l'arborescence complète du projet (incluant le code et les raccourcis vers les données) doit être pilotée depuis l'espace sauvegardé.*

## 4. Workflow : Démarrer un Nouveau Projet

Voici la procédure standard à chaque nouvelle expérience (ex: `extraction_graphe`).

### Étape A : Créer l'espace sécurisé (Le Code)
```bash
cd /users/$USER/projects/
mkdir extraction_graphe
cd extraction_graphe
git init
```

### Étape B : Créer l'espace lourd (Les Données)
```bash
mkdir -p /scratch/$USER/extraction_graphe/data
mkdir -p /scratch/$USER/extraction_graphe/results
```

### Étape C : Créer l'environnement virtuel sur le scratch
```bash
cd /scratch/$USER/extraction_graphe
module load python/3.11.14 gcc cuda
uv venv
```

### Étape D : Relier les deux mondes (Les Symlinks)
Retourner dans le dossier sécurisé et créer les raccourcis vers le scratch :
```bash
cd /users/$USER/projects/extraction_graphe

# Relier l'environnement virtuel pour que VS Code le détecte
ln -s /scratch/$USER/extraction_graphe/.venv .venv

# Relier les dossiers de données et de résultats
ln -s /scratch/$USER/extraction_graphe/data data
ln -s /scratch/$USER/extraction_graphe/results results
```

## 5. Règle d'or : Le `.gitignore`

Pour éviter que Git n'essaie de versionner des giga-octets de données ou des environnements virtuels (même symlinkés), ton fichier `.gitignore` à la racine de `/users/$USER/projects/extraction_graphe/` **doit** contenir ceci :

```text
# Environnements
.venv/
__pycache__/

# Dossiers lourds symlinkés
data/
results/
models/

# Fichiers logs SLURM
*.out
*.err

# Fichiers d'environnement locaux
.env
```

## 6. Routine de Travail dans VS Code

1. **Ouvrir le dossier :** Dans VS Code (via Remote-SSH), ouvrir **uniquement** le dossier `/users/$USER/projects/extraction_graphe/`.
2. **Sélectionner l'interpréteur :** VS Code détectera le dossier symlinké `.venv`. Choisir cet interpréteur Python. L'autocomplétion fonctionnera parfaitement.
3. **Coder et Versionner :** Écrire les scripts (`extract.py`) et faire des `git commit` / `git push` normalement.
4. **Installer des paquets :** Ouvrir le terminal dans VS Code et utiliser `uv` (qui installera les paquets physiquement sur le scratch via le symlink) :
   ```bash
   source .venv/bin/activate
   uv pip install vllm pydantic outlines
   ```
5. **Exécuter en mode interactif (Tests) :**
   ```bash  
   Sinteractive -p gpu-h100 -m 150G -G 1 -c 24
   source .venv/bin/activate
   python extract.py
   ```

## 7. Que faire si le `/scratch/` est purgé par les administrateurs ?

Pas de panique ! Puisque ton code source, ton script SLURM et ton fichier de dépendances (`pyproject.toml` ou `requirements.txt` via `uv`) sont sauvés dans `/users/` et sur GitHub :
1. Tu recrées les dossiers `data/` et `results/` sur le scratch.
2. Tu lances `uv pip install -r requirements.txt` pour recréer le `.venv` en 5 secondes.
3. Le code relancera le téléchargement du modèle (mis en cache sur le scratch) et l'expérience reprendra exactement là où elle s'était arrêtée.