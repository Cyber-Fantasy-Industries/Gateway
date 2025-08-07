# backend/memory/memory.py
"""
Komplettes Zep Graph Memory Interface:

- create_graph, list_graphs, update_graph, clone_graph
- set_ontology (Custom Entities/Edges)
- add_text, add_fact (User- oder Group-Graph)
- search (einfach & advanced)
- get_node, get_edge, get_node_edges
- delete_edge, delete_episode
- list_user_nodes, list_graph_nodes, list_user_edges, list_graph_edges
- Future: Node-Delete, Bulk-Operationen
"""
import inspect
from loguru import logger
from zep_autogen.memory import ZepMemory
from zep_cloud.client import AsyncZep
from typing import Any, List, Optional

from zep_cloud.types import (
    SuccessResponse,
    AddTripleResponse,
    EntityNode,
    EntityEdge,
    GraphSearchResults,
    GraphListResponse,
    CloneGraphResponse
)
from autogen_core.memory import MemoryContent, MemoryMimeType
class Memory(ZepMemory):
    """
    Erweitert ZepMemory um explizite Graph-Funktionen (Triples, Suche, etc).
    Nutzt async API. Kompatibel mit Autogen UND Custom-Backend.
    """
    def __init__(
        self,
        client: AsyncZep,
        user_id: Optional[str] = None,
        thread_id: Optional[str] = None,
        graph_id: Optional[str] = None,
        async_mode: Optional[bool] = None,
    ):
        if not (user_id or graph_id):
            raise ValueError("Memory: Either user_id or graph_id must be set!")
        user_id_ = user_id if user_id is not None else "__GROUP__"
        super().__init__(client, user_id=user_id_, thread_id=thread_id)

        self.graph_id = graph_id
        # self._client und self._thread_id werden von der Basisklasse gesetzt!
        if async_mode is not None:
            self.async_mode = async_mode
        else:
            add_func = getattr(self._client.thread, "add_messages", None)
            self.async_mode = inspect.iscoroutinefunction(add_func)


    def _target_args(self) -> dict[str, str]:
        """Return the correct target args for Zep API calls (user_id or graph_id)"""
        if self._user_id:
            return {"user_id": self._user_id}
        elif self.graph_id:
            return {"graph_id": self.graph_id}
        else:
            raise ValueError("Either user_id or graph_id must be set.")

    async def persist_assistant_message(self, content: str):
        await self.add(
            MemoryContent(content=content, mime_type=MemoryMimeType.TEXT, metadata={"role": "assistant"})
        )


    async def persist_user_message(self, content: str):
        await self.add(
            MemoryContent(content=content, mime_type=MemoryMimeType.TEXT, metadata={"role": "user"})
        )

    async def fetch_context(self) -> str:
        logger.info(f"[Memory] fetch_context (thread={self._thread_id})")
        try:
            if self.async_mode:
                thread = await self._client.thread.get(self._thread_id)
            else:
                thread = self._client.thread.get(self._thread_id)
            logger.info(f"[Memory] fetch_context: thread.context={getattr(thread, 'context', None)}")
            context = getattr(thread, "context", None)
            if context:
                return context
            # Fallback: Kontext aus Messages zusammensetzen!
            messages = getattr(thread, "messages", [])
            # Hole z.B. die letzten 3 User- oder Assistant-Messages:
            last_msgs = [m.content for m in messages[-3:]]
            fallback_context = "\n".join(last_msgs)
            logger.info(f"[Memory] fetch_context: fallback_context={fallback_context!r}")
            return fallback_context or "No facts recalled."
        except Exception as e:
            logger.error(f"[Memory] fetch_context ERROR: {e}")
            return "[Fehler beim Laden des Kontextes]"

        
    async def debug_fetch_all_messages(self):
        logger.info(f"[Memory] DEBUG: fetching all messages for thread {self._thread_id}")
        try:
            if self.async_mode:
                thread = await self._client.thread.get(self._thread_id)
            else:
                thread = self._client.thread.get(self._thread_id)
            logger.info(f"[Memory] DEBUG: thread={thread}")
            # Versuche, alle Messages zu loggen:
            msgs = getattr(thread, "messages", None)
            if msgs is None:
                logger.warning("[Memory] DEBUG: No messages attribute found in thread!")
            else:
                logger.info(f"[Memory] DEBUG: {len(msgs)} messages found: {msgs}")
        except Exception as e:
            logger.error(f"[Memory] DEBUG: fetch_all_messages ERROR: {e}")
            
    async def add_fact(
        self,
        fact: str,
        fact_name: str,
        target: str,
        source: Optional[str] = None,
        valid_at: Optional[str] = None,
        invalid_at: Optional[str] = None,
    ) -> AddTripleResponse:
        """
        Fügt ein Fakt-Triple zum passenden Graph hinzu (user_id oder graph_id).
        """
        target_args = self._target_args()  # {'user_id': ...} oder {'graph_id': ...}
        params = {
            "fact": fact,
            "fact_name": fact_name,
            "target_node_name": target,
        }
        if source:
            params["source_node_name"] = source
        if valid_at:
            params["valid_at"] = valid_at
        if invalid_at:
            params["invalid_at"] = invalid_at
        params.update(target_args)  # Nur user_id oder graph_id!
        result = await self._client.graph.add_fact_triple(**params)
        return result



    # async def add_text(self, text: str, type: str = "text", **kwargs) -> dict:
    #     """
    #     Fügt freien Text als Datenobjekt in den Graph ein.
    #     """
    #     return await self._client.graph.add(
    #         data=text,
    #         type=type,
    #         **self._target_args(),
    #         **kwargs
    #     )


    async def search(
        self,
        query: str,
        scope: str = "edges",
        search_filters: Optional[dict] = None,
        limit: int = 10,
        **kwargs
    ) -> GraphSearchResults:
        """
        Suche im Graph nach Fakten, Knoten, Kanten usw.
        """
        params = dict(
            query=query,
            scope=scope,
            limit=limit,
            **self._target_args(),
        )
        if search_filters:
            params["search_filters"] = search_filters
        params.update(kwargs)
        return await self._client.graph.search(**params)

    
    async def advanced_search(
        self,
        query: str,
        scope: str = "edges",
        search_filters: Optional[dict] = None,
        limit: int = 10,
        min_fact_rating: Optional[float] = None,
        reranker: Optional[str] = None,
        center_node_uuid: Optional[str] = None,
        **kwargs
    ) -> GraphSearchResults:
        """
        Erweiterte Suche mit weiteren Parametern.
        """
        params = dict(
            query=query,
            scope=scope,
            limit=limit,
            **self._target_args()
        )
        if search_filters:
            params["search_filters"] = search_filters
        if min_fact_rating is not None:
            params["min_fact_rating"] = min_fact_rating
        if reranker:
            params["reranker"] = reranker
        if center_node_uuid:
            params["center_node_uuid"] = center_node_uuid
        params.update(kwargs)
        return await self._client.graph.search(**params)


    async def get_node(self, uuid: str) -> EntityNode:
        """
        Holt einen Knoten (Node) aus dem Graph nach UUID.
        """
        return await self._client.graph.node.get(uuid_=uuid)


    async def get_edge(self, uuid: str) -> EntityEdge:
        """
        Holt eine Kante (Edge) aus dem Graph nach UUID.
        """
        return await self._client.graph.edge.get(uuid_=uuid)


    async def get_node_edges(self, node_uuid: str) -> List[EntityEdge]:
        """
        Holt alle Kanten eines Knotens (Node) im Graph nach Node-UUID.
        """
        return await self._client.graph.node.get_edges(node_uuid=node_uuid)

    # Graph-Verwaltung
    async def create_graph(
        self,
        graph_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None
    ) -> Any:
        """
        Legt einen neuen Gruppen-Graph an.
        """
        return await self._client.graph.create(graph_id=graph_id, name=name, description=description)

    async def list_graphs(self) -> GraphListResponse:
        """
        Listet alle Gruppen-Graphs (nicht User-Graphs).
        """
        return await self._client.graph.list_all()

    async def update_graph(self, graph_id: str, **kwargs) -> dict:
        """
        Aktualisiert einen Graph (z.B. Beschreibung, fact_rating_instruction).
        """
        return await self._client.graph.update(graph_id=graph_id, **kwargs)

    async def clone_graph(
        self,
        source_graph_id: Optional[str] = None,
        source_user_id: Optional[str] = None,
        target_graph_id: Optional[str] = None,
        target_user_id: Optional[str] = None
    ) -> CloneGraphResponse:
        """
        Klont einen Graph (nach ID oder User).
        """
        return await self._client.graph.clone(
            source_graph_id=source_graph_id,
            source_user_id=source_user_id,
            target_graph_id=target_graph_id,
            target_user_id=target_user_id
        )


    # Ontologie (Custom Entities & Edges)
    async def set_ontology(self, entities: dict, edges: dict) -> dict:
        """
        Setzt eine benutzerdefinierte Ontologie (Entities und Edges) für den Graph.
        """
        return await self._client.graph.set_ontology(entities=entities, edges=edges)

    # Episoden-Management
    async def delete_episode(self, uuid: str) -> SuccessResponse:
        """
        Löscht eine Graph-Episode (entfernt verbundene Fakten/Knoten, falls keine weiteren Links existieren).
        """
        return await self._client.graph.episode.delete(uuid_=uuid)


    # Edge- und Node-Liste, Admin
    async def list_user_nodes(
        self,
        user_id: Optional[str] = None,
        limit: int = 100,
        uuid_cursor: Optional[str] = None
    ) -> dict:
        """
        Listet alle Knoten für einen User-Graph.
        """
        user_id = user_id or self._user_id
        return await self._client.graph.node.get_by_user_id(
            user_id=user_id, limit=limit, uuid_cursor=uuid_cursor
        )

    async def list_graph_nodes(
        self,
        graph_id: Optional[str] = None,
        limit: int = 100,
        uuid_cursor: Optional[str] = None
    ) -> dict:
        """
        Listet alle Knoten für einen Gruppen-Graph.
        """
        graph_id = graph_id or self.graph_id
        if graph_id is None:
            raise ValueError("graph_id muss gesetzt sein!")
        return await self._client.graph.node.get_by_graph_id(
            graph_id=graph_id, limit=limit, uuid_cursor=uuid_cursor
        )

    async def list_user_edges(
        self,
        user_id: Optional[str] = None,
        limit: int = 100,
        uuid_cursor: Optional[str] = None
    ) -> dict:
        """
        Listet alle Kanten für einen User-Graph.
        """
        user_id = user_id or self._user_id
        return await self._client.graph.edge.get_by_user_id(
            user_id=user_id, limit=limit, uuid_cursor=uuid_cursor
        )

    async def list_graph_edges(
        self,
        graph_id: Optional[str] = None,
        limit: int = 100,
        uuid_cursor: Optional[str] = None
    ) -> dict:
        """
        Listet alle Kanten für einen Gruppen-Graph.
        """
        graph_id = graph_id or self.graph_id
        if graph_id is None:
            raise ValueError("graph_id muss gesetzt sein!")
        return await self._client.graph.edge.get_by_graph_id(
            graph_id=graph_id, limit=limit, uuid_cursor=uuid_cursor
        )


    async def delete_edge(self, uuid: str) -> SuccessResponse:
        """
        Löscht eine Fakt-Kante (Edge) aus dem Graph.
        """
        return await self._client.graph.edge.delete(uuid_=uuid)

        # (Node-Delete kommt in Zukunft; aktuell über delete_episode, falls du die Episode kennst.)

        # Helper: Alle Methoden für die Custom-Schnittstelle können beliebig ergänzt werden.

