# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

from langgraph.graph import StateGraph, START, END, state
from langgraph.checkpoint.memory import MemorySaver

from .types import State

# def _build_base_graph():
#     """Build and return the base state graph with all nodes and edges."""
#     builder = StateGraph(State)
    
#     return builder


# def build_graph_with_memory():
#     """Build and return the agent workflow graph with memory."""
#     # use persistent memory to save conversation history
#     # TODO: be compatible with SQLite / PostgreSQL
#     memory = MemorySaver()

#     # build state graph
#     builder = _build_base_graph()
#     return builder.compile(checkpointer=memory)


# def build_graph():
#     """Build and return the agent workflow graph without memory."""
#     # build state graph
#     builder = _build_base_graph()
#     return builder.compile()


# graph = build_graph()
