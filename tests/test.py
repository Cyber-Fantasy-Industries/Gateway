print("Starte Testskript...")
from autogen import ConversableAgent, LLMConfig
from autogen import GroupChat, GroupChatManager
llm_config = LLMConfig(
    model="gpt-4.1",
    api_key="",
    api_type="openai",
    base_url="https://api.openai.com/v1",
    temperature=0.7,
    timeout=60,
    max_tokens=2048,
)

with llm_config:
    agent = ConversableAgent(
        name="helpful_agent",
        system_message="You are a poetic AI assistant, respond in rhyme.",
    )
    response = agent.run(
        message="In one sentence, what's the big deal about AI?", max_turns=1
    )
    response.process()


msgs = list(response.messages)
print(f"{msgs=}")
print(f"{response.summary=}")

assert response.summary is not None, "Summary should not be None"
assert len(msgs) > 0, "Messages should not be empty"

print("MESSAGES:", response.messages)