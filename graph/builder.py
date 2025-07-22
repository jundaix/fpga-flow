# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

from langgraph.graph import StateGraph, START, END, state
from langgraph.checkpoint.memory import MemorySaver

from .types import State
from .nodes import (
    code_plan_node, 
    code_node,
    coordinator_node,
    logic_test_node,
    planner_node,
    test_plan_node,
    test_node,
    time_analyst_node,
)

def _plan_route(state: State):
    if state["next_step"] == "timing_analyse":
        return "time_analyst"
    elif state["next_step"] == "module_code_writing":
        return "code_plan"
    elif state["next_step"] == "testbench_writing":
        return "test_plan"
    elif state["next_step"] == "logic_test":
        return "logic_test"
    else:
        return END

def _build_base_graph():
    """Build and return the base state graph with all nodes and edges."""
    builder = StateGraph(State)

    builder.add_node("coordinator", coordinator_node)
    builder.add_node("planner", planner_node)
    builder.add_node("code_plan", code_plan_node)
    builder.add_node("code", code_node)
    builder.add_node("test_plan", test_plan_node)
    builder.add_node("test", test_node)
    builder.add_node("time_analyst", time_analyst_node)
    builder.add_node("logic_test", logic_test_node)

    builder.add_edge(START, "coordinator")
    builder.add_edge("coordinator", "planner")
    builder.add_conditional_edges("planner", 
                                _plan_route,
                                {
                                    "time_analyst": "time_analyst",
                                    "code_plan": "code_plan",
                                    "test_plan": "test_plan",
                                    "logic_test": "logic_test",
                                    END: END,
                                },
                                )
    builder.add_edge("time_analyst", "planner")
    builder.add_edge("code_plan", "code")
    builder.add_edge("code", "planner")
    builder.add_edge("test_plan", "test")
    builder.add_edge("test", "planner")
    builder.add_edge("logic_test", "planner")
    
    return builder


def build_graph_with_memory():
    """Build and return the agent workflow graph with memory."""
    # use persistent memory to save conversation history
    # TODO: be compatible with SQLite / PostgreSQL
    memory = MemorySaver()

    # build state graph
    builder = _build_base_graph()
    return builder.compile(checkpointer=memory)


def build_graph():
    """Build and return the agent workflow graph without memory."""
    # build state graph
    builder = _build_base_graph()
    return builder.compile()


graph = build_graph()
