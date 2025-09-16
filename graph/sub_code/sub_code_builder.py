"""
 用于构造编写代码子任务的图
"""

from langgraph.graph import StateGraph, START, END, state
from langgraph.checkpoint.memory import MemorySaver

from .sub_code_type import State_coder
from .code_nodes import code_writing_node, code_syntax_judge_node, code_logic_judge_node
from .code_nodes import end_saving_node

def _code_writing_route(state: State_coder):
    if state["is_else_error"]:
        if state["trying_times"] >= state["MAX_TRY_TIMES"]:
            return "end"
        else:
            return "code_writer"
    else:
        return "code_syntax"

def _syntax_judge_route(state: State_coder):
    if state["is_syntax_error"] or state["is_else_error"]:
        if state["trying_times"] >= state["MAX_TRY_TIMES"]:
            return "end"
        else:
            return "code_writer"
    else:
        return "code_logic"

def _logic_judge_route(state: State_coder):
    if state["is_logic_error"] or state["is_else_error"]:
        if state["trying_times"] >= state["MAX_TRY_TIMES"]:
            return "end"
        elif state["is_else_error"]:
            return "code_logic"
        else:
            return "code_writer"
    else:
        return "end"

def _build_graph_code():
    '''
        构建用于完成编写代码的图
    '''
    builder = StateGraph(State_coder)

    builder.add_node("code_writer", code_writing_node)
    builder.add_node("code_syntax", code_syntax_judge_node)
    builder.add_node("code_logic", code_logic_judge_node)

    builder.add_edge(START, "code_writer")
    builder.add_conditional_edges("code_writer", 
                                _code_writing_route,
                                {
                                    "code_writer": "code_writer",
                                    "code_syntax": "code_syntax",
                                    "end": END
                                })
    builder.add_conditional_edges("code_syntax", 
                                _syntax_judge_route,
                                {
                                    "code_writer": "code_writer",
                                    "code_logic": "code_logic",
                                    "end": END
                                })
    builder.add_conditional_edges("code_logic",
                                _logic_judge_route,
                                {
                                    "code_logic": "code_logic",
                                    "code_writer": "code_writer",
                                    "end": END
                                })

    return builder


def build_graph_code_with_memory():
    '''
    构建一个编写代码的流程图，该流程图通过记忆功能
    '''
    memory = MemorySaver()

    # 构造图
    builder = _build_graph_code()

    return builder.compile(checkpointer=memory)


def build_graph_code_without_memory():
    '''
    构建一个编写代码的流程图，该流程图不通过记忆功能
    '''

    builder = _build_graph_code()
    return builder.compile()
    

def _build_graph_for_verilogeval():
    '''
    构建一个适用于验证verilog-eval数据集的流程图
    '''
    builder = StateGraph(State_coder)

    builder.add_node("code_writer", code_writing_node)
    builder.add_node("code_syntax", code_syntax_judge_node)
    builder.add_node("code_logic", code_logic_judge_node)
    builder.add_node("end_saving", end_saving_node)

    builder.add_edge(START, "code_writer")
    builder.add_conditional_edges("code_writer", 
                                _code_writing_route,
                                {
                                    "code_writer": "code_writer",
                                    "code_syntax": "code_syntax",
                                    "end": "end_saving"
                                })
    builder.add_conditional_edges("code_syntax", 
                                _syntax_judge_route,
                                {
                                    "code_writer": "code_writer",
                                    "code_logic": "code_logic",
                                    "end": "end_saving"
                                })
    builder.add_conditional_edges("code_logic",
                                _logic_judge_route,
                                {
                                    "code_logic": "code_logic",
                                    "code_writer": "code_writer",
                                    "end": "end_saving"
                                })
    builder.add_edge("end_saving", END)

    return builder

def build_graph_for_verilogeval_without_memory():
    '''
    构建一个适用于验证verilog-eval数据集的流程图，该流程图不通过记忆功能
    '''
    builder = _build_graph_for_verilogeval()
    return builder.compile()
