import polars as pl


def prepare_edge_extraction(nodes_csv: str, edges_csv: str, output_csv: str) -> None:
    """
    Reads the nodes and edges CSV files, processes the data, and saves the json file for edge extraction
    with the following schema :
    [
        {
            "id": <paragraph_id>,
            "text": <paragraph_text, with choices between <choice> tags>,
        }
    ]
    """

    # Read the nodes and edges CSV files
    df_nodes = pl.read_csv(nodes_csv)
    df_edges = pl.read_csv(edges_csv)

    # Left join edges with nodes to get the source node text
    df_edges = (
        df_edges.join(
            df_nodes.select(["node_id", "text_content"]),
            left_on="source_node_id",
            right_on="node_id",
            how="left",
        )
        .select(["source_node_id", "text_content", "edge_text"])
        .rename({"source_node_id": "node_id"})
    )

    empty_json = []
    for node_id in df_edges["node_id"].unique():
        df_node = df_edges.filter(pl.col("node_id") == node_id)
        node_text = df_node["text_content"].to_list()[0]
        edge_texts = df_node["edge_text"].to_list()
        full_text = node_text + "".join(
            [f"<choice>{edge_text}</choice>" for edge_text in edge_texts]
        )
        empty_json.append({"id": node_id, "text": full_text})

    # Save json file for each node
    with open(output_csv, "w") as f:
        pl.DataFrame(empty_json).write_json(f)


# Test the function
prepare_edge_extraction(
    nodes_csv="data/processed/nodes_edges_csv/LW01/LW01_nodes.csv",
    edges_csv="data/processed/nodes_edges_csv/LW01/LW01_edges.csv",
    output_csv="data/processed/nodes_edges_csv/LW01/LW01_for_edge_extraction.json",
)
