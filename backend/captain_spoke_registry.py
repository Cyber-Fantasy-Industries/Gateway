# backend/captain_spoke_registry.py
from __future__ import annotations
from typing import Dict, List, Set, Optional
from loguru import logger

# Wir nutzen die Typen aus captain_hub
from backend.captain_hub import Router, Spoke  # type: ignore

class RealRouter(Router):
    """
    Einfache Router-Implementierung mit registry-basierten Kandidatenlisten.
    Anfangs leer (wie ein NullRouter), aber später leicht erweiterbar:
    - spokes['planner'] = [MyPlanner(...), ...]
    - spokes['coder']   = [MyCoder(...),   ...]
    - spokes['critic']  = [MyCritic(...),  ...]
    """
    def __init__(self, spokes: Optional[Dict[str, List[Spoke]]] = None) -> None:
        self._spokes: Dict[str, List[Spoke]] = spokes or {}

    def candidates(self, role: str, tags: Set[str]) -> List[Spoke]:  # type: ignore[override]
        # Tags können später für Filter/Scoring genutzt werden
        return list(self._spokes.get(role, []))


from typing import Dict, List
from loguru import logger
from backend.captain_hub import Spoke  # type: ignore

def load_default_spokes() -> Dict[str, List[Spoke]]:
    spokes: Dict[str, List[Spoke]] = {"planner": [], "coder": [], "critic": []}
    try:
        from backend.spokes.librarian import LibrarianPlanner  # optional, wenn vorhanden
        spokes["planner"].append(LibrarianPlanner())
        logger.info("Spoke geladen: LibrarianPlanner")
    except Exception as e:
        logger.info("Keine LibrarianPlanner verfügbar: {}", e)
    return spokes

