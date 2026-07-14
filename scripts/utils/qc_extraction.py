"""Bilan de contrôle qualité d'une extraction complète d'arêtes (LLM).

Vérifie la table finale des arêtes (schéma "enhanced", cf.
docs/gamebook_data_schema.md §3) contre le corpus balisé et la table des
nœuds, puis affiche un bilan : complétude, validité des IDs, états
absorbants, cohérence des règles du schéma, distributions, atteignabilité.
"""

import csv
import json
from collections import Counter, defaultdict, deque

# --- Configuration ---
FICHIER_EDGES = "data/processed/nodes_edges/LW01/LW01_e_edges.csv"
FICHIER_CORPUS = "data/processed/nodes_edges/LW01/LW01_for_edges_extraction.json"
FICHIER_NODES = "data/processed/nodes_edges/LW01/LW01_nodes.csv"
SECTION_DEPART = "1"

CHAMPS_SEMANTIQUES = ["semantic_risk", "semantic_morality", "semantic_action"]


def controler_extraction(
    fichier_edges: str,
    fichier_corpus: str,
    fichier_nodes: str,
    section_depart: str = "1",
) -> None:
    # 1. Chargement des trois fichiers
    with open(fichier_edges, encoding="utf-8") as f:
        edges = list(csv.DictReader(f))
    with open(fichier_corpus, encoding="utf-8") as f:
        corpus = json.load(f)
    with open(fichier_nodes, encoding="utf-8") as f:
        nodes = {ligne["node_id"]: ligne for ligne in csv.DictReader(f)}

    # Nombre de balises <choice> par section (la vérité terrain du parsing)
    n_choix = {section["id"]: section["text"].count("<choice>") for section in corpus}
    ids_valides = set(n_choix)

    # --- A. Volumes et doublons ---
    print("== A. Volumes ==")
    print(f"{len(edges)} arêtes, {len(corpus)} sections, {len(nodes)} nœuds")
    paires = Counter((e["source_id"], e["target_id"]) for e in edges)
    doublons = {p: c for p, c in paires.items() if c > 1}
    print(f"Paires (source, target) dupliquées : {doublons or 'aucune'}")

    # --- B. Validité des IDs ---
    print("\n== B. Validité des IDs ==")
    src_invalides = sorted({e["source_id"] for e in edges} - ids_valides)
    tgt_invalides = sorted({e["target_id"] for e in edges} - ids_valides)
    print(f"Sources hors corpus : {src_invalides or 'aucune'}")
    print(f"Cibles hors corpus  : {tgt_invalides or 'aucune'}")

    # --- C. Complétude : nb d'arêtes vs nb de balises <choice> par section ---
    print("\n== C. Complétude (arêtes vs balises <choice>) ==")
    aretes_par_source = Counter(e["source_id"] for e in edges)
    ecarts = [
        (sid, nb, aretes_par_source.get(sid, 0))
        for sid, nb in n_choix.items()
        if aretes_par_source.get(sid, 0) != nb
    ]
    print(f"{len(ecarts)} section(s) avec écart")
    for sid, nb_balises, nb_arêtes in sorted(ecarts, key=lambda x: int(x[0])):
        print(f"   sect {sid} : {nb_balises} balises, {nb_arêtes} arêtes")

    # --- D. Sections sans arête sortante (doivent être absorbantes) ---
    print("\n== D. Sections sans arête sortante ==")
    for sid in sorted(n_choix, key=int):
        if aretes_par_source.get(sid, 0) == 0:
            statut = nodes.get(sid, {}).get("absorbing_status", "?")
            alerte = "" if n_choix[sid] == 0 else "  <-- AVAIT DES CHOIX !"
            print(f"   sect {sid} : absorbing={statut}{alerte}")

    # --- E. Cohérence des règles du schéma ---
    print("\n== E. Cohérence des règles du schéma ==")
    # realisation_value présent ssi type stochastic/conditional
    v_real = [
        e
        for e in edges
        if bool(e["realisation_value"])
        != (e["transition_type"] in ("stochastic", "conditional"))
    ]
    print(f"realisation_value incohérent avec le type : {len(v_real)}")
    # axes sémantiques présents ssi type explicit_choice (et tous les trois)
    v_sem = [
        e
        for e in edges
        if any(bool(e[c]) for c in CHAMPS_SEMANTIQUES)
        != (e["transition_type"] == "explicit_choice")
        or (
            e["transition_type"] == "explicit_choice"
            and not all(bool(e[c]) for c in CHAMPS_SEMANTIQUES)
        )
    ]
    print(f"Axes sémantiques incohérents avec le type : {len(v_sem)}")
    # une seule balise <choice> dans la section -> forced
    v_forced = [
        e
        for e in edges
        if n_choix.get(e["source_id"]) == 1 and e["transition_type"] != "forced"
    ]
    print(f"Sections à choix unique non 'forced' : {len(v_forced)}")
    for e in (v_real + v_sem + v_forced)[:10]:
        print(f"   {e['source_id']}->{e['target_id']} type={e['transition_type']}")

    # --- F. Distributions ---
    print("\n== F. Distributions ==")
    print(f"transition_type : {dict(Counter(e['transition_type'] for e in edges))}")
    explicites = [e for e in edges if e["transition_type"] == "explicit_choice"]
    print(f"explicit_choice : {len(explicites)}")
    for champ in CHAMPS_SEMANTIQUES:
        print(f"   {champ} : {dict(Counter(e[champ] for e in explicites))}")
    print(f"Warnings non vides : {sum(1 for e in edges if e['warnings'])}")

    # --- G. Nœuds jamais cibles (hors section de départ) ---
    print("\n== G. Nœuds jamais cibles ==")
    cibles = {e["target_id"] for e in edges}
    orphelins = sorted(ids_valides - cibles - {section_depart}, key=int)
    print(f"Orphelins (hors sect {section_depart}) : {orphelins or 'aucun'}")

    # --- H. Atteignabilité depuis la section de départ (BFS) ---
    print("\n== H. Atteignabilité ==")
    adjacence = defaultdict(list)
    for e in edges:
        adjacence[e["source_id"]].append(e["target_id"])
    atteints = {section_depart}
    file = deque([section_depart])
    while file:
        for voisin in adjacence[file.popleft()]:
            if voisin not in atteints:
                atteints.add(voisin)
                file.append(voisin)
    inatteignables = sorted(ids_valides - atteints, key=int)
    print(f"{len(atteints)} nœuds atteignables depuis la section {section_depart}")
    print(f"Inatteignables : {inatteignables or 'aucun'}")


if __name__ == "__main__":
    controler_extraction(
        fichier_edges=FICHIER_EDGES,
        fichier_corpus=FICHIER_CORPUS,
        fichier_nodes=FICHIER_NODES,
        section_depart=SECTION_DEPART,
    )
