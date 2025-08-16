"""
Zep Memory integration for AutoGen.

This module provides memory classes that integrate Zep with AutoGen's memory system.
"""

import logging
import uuid
from typing import Any

from autogen_core import CancellationToken
from autogen_core.memory import (
    Memory,
    MemoryContent,
    MemoryMimeType,
    MemoryQueryResult,
    UpdateContextResult,
)
from autogen_core.model_context import ChatCompletionContext
from autogen_core.models import SystemMessage
from zep_cloud.client import AsyncZep
from zep_cloud.types import Message


class ZepMemory(Memory):
    """
    A memory implementation that integrates with Zep for persistent storage
    and retrieval of conversation context and agent memories.

    v3 notes:
    - Use thread.add_messages for chat history
    - Use thread.get_user_context(..., mode="basic") for summarized context (no .messages!)
    - If recent messages are needed, call thread.get(thread_id) separately.
    - Graph APIs are used for user-graph data (facts/nodes/episodes).
    """

    def __init__(
        self, client: AsyncZep, user_id: str, thread_id: str | None = None, **kwargs: Any
    ) -> None:
        if not isinstance(client, AsyncZep):
            raise TypeError("client must be an instance of AsyncZep")
        if not user_id:
            raise ValueError("user_id is required")

        self._client = client
        self._user_id = user_id
        self._thread_id = thread_id
        self._config = kwargs

        self._logger = logging.getLogger(__name__)

    async def add(
        self, content: MemoryContent, cancellation_token: CancellationToken | None = None
    ) -> None:
        supported_mime_types = {MemoryMimeType.TEXT, MemoryMimeType.MARKDOWN, MemoryMimeType.JSON}
        if content.mime_type not in supported_mime_types:
            raise ValueError(
                f"Unsupported mime type: {content.mime_type}. "
                f"ZepMemory only supports: {', '.join(str(mt) for mt in supported_mime_types)}"
            )

        metadata_copy = content.metadata.copy() if content.metadata else {}
        content_type = metadata_copy.get("type", "data")

        if content_type == "message":
            if self._thread_id:
                # will raise if not found → lets us detect config errors
                await self._client.thread.get(self._thread_id)

            if not self._thread_id:
                self._thread_id = f"thread_{uuid.uuid4().hex[:16]}"
                await self._client.thread.create(thread_id=self._thread_id, user_id=self._user_id)

            role = metadata_copy.get("role", "user")
            name = metadata_copy.get("name")
            msg = Message(name=name, content=str(content.content), role=role)

            await self._client.thread.add_messages(thread_id=self._thread_id, messages=[msg])

        elif content_type == "data":
            mime_to_data_type: dict[MemoryMimeType, str] = {
                MemoryMimeType.TEXT: "text",
                MemoryMimeType.MARKDOWN: "text",
                MemoryMimeType.JSON: "json",
            }
            data_type = mime_to_data_type.get(content.mime_type, "text")
            await self._client.graph.add(user_id=self._user_id, type=data_type, data=str(content.content))

        else:
            raise ValueError(
                f"Unsupported metadata type: {content_type}. Supported types: 'message', 'data'"
            )

    async def query(
        self,
        query: str | MemoryContent,
        cancellation_token: CancellationToken | None = None,
        **kwargs: Any,
    ) -> MemoryQueryResult:
        if isinstance(query, MemoryContent):
            query_str = str(query.content)
        else:
            query_str = query

        limit = kwargs.pop("limit", 5)
        results: list[MemoryContent] = []

        try:
            graph_results = await self._client.graph.search(
                user_id=self._user_id, query=query_str, limit=limit, **kwargs
            )

            edges = getattr(graph_results, "edges", None) or []
            for edge in edges:
                    results.append(
                        MemoryContent(
                            content=edge.fact,
                            mime_type=MemoryMimeType.TEXT,
                            metadata={
                                "source": "user_graph",
                                "edge_name": edge.name,
                                "edge_attributes": edge.attributes or {},
                                "created_at": edge.created_at,
                                "expired_at": edge.expired_at,
                                "valid_at": edge.valid_at,
                                "invalid_at": edge.invalid_at,
                            },
                        )
                    )
            nodes = getattr(graph_results, "nodes", None) or []
            for node in nodes:
                    results.append(
                        MemoryContent(
                            content=f"{node.name}:\n {node.summary}",
                            mime_type=MemoryMimeType.TEXT,
                            metadata={
                                "source": "user_graph",
                                "node_name": node.name,
                                "node_attributes": node.attributes or {},
                                "created_at": node.created_at,
                            },
                        )
                    )
            episodes = getattr(graph_results, "episodes", None) or []
            for episode in episodes:
                    # v3: role_type → role
                    results.append(
                        MemoryContent(
                            content=episode.content,
                            mime_type=MemoryMimeType.TEXT,
                            metadata={
                                "source": "user_graph",
                                "episode_type": episode.source,
                                "episode_role": getattr(episode, "role", None),
                                "created_at": episode.created_at,
                            },
                        )
                    )
        except Exception as e:
            self._logger.error(f"Error querying Zep memory: {e}")

        return MemoryQueryResult(results=results)

    async def update_context(self, model_context: ChatCompletionContext) -> UpdateContextResult:
        """
        v3-safe:
        - Pull summarized context via thread.get_user_context(..., mode="basic")
        - Optionally pull last messages via thread.get(thread_id) (if available)
        - Inject a single SystemMessage into model_context
        """
        try:
            msgs = await model_context.get_messages()
            if not msgs:
                return UpdateContextResult(memories=MemoryQueryResult(results=[]))

            if not self._thread_id:
                return UpdateContextResult(memories=MemoryQueryResult(results=[]))

            # 1) Summarized context (NO .messages in v3)
            ctx_resp = await self._client.thread.get_user_context(thread_id=self._thread_id, mode="basic")
            memory_contents: list[MemoryContent] = []
            parts: list[str] = []
            context_text = getattr(ctx_resp, "context", None)
            if context_text:
                # hier ist context_text Optional[str] -> in str umwandeln
                context_text_str = str(context_text)
                memory_contents.append(MemoryContent(
                    content=context_text_str,
                    mime_type=MemoryMimeType.TEXT,
                    metadata={"source": "thread_context"},
                ))
                parts.append(f"Memory context: {context_text_str}")

            # Nachrichtenverlauf getrennt holen (best‑effort)
            try:
                thread_resp = await self._client.thread.get(self._thread_id)
                recent = getattr(thread_resp, "messages", None) or []
                last_10 = recent[-10:]
                if last_10:
                    history_lines = [f"{m.role}: {getattr(m, 'content', '')}" for m in last_10 if getattr(m, 'content', None)]
                    if history_lines:
                        parts.append("Recent conversation:\n" + "\n".join(history_lines))
            except Exception as e:
                self._logger.debug(f"Skipping recent messages fetch: {e}")

            if parts:
                await model_context.add_message(SystemMessage(content="\n\n".join(parts)))

            return UpdateContextResult(memories=MemoryQueryResult(results=memory_contents))

        except Exception as e:
            self._logger.error(f"Error updating context with Zep memory: {e}")
            return UpdateContextResult(memories=MemoryQueryResult(results=[]))


    async def clear(self) -> None:
        """
        Clear all memories from Zep storage by deleting the session.

        This will delete the entire session and all its messages.
        Note: This operation cannot be undone.
        """
        try:
            # Delete the session - this clears all messages and memory for this session
            if self._thread_id:
                await self._client.thread.delete(thread_id=self._thread_id)

        except Exception as e:
            self._logger.error(f"Error clearing Zep memory: {e}")
            raise

    async def close(self) -> None:
        """
        Clean up Zep client resources.

        Note: This method does not close the AsyncZep instance since it was
        provided externally. The caller is responsible for managing the client lifecycle.
        """
        # The client was provided externally, so we don't close it here
        # The caller is responsible for closing the client when appropriate
        pass
