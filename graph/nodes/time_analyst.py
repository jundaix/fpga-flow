from graph.types import State, update_dict_value
from agents.fpga_agents import time_analyse_agent
from .getting_info import get_json_info

from langgraph.types import Command
from langchain_core.runnables import RunnableConfig
from langchain_core.messages import AIMessage, HumanMessage

import logging
import copy

logger = logging.getLogger(__name__)

def time_analyst_node(state: State, config: RunnableConfig) -> Command:
    """ 时间分析节点：根据当前的状态，生成需要执行的下一项任务 """
    logger.info(f"Time Analyst node start ...")

    # 整理用户需求内容
    requirement_message = f"""
    Please analyze the timing behavior and make assumptions about this module based on the following information:
    Module Name: {state["module_name"]}
    Module Description: {state["module_descrption"]}
    Module Interface: {state["module_interface"]}
    Design Requirements: {state["requirements"]}
    Suggestions: {state["next_step_suggest"]}
    """                                             # Suggestions 为操作执行建议，后续分析效果

    state_copy = copy.deepcopy(state)
    state_copy["messages"] = [
        HumanMessage(content=requirement_message, name="user_time_analyse")
    ]

    # 与llm交互获取运行结果
    response = time_analyse_agent.invoke(state_copy, config)
    response_content = response["messages"][-1].content

    # 提取其中的 json 信息 
    get_json_result, json_info = get_json_info(response_content)

    if get_json_result:
        logger.info(f"Time analysing result: {json_info}")

        timing_proposing = json_info.get("timing_proposing")
        return Command(
            update={
                "timing_proposing": timing_proposing,
                "messages": [
                    AIMessage(content=response_content, name="time_analyst"),
                ],
                "additional_info_needed": "",
                "task_finished": update_dict_value(state, "task_finished", "time_analysis", True),
            }
        )
    else:
        logger.warning(f"Failed to get time analysing result from LLM: {response_content}")
        
        return Command(
            update={
                "messages": [
                    AIMessage(content=response_content, name="time_analyst"),
                ],
                "additional_info_needed": f"Fail to get time analysing result:\n{json_info}",
                "task_finished": update_dict_value(state, "task_finished", "time_analysis", False),
            }
        )
