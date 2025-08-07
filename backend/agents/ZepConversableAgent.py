from typing import Union, Dict
from autogen import ConversableAgent
from zep_cloud.client import AsyncZep
from backend.memory.memory import Memory

class ZepConversableAgent(ConversableAgent):  # Agent with Zep memory
    """A custom ConversableAgent that integrates with Zep for long-term memory."""

    def __init__(
        self,
        name: str,
        system_message: str,
        llm_config: dict,
        function_map: dict,
        human_input_mode: str,
        zep_thread_id: str,
        zep_client: AsyncZep,
        min_fact_rating: float,
        memory: Memory,
    ):
        super().__init__(
            name=name,
            system_message=system_message,
            llm_config=llm_config,
            human_input_mode=human_input_mode,
            function_map=function_map,
        )
        self.zep_thread_id = zep_thread_id
        self.zep_client = zep_client
        self.min_fact_rating = min_fact_rating
        # Store the original system message as we will update it with relevant facts from Zep
        self.original_system_message = system_message
        self.memory = memory
        

        # Note: Persisting user messages needs to happen *before* the agent
        # processes them to fetch relevant facts. We'll handle this outside
        # the hook based on Streamlit input.

    async def on_assistant_message(self, content):
        await self.memory.persist_assistant_message(content)

    async def on_user_message(self, content):
        await self.memory.persist_user_message(content)

    async def get_context(self):
        context = await self.memory.fetch_context()
        # Systemnachricht updaten, damit der Kontext sichtbar wird!
        self.update_system_message(f"{context}\n{self.original_system_message}")
        return context
