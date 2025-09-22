"""
    实现关于子任务下代码编写的节点，其中包含：
        代码编写节点
        代码语法审核节点
        代码逻辑审核节点
"""

import json
import logging
import os
from pathlib import Path
from platform import node
from typing import Annotated, Literal, Dict, Any
import copy
import re

from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.types import Command, interrupt

from utils.verilog_extractor import extract_verilog_code, validate_verilog_syntax
from utils.analysis_json import parse_llm_json_first
from agents import coder_agent, code_syntax_err_analyst, code_review

from .sub_code_type import State_coder, updata_list

logger = logging.getLogger(__name__)
workspace = Path(__file__).parent.parent.parent / "workspace"

def code_writing_node(state: State_coder, config: RunnableConfig) -> Command:
    """
    代码编写节点，根据实现要求由对应 agent 生成代码，再将代码保存在指定目录下
    """

    logger.info("Code writing node START!")
    # 计算更新当前的 trying_times
    trying_time = state["trying_times"] + 1

    # 深拷贝 state，用于保证不改变原 state，并调整其中的 message 内容
    node_state = copy.deepcopy(state)

    ''' 整理曾经出现过的语法错误 '''
    syntax_error = ""
    if len(node_state["module_code_syntax_error"]) > 1:
        syntax_error_list = node_state["module_code_syntax_error"][:-1]
        syntax_error = "Some grammatical errors you need to avoid:\n" + "\n".join(syntax_error_list) if syntax_error_list else ""

    ''' 根据当前运行状况调整输入要求 '''
    request = ""
    # 首次生成
    if trying_time == 1:
        request = f"""Please write the Verilog RTL code based on the following module information:{node_state['module_requirements']}"""
    # 非首次生成，表明上一次生成出现语法或逻辑问题
    else:
        # 上一次出现语法错误
        if node_state["is_syntax_error"]:
            request = f"""
            Please correct any syntax errors in the following Verilog code according to the implementation requirements.
            Requirement: {node_state['module_requirements']}
            {syntax_error}
            Current RTL code:\n{node_state['module_code']}
            Current syntax error you need to fix:{node_state['syntax_error_source']}
            Please be sure to correct any syntax errors in your code based on the feedback provided, even if you believe it is correct!
            """
        # 上一次出现逻辑错误
        elif node_state["is_logic_error"]:
            request = f"""
            Please correct any logic errors in the following Verilog code according to the implementation requirements.
            Requirement: {node_state['module_requirements']}
            {syntax_error}
            Current RTL code:\n{node_state['module_code']}
            Current logic error you need to fix:{node_state['module_code_logic_error']}
            Please be sure to correct any logic errors in your code based on the feedback provided, even if you believe it is correct!
            """
        else:
            request = f"""
            Please correct any errors in the following Verilog code according to the implementation requirements.
            Requirement: {node_state['module_requirements']}
            {syntax_error}
            {f"Current RTL code:\n{node_state['module_code']}" if node_state['module_code'] else ""}
            """
    
    ''' 更新状态中的信息内容 '''
    node_state["messages"] = [HumanMessage(content=request)]
    
    ''' 调用 coder_agent 生成代码 '''
    response = coder_agent.invoke(node_state, config)
    response_content = response["messages"][-1].content

    ''' 提取生成的代码 '''
    generated_code = extract_verilog_code(response_content)
    # 提取到目的代码
    if generated_code:
        logger.info("The RTL code generated successfully!")
        # 将代码保存到目的文件内
        code_file_path = workspace / node_state["module_name"] / f"{node_state["module_name"]}.v"

        try:
            with open(code_file_path, 'w', encoding='gb18030') as f:
                f.write(generated_code)
            logger.info(f"Code saved to: {code_file_path}")
        except Exception as e:
            ''' 保存代码文件时失败，归类为其它错误，重新尝试 '''
            logger.error(f"Failed to save code file: {e}")
            logger.info("Code writing node END!")
            return Command(
                update={
                    "is_else_error": True,
                    "is_syntax_error": False,
                    "is_logic_error": False,
                    "else_error": f"Failed to save code file: {e}",
                    "trying_times": trying_time,
                }
            )

        logger.info("Code writing node END!")
        return Command(
            update={
                "module_code": generated_code,
                "is_else_error": False,
                "is_syntax_error": False,
                "is_logic_error": False,
                "trying_times": trying_time,
            }
        )

    else:
        ''' 提取到的代码为空，归类为其它错误，重新尝试 '''
        logger.error("Failed to get the RTL code from response!")
        logger.info("Code writing node END!")
        return Command(
            update={
                "is_else_error": True,
                "is_syntax_error": False,
                "is_logic_error": False,
                "else_error": f"Failed to get the RTL code from response: {response_content}",
                "trying_times": trying_time,
            }
        )

