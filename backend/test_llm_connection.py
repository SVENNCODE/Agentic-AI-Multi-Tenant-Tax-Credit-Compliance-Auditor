"""
Minimal LangGraph + Claude connectivity test.
"""

import os
from typing import TypedDict

from langchain_anthropic import ChatAnthropic
from langgraph.graph import StateGraph, END
from dotenv import load_dotenv
load_dotenv()

if not os.getenv("ANTHROPIC_API_KEY"):
    raise RuntimeError(
        "ANTHROPIC_API_KEY not found in environment."
    )

class GraphState(TypedDict):
    """The state that flows through the graph."""
    question: str
    answer: str


llm = ChatAnthropic(
    model="claude-sonnet-5",
    max_tokens=200,
)


def call_claude(state: GraphState) -> GraphState:
    """The one node in this graph: sends question to Claude, stores the
    reply in answer."""
    response = llm.invoke(state["question"])
    return {"question": state["question"], "answer": response.content}

graph_builder = StateGraph(GraphState)
graph_builder.add_node("call_claude", call_claude)
graph_builder.set_entry_point("call_claude")
graph_builder.add_edge("call_claude", END)
graph = graph_builder.compile()


if __name__ == "__main__":
    result = graph.invoke({"question": "Reply with exactly: wiring confirmed", "answer": ""})
    print("---")
    print(f"Question: {result['question']}")
    print(f"Answer:   {result['answer']}")
    print("---")