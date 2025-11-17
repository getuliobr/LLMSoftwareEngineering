from langchain_ollama import ChatOllama
# from langgraph.prebuilt import create_react_agent
from langchain.agents import create_agent
from langgraph.checkpoint.memory import InMemorySaver
from tools import *
import os
import logging
from logger import logger
from dotenv import load_dotenv

load_dotenv()

database_type = os.getenv('DATABASE_TYPE', 'sqlite')
database_url = os.getenv('DATABASE_URL', 'issues.sqlite')

llm = ChatOllama(
    model="gpt-oss:20b",
    reasoning="medium",
    num_ctx=128000,
    base_url='http://localhost:11434'
)

prompt = (
    f"Você é um assistente que sempre deve consultar a base de dados PostgreSQL definida em {os.getenv('DATABASE_URL')} "
    "usando a ferramenta 'sql_query_executor' com a sintaxe do PostgreSQL antes de qualquer outra ação. "
    "Sempre tente responder a pergunta consultando essa base primeiro. "
    "Somente se a informação não estiver lá, use outras ferramentas. "
    "Evite chamadas desnecessárias e pare quando tiver informações suficientes."
)
        
agent = create_agent(
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
    system_prompt=prompt
)

config = {
    "configurable": {"thread_id": "1"},
    "recursion_limit": 100
}

def main_function(question: str):
    final_answer = None
    tool_calls = 0
    for step in agent.stream(
        {"messages": [{"role": "user", "content": question}]},
        config,
        stream_mode="values",
    ):
        last_msg = step["messages"][-1]
        role = getattr(last_msg, "type", getattr(last_msg, "role", "unknown"))
        tool_name = getattr(last_msg, "name", None)

        if role == "ai":
            final_answer = last_msg.content
        
        logger.info(last_msg.content, extra={"role": role, "tool_name": tool_name})
        
        if last_msg.response_metadata:
            metada = last_msg.response_metadata
            logger.info(
                f"Detalhes da resposta:\n"
                f"Tempo total de {metada.get('total_duration', 'N/A') / 10**9} segundos\n"
                f"Tempo de carregamento do modelo: {metada.get('load_duration', 'N/A') / 10**9} segundos\n"
                f"Tokens de entrada: {metada.get('prompt_eval_count', 'N/A')}\n"
                f"Tempo para processar tokens de entrada: {metada.get('prompt_eval_duration', 'N/A') / 10**9} segundos\n"
                f"Tokens gerados: {metada.get('eval_count', 'N/A')}\n"
                f"Tempo para gerar tokens: {metada.get('eval_duration', 'N/A') / 10**9} segundos\n"
            , extra={"role": role, "tool_name": tool_name}
            )
        
        if hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
            tool_calls += 1

    logger.info(f"Quantidade total de chamadas de ferramentas feitas para a pergunta [{question}]: {tool_calls}", extra={"role": "summary", "tool_name": None})
    return final_answer