def code_syntax_judge_node(state: State_coder, config: RunnableConfig) -> Command:
    """
    代码语法判断节点，调用语法分析器判断代码是否存在语法错误，并在出现语法错误时对错误内容进行解析学习
    目前调用的是iverilog的语法分析器，且仅是分析单个文件下的语法问题
    """
    logger.info("Code syntax judge node START!")

    # 代码文件路径
    code_file_path = workspace / state["module_name"] / f"{state["module_name"]}.v"

    # 调用语法分析器判断是否存在语法错误
    is_valid, validation_message = validate_verilog_syntax(str(code_file_path))

    ''' 根据验证反馈信息执行不同操作 '''
    # 若语法验证通过，直接返回
    if is_valid:
        logger.info("Code syntax judge node: The code syntax is valid!")
        logger.info("Code syntax judge node END!")
        return Command(
            update={
                "is_syntax_error": False,
                "syntax_error_source": "",
            }
        )

    # 若语法验证不通过
    else:
        # 判断是否真的出现语法错误
        if "语法错误" in validation_message:
            logger.error("Code syntax judge node: The code syntax is invalid!")
            # 由对应 agent 解析语法错误内容
            request = f"""
            Please parse the following syntax error content and provide a clear and concise description of the error.
            syntax error message:\n{validation_message}
            """
            # 深拷贝 state ，用于保证不改变原 state，并调整其中的 message 内容
            node_state = copy.deepcopy(state)
            node_state["messages"] = [HumanMessage(content=request)]
            response = code_syntax_err_analyst.invoke(node_state, config)
            syntax_error_analysis = response["messages"][-1].content
            logger.info("Code syntax judge node END!")
            return Command(
                update={
                    "is_syntax_error": True,
                    "is_logic_error": False,
                    "is_else_error": False,
                    "syntax_error_source": validation_message,
                    "module_code_syntax_error": updata_list(state, "module_code_syntax_error", syntax_error_analysis)
                }
            )

        # 否则被视为出现其它错误
        else:
            logger.error("Code syntax judge node: Some error raise when judging syntax error!")
            logger.info("Code syntax judge node END!")
            return Command(
                update={
                    "is_else_error": True,
                    "is_syntax_error": False,
                    "is_logic_error": False,
                    "else_error": validation_message
                }
            )


def code_logic_judge_node(state: State_coder, config: RunnableConfig) -> Command:
    """
    代码逻辑判断节点，调用逻辑分析器判断代码是否满足实现需求以及是否存在逻辑错误
    """
    logger.info("Code logic judge node START!")

    if state["is_else_error"]:
        trying_time = state["trying_times"] + 1
    else:
        trying_time = state["trying_times"]

    # 深拷贝 state，用于保证不改变原 state，并调整其中的 message 内容
    node_state = copy.deepcopy(state)

    # 整理输入请求
    request = f"""
    implementation requirements:\n{node_state["module_requirements"]}
    code:\n{node_state["module_code"]}
    """
    node_state["messages"] = [HumanMessage(content=request)]
    # 调用模型，检查代码实现是否匹配需求以及是否存在逻辑错误
    response = code_review.invoke(node_state, config)
    code_review_result = response["messages"][-1].content

    # 读取模型输出的 json 内容
    json_match, judge_result = parse_llm_json_first(code_review_result)

    # 未解析出 json 内容
    if not json_match:
        ''' 模型输出的 json 内容为空，需要重新尝试 '''
        logger.warning("Code logic judge node: Failed to get the json content from response!")
        logger.info("Code logic judge node END!")
        with open(f"{state['module_name']}_json_error.txt", "w", encoding="utf-8") as f:
            f.write(f"LLM_RESPONSE:\n{code_review_result}")
        return Command(
            update={
                "is_logic_error": False,
                "is_else_error": True,
                "is_syntax_error": False,
                "trying_times": trying_time,
            }
        )
    
    # 解析读取出来的 json 内容，判断是否存在问题
    if judge_result.get("meet_requirements", False):
        logger.info("Code logic judge node: The code meets the requirements!")
        logger.info("Code logic judge node END!")
        return Command(
            update={
                "is_logic_error": False,
                "is_else_error": False,
                "is_syntax_error": False,
                "trying_times": trying_time,
            }
        )
    else:
        logger.error("Code logic judge node: The code does not meet the requirements!")
        logger.info("Code logic judge node END!")
        return Command(
            update={
                "is_logic_error": True,
                "is_else_error": False,
                "is_syntax_error": False,
                "module_code_logic_error": judge_result.get("error_explanation", "No Info"),
                "trying_times": trying_time,
            }
        )


def end_saving_node(state: State_coder):
    '''
    将对应的运行结果保存到 json 文件中。
    适用于验证 verilog-eval 数据集
    '''
    if state["is_syntax_error"]:
        result = {
            "result": "syntax_error",
            "trying_times": state["trying_times"]
        }
    elif state["is_logic_error"]:
        result = {
            "result": "logic_error",
            "trying_times": state["trying_times"]
        }
    elif state["is_else_error"]:
        result = {
            "result": "else_error",
            "trying_times": state["trying_times"]
        }
    else:
        result = {
            "result": "success",
            "trying_times": state["trying_times"]
        }
    
    # 定义存储的 json 文件位置
    json_file_path = workspace / state["module_name"] / "result.json"
    with open(json_file_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=4)
