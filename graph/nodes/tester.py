from os import name
from sre_parse import IN
from graph.types import State, update_dict_value
from agents.fpga_agents import test_planner_agent, tester_agent
from utils.verilog_extractor import extract_verilog_code
from utils.vivado_operation import *
from utils.judge_same_code import judge_same_code
from .getting_info import get_error_info

from langgraph.types import Command
from langchain_core.runnables import RunnableConfig
from langchain_core.messages import AIMessage, HumanMessage

import logging
import copy
from typing import Dict, Any

logger = logging.getLogger(__name__)
RUNNING_CYCLE = 5                                       # 定义最多仅运行 5 次

def test_plan_node(state: State, config: RunnableConfig) -> Command:
    """ 测试计划节点，根据实现需求设计FPGA模块的测试（采用自然语言描述） """
    logger.info("Starting FPGA test planning...")

    requirement_message = f"""
    Please decide a testbench plan based on the following module information:
    Module Name: {state["module_name"]}
    Module Description: {state["module_descrption"]}
    Module Interface: {state["module_interface"]}
    Requirement: {state["requirements"]}
    Timing Constraint: {state["timing_proposing"]}
    Suggestions: {state["next_step_suggest"]}
    """                                             # Suggestions 为操作执行建议，后续分析效果

    # 复制图状态，在复制的状态中更改 message 字段，为该节点添加特定的 message
    state_copy = copy.deepcopy(state)
    state_copy["messages"] = [
        HumanMessage(content=requirement_message, name="user_test")
    ]

    # 调用对应智能体生成testbench设计计划
    response = test_planner_agent.invoke(state_copy, config)
    response_content = response["messages"][-1].content

    if response_content:
        logger.info(f"FPGA test design generated for module: {state.get('module_name', 'unknown')}")

        return Command(
            update={
                "messages": [AIMessage(content=response_content, name="test_planner")],
                "testbench_code_plan": response_content, 
                "additional_info_needed": "",
            },
        )
    else:
        logger.error(f"Fail to generate FPGA test design for module: {state.get('module_name', 'unknown')}")

        return Command(
            update={
                # llm 未给出 response，此处不更新 message 内容
                "additional_info_needed": "[System Error] Fail to generate FPGA test design",
                "testbench_code_plan": "",
            },
        )


