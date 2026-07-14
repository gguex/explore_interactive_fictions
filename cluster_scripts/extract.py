import csv
import json
import os
from typing import Iterator

# 1. Correctifs d'infrastructure HPC
os.environ["CUDA_VISIBLE_DEVICES"] = "0"
os.environ["VLLM_GDN_PREFILL_BACKEND"] = "triton"

from schemas import ExtractionResult
from vllm import LLM, SamplingParams
from vllm.sampling_params import StructuredOutputsParams

# Variable des fichiers
SYSTEM_PROMPT_FILE = "system_prompt_final.txt"
CORPUS_FILE = "data/LW01_edge_extraction.json"
OUTPUT_CSV_FILE = "results/LW01_edge_extraction.csv"
BATCH_SIZE = 50

# Fonction utilitaire pour découper le corpus en sous-lots
def decouper_en_lots(liste: list, taille_lot: int) -> Iterator[list]:
    for i in range(0, len(liste), taille_lot):
        yield liste[i:i + taille_lot]

if __name__ == "__main__":
    
    # ==========================================
    # A. CONFIGURATION DES CHEMINS ET DU CSV
    # ==========================================
    fichier_csv = OUTPUT_CSV_FILE
    
    # Définition des colonnes du CSV
    # (doivent correspondre aux clés de ton Edge Pydantic)
    colonnes = [
        "source_id", "target_id", "edge_text", "transition_type", 
        "realisation_value", "semantic_risk", "semantic_morality", 
        "semantic_action", "warnings"
    ]
    
    # Est-ce que le fichier existe déjà ? (Pour savoir s'il faut écrire l'en-tête)
    csv_existe = os.path.isfile(fichier_csv)

    # ==========================================
    # B. LECTURE DES ENTRÉES
    # ==========================================
    print("Lecture du prompt et du corpus...")
    with open(SYSTEM_PROMPT_FILE, "r", encoding="utf-8") as f:
        SYSTEM_PROMPT = f.read()

    with open(CORPUS_FILE, "r", encoding="utf-8") as f:
        corpus = json.load(f)

    # ==========================================
    # C. INITIALISATION DE vLLM
    # ==========================================
    print("Initialisation du moteur vLLM...")
    llm = LLM(
        model="Qwen/Qwen3.6-27B",
        tensor_parallel_size=1,
        dtype="bfloat16",
        max_model_len=8192,
        gpu_memory_utilization=0.90,
        max_num_seqs=256,
    )

    sampling_params = SamplingParams(
        temperature=0.0,
        max_tokens=1500,
        structured_outputs=StructuredOutputsParams(
            json=json.dumps(ExtractionResult.model_json_schema())
        )
    )

    # ==========================================
    # D. BOUCLE D'EXTRACTION PAR LOTS & ECRITURE STREAMEE
    # ==========================================
    print(
        f"Démarrage de l'extraction de {len(corpus)} paragraphes "
        f"par lots de {BATCH_SIZE}..."
    )

    # On ouvre le CSV en mode 'a' (append).
    # Le fichier reste ouvert pendant toute la boucle.
    with open(fichier_csv, mode="a", newline="", encoding="utf-8") as f_csv:
        writer = csv.DictWriter(f_csv, fieldnames=colonnes)
        
        # Si le fichier est neuf, on écrit la ligne d'en-tête (les noms des colonnes)
        if not csv_existe:
            writer.writeheader()
            f_csv.flush() # Force l'écriture immédiate sur le disque

        compteur_paragraphes = 0
        
        # On entame la boucle des sous-lots
        for num_lot, lot in enumerate(decouper_en_lots(corpus, BATCH_SIZE), start=1):
            
            # 1. Préparation des prompts pour le lot actuel
            prompts_du_lot = []
            for paragraphe in lot:
                texte_input = json.dumps(paragraphe, ensure_ascii=False)
                prompt_formatte = (
                    f"<|im_start|>system\n{SYSTEM_PROMPT}<|im_end|>\n"
                    f"<|im_start|>user\n{texte_input}<|im_end|>\n"
                    f"<|im_start|>assistant\n"
                )
                prompts_du_lot.append(prompt_formatte)
            
            # 2. Inférence vLLM en parallèle sur tout le lot
            print(
                f"\n[Lot {num_lot}] Traitement de {len(prompts_du_lot)} paragraphes..."
            )
            outputs = llm.generate(prompts_du_lot, sampling_params)
            
            # 3. Extraction et écriture immédiate dans le CSV
            arêtes_extraites_ce_lot = 0
            for output in outputs:
                parsed_json = json.loads(output.outputs[0].text)
                edges = parsed_json.get("edges", [])
                
                for edge in edges:
                    # writer.writerow accepte directement un dictionnaire Python.
                    # Comme notre schéma Pydantic a exactement les mêmes clés que
                    # nos colonnes, le dictionnaire s'insère parfaitement.
                    writer.writerow(edge)
                    arêtes_extraites_ce_lot += 1
            
            # 4. LE RECOIN CRUCIAL : flush()
            # Par défaut, Linux garde les écritures en mémoire tampon. Cette ligne
            # force physiquement le serveur à écrire le lot sur le disque GPFS.
            f_csv.flush() 
            
            compteur_paragraphes += len(lot)
            print(
                f"[Lot {num_lot}] Sauvegardé. "
                f"({compteur_paragraphes}/{len(corpus)} paragraphes traités, "
                f"+{arêtes_extraites_ce_lot} arêtes)"
            )

    print(f"\n✅ Extraction globale terminée ! Le fichier {fichier_csv} est à jour.")