from reader import SCHEMA_SQL
from langchain_ollama import ChatOllama
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import InMemorySaver
from tools import *

llm = ChatOllama(
    model="gpt-oss:20b",
    reasoning="high",
    num_ctx=128000
)

agent = create_react_agent(
    llm,
    tools=[
        sql_query_executor,
        get_user_info,
        web_search,
        visit_url,
        get_repository_issue_info,
    ],
    checkpointer=InMemorySaver()
)

config = {
    "configurable": {"thread_id": "1"},
    "recursion_limit": 100
}

while msg := input("Enter your question (or 'exit' to quit): "):
    if msg.lower() == 'exit':
        break

    for step in agent.stream(
        {"messages": [{"role": "user", "content": msg}]},
        config,
        stream_mode="values",
    ):
        step["messages"][-1].pretty_print()