from graph.types import State
from agents.fpga_agents import planner_agent
from .getting_info import get_json_info

from langgraph.types import Command
from langchain_core.runnables import RunnableConfig
from langchain_core.messages import AIMessage, HumanMessage

import logging
import copy
import json

logger = logging.getLogger(__name__)

def planner_node(state: State, config: RunnableConfig) -> Command:
    """ 计划节点：根据当前的状态，生成需要执行的下一项任务 """
    logger.info(f"Planner node start ...")

    print(f"当前的任务完成状态:\n{state["task_finished"]}\n*********************************************************")

    task_finished = json.dumps(state["task_finished"])
    # 若存在额外的返回信息（即下属 agent 运行时出现异常，通过 additional_info_needed 字段返回）
    if state["additional_info_needed"]:
        # 若 additional_info_needed 词条不为空，则认为上一步的任务处理出现异常，需要在信息中指出
        current_message = f"""
        The current task completion status is:
        {task_finished}
        The previous operation was {state["next_step"]}
        Now the information returned by the subordinate agent is:
        {state["messages"]}
        """
    elif state["next_step"]:
        # 初始设定 next_step 词条为空，若不为空则认为之前完成了某项任务
        current_message = f"""
        The current task completion status is:
        {task_finished}
        The previous operation was {state["next_step"]}
        """
    else:
        current_message = f"""
        The current task completion status is:
        {task_finished}
        """

    state_copy = copy.deepcopy(state)
    state_copy["messages"] = [
        HumanMessage(content=f"Here is the project status. Please decide the next step base on the information:\n{current_message}", name="user_planner")
    ]

    # 与llm交互获取运行结果
    response = planner_agent.invoke(state_copy, config)
    response_content = response["messages"][-1].content

    # 提取其中的 json 信息
    next_decide = {}
    get_json_result, json_info = get_json_info(response_content)

    if get_json_result:
        next_decide = json_info
        next_step = next_decide.get("next_step")

        logger.info(f"The planner decide the next decide: {next_step}")

        return Command(
            update={
                "messages": [AIMessage(content=response_content, name="planner")],
                "next_step": next_step,
                "next_step_suggest": next_decide.get("next_step_suggest"),
            }
        )
    
    else:
        logger.warning(f"No valid JSON found in PLANNER response!")

        return Command(
            update={
                "messages": [AIMessage(content=f"There is no valid JSON found in PLANNER response!\n{response_content}", name="planner")],
                "next_step": "None",
                "next_step_suggest": "",       # 当前未使用该字段
            }
        )