def test_node(state: State, config: RunnableConfig) -> Command:
    """ 测试节点，根据测试计划设计FPGA模块的tetsbench（采用Verilog代码描述） """
    logger.info("Starting FPGA test generation...")

    # 验证项目是否已经建立
    project_name = state.get('project_name', state.get('module_name', 'unknown'))
    # 定义workspace目录
    workspace_dir = Path(__file__).parent.parent.parent / "workspace"

    if not judge_project_exit(project_name, workspace_dir):
        return Command(
            update={
                "additional_info_needed": f"Project '{project_name}' does not exist, meaning there is not the source code file.\nPlease check if the previous steps are completed!",
            }
        )

    requirement_message = f"""
    Please write a testbench code based on the following information:
    Module Name: {state["module_name"]}
    Module Description: {state["module_descrption"]}
    Module Interface: {state["module_interface"]}
    Test Plan: {state["testbench_code_plan"]}
    """

    # 复制图状态，在复制的状态中更改 message 字段，为该节点添加特定的 message
    state_copy = copy.deepcopy(state)
    state_copy["messages"] = [
        HumanMessage(content=requirement_message, name="user_test")
    ]

    # 定义完成的次数，用于追踪当前完成的情况
    running_times = 0
    # 用于暂存出现的语法错误和生成异常（未生成代码或是和源码一致）
    syntax_error = ""
    no_code = False
    source_same = False

    while running_times < RUNNING_CYCLE:
        running_times += 1

        # 若语法错误内容不为空，说明之前生成的代码存在语法错误，需要说明
        if syntax_error:
            state_copy["messages"].append(HumanMessage(content=f"The Verilog testbench you are currently writing has syntax problems{syntax_error}\nPlease correct them!"))
        # 若之前生成的内容没有代码，需要说明
        if no_code:
            state_copy["messages"].append(HumanMessage(content="Failed to extract Verilog testbench from your response. Please check the requirements!"))
        # 若生成的内容与源码相同，需要说明
        if source_same:
            state_copy["messages"].append(HumanMessage(content=f"The testbench you writed is the same as the design source code. Please rewrite!"))

        running_result = _verify_testbench_syntax(state_copy, config, running_times)

        if running_result.get("result"):
            break
        elif running_result.get("system_error"):
            break
        elif not running_result.get("testbench_code"):
            no_code, source_same = True, False
        elif running_result.get("source_code_judge"):
            no_code, source_same = False, True
        else:
            no_code, source_same = False, False
            syntax_error = running_result.get("syntax_error")
        
        # 追加输出的 AI 信息
        state_copy["messages"].append(AIMessage(content=running_result.get("response_content"), name="tester"))

    # 对于不同的输出结果返回不同的值
    if running_result.get("system_error"):
        system_error = running_result.get("system_error")
        return Command(
            update={
                "additional_info_needed": f"[System Error] {system_error}",
            }
        )
    elif running_result.get("result"):
        response_content = running_result.get("response_content")
        save_message = running_result.get("save_message")
        testbench_code = running_result.get("testbench_code")
        return Command(
            update={
                    "messages": [AIMessage(content=f"{response_content}\n\n{save_message}\n\
                        Syntax validation: PASSED", name="tester")],
                    "testbench_code": testbench_code,
                    "testbench_code_syntax_error": "",
                    "additional_info_needed": "",
                    "task_finished": update_dict_value(state, "task_finished", "testbench_writing", True),
                },
        )
    elif no_code:
        response_content = running_result.get("response_content")
        return Command(
            update={
                "messages": [AIMessage(content=f"Failed to extract testbench code from response {response_content}", name="tester")],
                "testbench_code": "",
                "testbench_code_syntax_error": "",
                "additional_info_needed": f"The generated content is: {response_content}\nNo testbench code was extracted!",
                "task_finished": update_dict_value(state, "task_finished", "testbench_writing", False),
            },
        )
    elif source_same:
        response_content = running_result.get("response_content")
        testbench_code = running_result.get("testbench_code")
        return Command(
            update={
                "messages": [AIMessage(content=f"{response_content}\n\nThe generated code is source code,\
                not a testbench!", name="tester")],
                "additional_info_needed": f"The generated content is: {response_content}\nThe testbench code is repeated with the source code, please check!",
                "testbench_code": testbench_code,
                "testbench_code_syntax_error": "",
                "task_finished": update_dict_value(state, "task_finished", "testbench_writing", False),
            },
        )
    else:
        response_content = running_result.get("response_content")
        save_message = running_result.get("save_message")
        testbench_code = running_result.get("testbench_code")
        return Command(
                update={
                    "messages": [AIMessage(content=f"{response_content}\n\n{save_message}\n\
                        Syntax validation: FAILED\n{syntax_error}", name="tester")],
                    "testbench_code": testbench_code,
                    "testbench_code_syntax_error": syntax_error,
                    "additional_info_needed": f"Some syntax error occurred while compiling the testbench code! Please solve this problem.",
                    "task_finished": update_dict_value(state, "task_finished", "testbench_writing", False),
                },
            )


