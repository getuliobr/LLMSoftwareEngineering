from reader import SCHEMA_SQL, load_csv_to_sqlite
from langchain_ollama import ChatOllama
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import InMemorySaver
from tools import *
import os
from langchain_core.messages import SystemMessage     # Use isso caso queira definir um prompt de sistema diferente
import os
import logging
from logger import logger

# Verifica se o banco de dados SQLite já existe; se não, carrega os dados do CSV
if not os.path.exists('issues.sqlite'):
    load_csv_to_sqlite('data/data.csv', 'issues.sqlite')
else:
    print("Banco de dados SQLite já existe. Pulando o carregamento do CSV.")


llm = ChatOllama(
    model="gpt-oss:20b",
    reasoning="medium",
    num_ctx=128000,
)

agent = create_react_agent(
    llm,
    tools=[
        sql_query_executor,
        get_user_info,
        web_search,
        github_search,
        visit_url,
        get_repository_issue_info,
    ],
    checkpointer=InMemorySaver(),
    prompt=SystemMessage(
       content=(
            "Você é um assistente que sempre deve verificar a base de dados SQLite 'issues.sqlite' "
            "usando a ferramenta 'sql_query_executor' antes de qualquer outra ação. "
            "Sempre tente responder a pergunta consultando essa base primeiro. "
            "Somente se a informação não estiver lá, use outras ferramentas. "
            "Evite chamadas desnecessárias e pare quando tiver informações suficientes."
        )
    )
)

config = {
    "configurable": {"thread_id": "1"},
    "recursion_limit": 100
}

while msg := input("Enter your question (or 'exit' to quit): "):
    if msg.lower() == 'exit':
        break
    
    tool_calls = 0
    for step in agent.stream(
        {"messages": [{"role": "user", "content": msg}]},
        config,
        stream_mode="values",
    ):
        last_msg = step["messages"][-1]
        role = getattr(last_msg, "type", getattr(last_msg, "role", "unknown"))
        tool_name = getattr(last_msg, "name", None)
        # last_msg.pretty_print()
        logger.info(last_msg.content, extra={"role": role, "tool_name": tool_name})
        
        if hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
            tool_calls += 1

    logger.info(f"Quantidade total de chamadas de ferramentas feitas para a pergunta [{msg}]: {tool_calls}", extra={"role": "summary", "tool_name": None})