# import sys
# import os
# sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from graph.types import State
from agents.fpga_agents import coordinator_agent
from .getting_info import get_json_info

from langchain_core.runnables import RunnableConfig
from langchain_core.messages import AIMessage
from langgraph.types import Command

import logging


logger = logging.getLogger(__name__)

def coordinator_node(state: State, config: RunnableConfig) -> Command: 
    """ 协调节点：用于和人类进行交互，根据人类输入，分析人类需求从而得到 Verilog module 的实现要求 """
    logger.info("Starting FPGA Coordinator ...")

    # 与 llm 进行交互，获得 Verilog module 的实现要求
    response = coordinator_agent.invoke(state, config)
    response_content = response["messages"][-1].content

    # 从 response_content 中提取 json 信息
    user_requirement = {}
    get_json_result, json_info = get_json_info(response_content)

    if get_json_result:
        user_requirement = json_info
        logger.info(f"User requirement analyse completed for module: {user_requirement.get('module_name', 'unknown')}")
    else:
        logger.warning("No valid JSON found in COORDINATOR response!")
        user_requirement["has_enough_context"] = False
        user_requirement["additional_info_needed"] = "No valid JSON found in coordinator response"
        return
    
    # 从读取到的 json 结果中读取信息
    module_name = user_requirement.get("module_name", "unname")
    if user_requirement.get("has_enough_context", False):
        return Command(
            update={
                "messages": [AIMessage(content=response_content, name="coordinator")],
                "module_name": module_name,
                "project_name": module_name,
                "module_descrption": user_requirement.get("module_description", ""),
                "module_interface": user_requirement.get("module_interface", ""),
                "requirements": user_requirement.get("requirements", ""),
                "has_enough_context": user_requirement.get("has_enough_context", False),
                "additional_info_needed": user_requirement.get("additional_info_needed", ""),
            },)
    else:
        additional_info = user_requirement.get("additional_info_needed", "More information needed")
        return Command(
            update={
                "messages": [AIMessage(content=f"I need more information to proceed: {additional_info}", name="coordinator")],
                "has_enough_context": False,
                "additional_info_needed": additional_info,
            })


if __name__ == "__main__":
    from langgraph.graph import StateGraph, START, END

    builder = StateGraph(State)

    # builder.add_node("coordinator", coordinator_node)
    # builder.add_edge(START, "coordinator")
    # builder.add_edge("coordinator", END)

    # graph = builder.compile()

    # state = {
    #     # Runtime Variables
    #     "messages": [{"role": "user", "content": "设计一个8位计数器，带使能和复位功能"}],
    #     "auto_accepted_plan": False,
    # }

    # for s in graph.stream(state):
    #     print(s)

    # print("运行结束")