def _verify_testbench_syntax(state: State, config: RunnableConfig, test_time: int) -> Dict[str, Any]:
    """ 
    执行验证 testbench 代码的语法正确性
    将原本编写代码和语法验证的内容封装，用于实现多次验证
    """
    logger.info(f"Execution Testbench Writing: {test_time} / {RUNNING_CYCLE}")

    # 调用对应智能体生成代码
    response = tester_agent.invoke(state, config)
    response_content = response["messages"][-1].content

    # 从回应中提取 tetsbench 代码
    testbench_code = extract_verilog_code(response_content)

    if testbench_code:
        logger.info("Testbench code extracted successfully")

        project_name = state.get('project_name', state.get('module_name', 'unknown'))
        module_name = state.get('module_name', 'unknown')
        # 定义workspace目录
        workspace_dir = Path(__file__).parent.parent.parent / "workspace"

        # 读取源码
        try:
            source_file = workspace_dir.joinpath(project_name, f"{project_name}.srcs", "sources_1", "new", f"{module_name}.v")
            with open(source_file, 'r', encoding='gb18030') as f:
                source_code = f.read()
            logger.info(f"Source code read from {source_file}")
        except Exception as e:
            logger.error(f"Failed to read source file: {e}")
            return {
                "result": False,
                "response_content": response_content,
                "testbench_code": testbench_code,
                "system_error": f"Fail to read the source file: {e}"
            }

        # 验证新生成的代码是否为源代码（当前存在对话时输出的testbench为源设计代码，并非testbench）
        try:
            if judge_same_code(source_code, testbench_code):
                logger.warning("The generated code is source code, not a testbench!")
                return {
                    "result": False,
                    "source_code_judge": True, 
                    "response_content": response_content,
                    "testbench_code": testbench_code,
                }
        except Exception as e:
            logger.warning(f"Failed to judge code similarity: {e}")
            return {
                "result": False,
                "system_error": f"Fail to judge code similarity: {e}",
                "response_content": response_content,
                "testbench_code": testbench_code,
            }

        # 先保存测试台代码到文件，无论语法是否正确
        # 创建目录
        try:
            sim_dir = workspace_dir.joinpath(project_name, f"{project_name}.srcs", "sim_1", "new")
            sim_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Directory created: {workspace_dir}")
        except Exception as e:
            logger.error(f"Failed to create directory: {e}")
            return {
                "result": False,
                "response_content": response_content,
                "testbench_code": testbench_code,
                "system_error": f"Fail to create source files directory: {e}"
            }
        
        # 保存代码文件
        testbench_file_path = sim_dir / f"tb_{module_name}.v"
        try:
            with open(testbench_file_path, 'w', encoding='gb18030') as f:
                f.write(testbench_code)
            logger.info(f"Code saved to: {testbench_file_path}")
            save_message = f"Code saved to {testbench_file_path}"
        except Exception as e:
            logger.error(f"Failed to save code file: {e}")
            return {
                "result": False,
                "response_content": response_content,
                "testbench_code": testbench_code,
                "system_error": f"Fail to save the testbench file: {e}"
            }

        # 将仿真文件添加至 vivado 项目中
        try:
            adding_result, adding_message = add_sim_files_to_project(project_name, workspace_dir, [str(testbench_file_path)])
            if adding_result:
                logger.info(adding_message)
            else:
                logger.error(adding_message)
                return {
                    "result": False,
                    "response_content": response_content,
                    "testbench_code": testbench_code,
                    "system_error": f"Fail to add the testbench file to project!\n{adding_message}",
                }
        except Exception as e:
            logger.error(f"Failed to add sim files to project {project_name}: {e}")
            return {
                "result": False,
                "response_content": response_content,
                "testbench_code": testbench_code,
                "system_error": f"Fail to add the testbench file to project: {e}",
            }
        
        # 语法验证
        is_valid, validation_message = validate_verilog_syntax_vivado(project_name, workspace_dir, [str(testbench_file_path)])
        if is_valid:
            logger.info(f"Testbench syntax : {validation_message}")
            return {
                "result": True,
                "response_content": response_content,
                "testbench_code": testbench_code,
                "save_message": save_message,
                "syntax_error": ""
            }
        else:
            logger.warning(f"Testbench syntax validation failed: {validation_message}")

            syntax_err = get_error_info(validation_message)
            return {
                "result": False,
                "response_content": response_content,
                "testbench_code": testbench_code,
                "save_message": save_message,
                "syntax_error": syntax_err
            }
    else:
        logger.warning("No testbench code found in tester response")

        return {
            "result": False,
            "response_content": response_content,
            "testbench_code": "",
            "save_message": "",
            "syntax_error": ""
        }
        

