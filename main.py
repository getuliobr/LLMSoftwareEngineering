from reader import SCHEMA_SQL
from langchain_ollama import ChatOllama
from tools import *

llm = ChatOllama(
    model="gpt-oss:20b",
    reasoning="high",
    num_ctx=128000
)

tools = {
    'sql_query_executor': sql_query_executor,
    'get_user_info': get_user_info,
    'web_search': web_search,
    'visit_url': visit_url,
    'get_repository_issue_info': get_repository_issue_info,
}

llm_with_tools = llm.bind_tools([ tool for tool in tools.values() ])

history = [
    ("system", f"You are a helpful assistant that helps people find information in a database of GitHub issues. Use the tools to answer questions. The database schema is as follows:\n```sql\n{SCHEMA_SQL}```"),
]

summarizeToolCallsSystemPrompt = ("system", "You are a helpful assistant that summarizes the tool calls so far in a concise way, focusing on the questions asked and the answers given. The summary should be brief and keeping the important details")

while msg := input("Enter your question (or 'exit' to quit): "):
    
    if msg.lower() == 'exit':
        break
    history.append(("user", msg))
    history.append(llm_with_tools.invoke(history))

    reasoning = history[-1].additional_kwargs.get('reasoning_content', '')
    if reasoning:
        reasoning = f"<think>{reasoning}</think>"

    print("Assistant:", reasoning)

    while len(history[-1].tool_calls) > 0:
        response = history[-1]
        print(response)
        tool_call_count = 0
        for tool_call in response.tool_calls:
            tool_name = tool_call["name"].lower()
            selected_tool = tools.get(tool_name)

            if not selected_tool:
                print(f"Tool {tool_name} not found. ({tool_call})")
                continue
            
            for i in range(5):
                try:
                    tool_msg = selected_tool.invoke(tool_call)
                    history.append(tool_msg)
                    tool_call_count += 1
                    break
                except Exception as e:
                    print(f"Error invoking tool {tool_name} (attempt {i+1}/3): {e}")

        history.append(llm_with_tools.invoke(history))
    
    print(history[-1].content)