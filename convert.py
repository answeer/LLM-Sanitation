from pathlib import Path
import sys
import os
from pprint import pprint
script_path = os.path.join(Path(sys.argv[0]).parent, "agent")
source_path = str(Path(script_path))
print("Source path ", source_path)
sys.path.insert(0, source_path)

current_file_path = os.path.abspath(__file__)
print("current_file_path  ", current_file_path)


from typing import Any, Generator, Optional, Sequence, Union

import mlflow
from databricks_langchain import (
    ChatDatabricks,
    VectorSearchRetrieverTool,
)
from langchain_core.language_models import LanguageModelLike
from langchain_core.runnables import RunnableConfig, RunnableLambda
from langchain_core.tools import BaseTool
from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt.tool_node import ToolNode
from mlflow.langchain.chat_agent_langgraph import ChatAgentState, ChatAgentToolNode
from mlflow.pyfunc import ChatAgent
from mlflow.types.agent import (
    ChatAgentChunk,
    ChatAgentResponse,
    ChatAgentMessage,
    ChatContext
)

from mlflow.types.chat import ChatCompletionChunk,ChatMessage, ChatCompletionResponse
try:
    from prompt_template import get_system_prompt
except:
    from RAGaaS.rag_chat.agent.prompt_template import get_system_prompt
try:
    from config import llm_endpoint_name, vs_index_name, business_prompt, description, fallback_message, mlflow_experiment_nm, experiment_dir
except:
    from RAGaaS.rag_chat.agent.config import llm_endpoint_name, vs_index_name, business_prompt, description, fallback_message, mlflow_experiment_nm, experiment_dir


LLM_ENDPOINT_NAME = llm_endpoint_name
llm = ChatDatabricks(endpoint=LLM_ENDPOINT_NAME)


def get_tools():
    tools = []
    vector_search_tools = [
        VectorSearchRetrieverTool(
            index_name=vs_index_name,
        )
    ]
    tools.extend(vector_search_tools)

    return tools


def create_tool_calling_agent(
    model: LanguageModelLike,
    tools: Union[ToolNode, Sequence[BaseTool]],
    system_prompt: Optional[str] = None,
):

    tools = get_tools()
    model = model.bind_tools(tools)

    # Define the function that determines which node to go to
    def should_continue(state: ChatAgentState):
        messages = state["messages"]
        last_message = messages[-1]
        # If there are function calls, continue. else, end
        if last_message.get("tool_calls"):
            return "continue"
        else:
            return "end"

    if system_prompt:
        preprocessor = RunnableLambda(
            lambda state: [{"role": "system", "content": system_prompt}]
            + state["messages"]
        )
    else:
        preprocessor = RunnableLambda(lambda state: state["messages"])

    def call_model(
        state: ChatAgentState,
        config: RunnableConfig,
    ):
        response = model_runnable.invoke(state, config)
        return {"messages": [response]}

    model_runnable = preprocessor | model
    workflow = StateGraph(ChatAgentState)
    workflow.add_node("agent", RunnableLambda(call_model))
    workflow.add_node("tools", ChatAgentToolNode(tools))
    workflow.set_entry_point("agent")
    workflow.add_conditional_edges(
        "agent",
        should_continue,
        {
            "continue": "tools",
            "end": END,
        },
    )
    workflow.add_edge("tools", "agent")

    return workflow.compile()


class LangGraphChatAgent(ChatAgent):
    def __init__(self, agent: CompiledStateGraph):
        self.agent = agent

         # Create a new experiment with a unique name
        experiment_name = os.path.join(
            experiment_dir, mlflow_experiment_nm
        )
        print("experiment_name ", experiment_name)
        # Create a new MLflow experiment for chat traces
        mlflow.set_experiment(experiment_name)

    def predict(
        self,
        messages: list[ChatMessage],
        context: Optional[ChatContext] = None,
        custom_inputs: Optional[dict[str, Any]] = None,
    ) -> ChatCompletionResponse:
        request = {"messages": self._convert_messages_to_dict(messages)}

        messages = []
        for event in self.agent.stream(request, stream_mode="updates"):
            for node_data in event.values():
                messages.extend(
                    ChatMessage(**msg) for msg in node_data.get("messages", [])
                )
        return ChatCompletionResponse(messages=messages)

    def predict_stream(
        self,
        messages: list[ChatMessage],
        context: Optional[ChatContext] = None,
        custom_inputs: Optional[dict[str, Any]] = None,
    ) -> Generator[ChatCompletionChunk, None, None]:
        request = {"messages": self._convert_messages_to_dict(messages)}
        for event in self.agent.stream(request, stream_mode="updates"):
            for node_data in event.values():
                yield from (
                    ChatCompletionChunk(**{"delta": msg}) for msg in node_data["messages"]
                )

system_prompt = get_system_prompt(business_prompt, fallback_message, description)
mlflow.langchain.autolog()
agent = create_tool_calling_agent(llm, [], system_prompt)
AGENT = LangGraphChatAgent(agent)
mlflow.models.set_model(AGENT)
message = {
                  "messages": [
                    {
                      "role": "user",
                      "content": "How does RAI Governance apply to the use of data analytics in audits?"
                    }
                  ]
                }
print("--------------")
print(AGENT.predict(message))
