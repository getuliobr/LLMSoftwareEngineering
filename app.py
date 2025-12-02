import streamlit as st
from langchain_ollama import ChatOllama
from langchain.agents import create_agent
from langgraph.checkpoint.memory import InMemorySaver
from tools import *
import os
from uuid import uuid4
from dotenv import load_dotenv

load_dotenv()

st.title("Agent Chat")

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []

if "agent" not in st.session_state:
    llm = ChatOllama(
        model="gpt-oss:120b",
        reasoning="high",
        num_ctx=128000,
    )
    
    prompt = (
        f"Você é um assistente que sempre deve consultar a base de dados PostgreSQL definida em {os.getenv('DATABASE_URL')} "
        "usando a ferramenta 'sql_query_executor' com a sintaxe do PostgreSQL antes de qualquer outra ação. "
        "Sempre tente responder a pergunta consultando essa base primeiro. "
        "Somente se a informação não estiver lá, use outras ferramentas. "
        "Evite chamadas desnecessárias e pare quando tiver informações suficientes."
    )
    
    st.session_state.agent = create_agent(
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
    
    st.session_state.config = {
        "configurable": {"thread_id": str(uuid4())},
        "recursion_limit": 100
    }

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])
        
        if message["role"] == "assistant":
            if message.get("reasoning"):
                with st.expander("💭 Reasoning"):
                    st.write(message["reasoning"])
            
            if message.get("tool_calls"):
                with st.expander(f"🔧 Tool Calls ({len(message['tool_calls'])})"):
                    for i, tool in enumerate(message["tool_calls"], 1):
                        st.write(f"{i}. {tool}")
            
            if message.get("summary"):
                st.info(message["summary"])

# Chat input
if prompt := st.chat_input("Enter your question..."):
    # Add user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)
    
    # Process agent response
    with st.chat_message("assistant"):
        tool_calls_list = []
        reasoning_text = ""
        final_content = ""
        tool_call_count = 0
        
        response_container = st.empty()
        
        # Stream agent response
        for step in st.session_state.agent.stream(
            {"messages": [{"role": "user", "content": prompt}]},
            st.session_state.config,
            stream_mode="values",
        ):
            last_msg = step["messages"][-1]
            last_msg_additional_kwargs = last_msg.additional_kwargs if hasattr(last_msg, "additional_kwargs") else {}
            role = getattr(last_msg, "type", getattr(last_msg, "role", "unknown"))
            reasoning_text = last_msg_additional_kwargs.get('reasoning_content', "")
            
            # Check for tool calls
            if hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
                tool_call_count += len(last_msg.tool_calls)
                for tool_call in last_msg.tool_calls:
                    tool_name = tool_call.get("name", "unknown")
                    tool_args = tool_call.get("args", {})
                    tool_calls_list.append((reasoning_text, tool_name, tool_args))
            
            # Get final content
            if role == "ai" and hasattr(last_msg, "content"):
                final_content = last_msg.content
                response_container.write(final_content)
        
        # Show reasoning
        if reasoning_text:
            with st.expander("💭 Reasoning"):
                st.write(reasoning_text)
        
        # Show tool calls
        if tool_calls_list:
            with st.expander(f"🔧 Tool Calls ({len(tool_calls_list)})"):
                for i, (reasoning_text, tool_name, tool_args) in enumerate(tool_calls_list, 1):
                    args = ", ".join(f"{k}={v}" for k, v in tool_args.items())
                    st.write(f"{i}. {reasoning_text} -> {tool_name}({args})")
        
        # Show summary
        summary = f"Total tool calls: {tool_call_count}"
        st.info(summary)
        
        # Save to session state
        st.session_state.messages.append({
            "role": "assistant",
            "content": final_content,
            "tool_calls": tool_calls_list,
            "reasoning": reasoning_text,
            "summary": summary
        })