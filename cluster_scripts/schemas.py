from typing import List, Literal, Optional
from pydantic import BaseModel, Field

class Edge(BaseModel):
    source_id: str
    target_id: str
    edge_text: str
    transition_type: Literal["explicit_choice", "forced", "stochastic", "conditional", "complex"]
    realisation_value: Optional[str]
    semantic_risk: Optional[Literal["cautious", "neutral", "reckless"]]
    semantic_morality: Optional[Literal["selfish", "neutral", "noble"]]
    semantic_action: Optional[Literal["physical", "neutral", "tactical"]]
    warnings: Optional[str] # Nouvelle clé ajoutée

class ExtractionResult(BaseModel):
    edges: List[Edge]