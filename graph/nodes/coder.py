from os import name
from graph.types import State, update_dict_value
from agents.fpga_agents import code_planner_agent, coder_agent
from utils.verilog_extractor import extract_verilog_code
from utils.vivado_operation import *
from .getting_info import get_error_info

from langgraph.types import Command
from langchain_core.runnables import RunnableConfig
from langchain_core.messages import AIMessage, HumanMessage

import logging
import copy
from typing import Dict, Any

logger = logging.getLogger(__name__)
RUNNING_CYCLE = 5                                       # 定义最多仅运行 5 次

def code_plan_node(state: State, config: RunnableConfig) -> Command:
    """ 代码计划节点，编写代码生成计划，用于后续代码编写节点 """

    logger.info(f"Code Planner node start ...")

    # 整理用户需求内容
    requirement_message = f"""
    Please write a Verilog implementation plan based on the following module information:
    Module Name: {state["module_name"]}
    Module Description: {state["module_descrption"]}
    Module Interface: {state["module_interface"]}
    Requirement: {state["requirements"]}
    Timing Constraint: {state["timing_proposing"]}
    Suggestions: {state["next_step_suggest"]}
    """                                             # Suggestions 为操作执行建议，后续分析效果，新增了时序要求用于指导编写

    # 复制图状态，在复制的状态中更改 message 字段，为该节点添加特定的 message
    state_copy = copy.deepcopy(state)
    state_copy["messages"] = [
        HumanMessage(content=requirement_message, name="user_code")
    ]

    # 调用对应智能体生成代码设计计划
    response = code_planner_agent.invoke(state_copy, config)
    response_content = response["messages"][-1].content

    if response_content:
        logger.info(f"FPGA code design generated for module: {state.get('module_name', 'unknown')}")

        return Command(
            update={
                "messages": [AIMessage(content=response_content, name="code_planner")],
                "module_code_plan": response_content, 
                "additional_info_needed": "",
            },
        )
    else:
        logger.error(f"Fail to generate FPGA code design for module: {state.get('module_name', 'unknown')}")

        return Command(
            update={
                # llm 未给出 response，此处不更新 message 内容
                "additional_info_needed": "[System Error] Fail to generate FPGA code design",
                "module_code_plan": "",
            }, 
        )


def code_node(state: State, config: RunnableConfig) -> Command:
    """ 代码编写节点，根据设计编写对应的 module 设计代码 """
    logger.info(f"Code Writer node start ...")

    # 整理前期的需求
    requirement_message = f"""
    Please write the Verilog RTL code based on the following module information:
    Module Name: {state["module_name"]}
    Module Description: {state["module_descrption"]}
    Module Interface: {state["module_interface"]}
    Code Design Plan: {state["module_code_plan"]}
    """

    # 复制图状态，在复制的状态中更改 message 字段，为该节点添加特定的 message
    state_copy = copy.deepcopy(state)
    state_copy["messages"] = [
        HumanMessage(content=requirement_message, name="user_code")
    ]

    # 定义完成的次数，用于追踪当前的尝试情况
    running_times = 0
    # 用于暂存出现的语法错误和生成异常（例如生成的内容无代码），初始时没有
    syntax_error = ""
    no_code = False

    # 执行循环，最多运行 RUNNING_CYCLE 次
    while running_times < RUNNING_CYCLE:
        running_times += 1

        # 若语法错误内容不为空，说明之前生成的代码存在语法错误，需要说明
        if syntax_error:
            state_copy["messages"].append(HumanMessage(content=f"The Verilog code you are currently writing has syntax problems{syntax_error}\nPlease correct them!"))
        # 若之前生成的内容没有代码，需要说明
        if no_code:
            state_copy["messages"].append(HumanMessage(content="Failed to extract Verilog code from your response. Please check the requirements!"))

        running_result = _verify_code_syntax(state_copy, config, running_times)

        # 若生成的代码语法验证通过，则直接退出循环
        if running_result.get("result"):
            no_code = False
            break
        # 若存在系统错误，也直接退出循环
        elif running_result.get("system_error"):
            break
        # 若生成的内容中没有代码，则进行相应的信息更新
        elif not running_result.get("code"):
            no_code = True
        # 若生成的代码中存在语法错误，则进行相应的信息更新
        else:
            no_code = False
            syntax_error = running_result.get("syntax_error")
        
        # 追加输出的 AI 信息
        state_copy["messages"].append(AIMessage(content=running_result.get("response_content"), name="coder"))
        
    # 对循环后的不同输出结果进行处理
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
        generated_code = running_result.get("code")
        return Command(
            update={
                    "messages": [AIMessage(content=f"{response_content}\n\n{save_message}\n\nSyntax validation: PASSED", name="coder")],
                    "module_code": generated_code,
                    "additional_info_needed": "",
                    "module_code_syntax_error": "",
                    "task_finished": update_dict_value(state, "task_finished", "module_code_writing", True),
                },
        )
    elif no_code:
        response_content = running_result.get("response_content")
        return Command(
            update={
                "messages": [AIMessage(content=f"Failed to extract Verilog code from response:\n{response_content} . Please check the requirements!", name="coder")],
                "module_code": "",
                "module_code_syntax_error": "",
                "additional_info_needed": f"The generated content is:\n{response_content}\nNo Verilog RTL code was extracted!",
                "task_finished": update_dict_value(state, "task_finished", "module_code_writing", False)
            },
        )
    else:
        response_content = running_result.get("response_content")
        save_message = running_result.get("save_message")
        generated_code = running_result.get("code")
        return Command(
            update={
                    "messages": [AIMessage(content=f"{response_content}\n\n{save_message}\nSyntax validation: FAILED\n{syntax_error}", name="coder")],
                    "module_code": generated_code,
                    "module_code_syntax_error": syntax_error,
                    "additional_info_needed": f"Some syntax error occurred while compiling the RTL code! Please solve this problem.",
                    "task_finished": update_dict_value(state, "task_finished", "module_code_writing", False),
                },
        )


def _verify_code_syntax(state: State, config: RunnableConfig, test_time: int) -> Dict[str, Any]:
    """ 
    执行验证设计代码的语法正确性
    将原本编写代码和语法验证的内容封装，用于实现多次验证
    """
    logger.info(f"Execution Code Writing: {test_time} / {RUNNING_CYCLE}")

    # 调用对应智能体生成 Verilog 代码
    response = coder_agent.invoke(state, config)
    response_content = response["messages"][-1].content

    # 提取回答中的 Verilog 代码
    generated_code = extract_verilog_code(response_content)
        
    if generated_code:
        logger.info(f"Code generated for module: {state.get('module_name', 'unknown')}")

        # 先保存代码到文件，无论语法是否正确
        project_name = state.get('project_name', state.get('module_name', 'unknown'))
        module_name = state.get('module_name', 'unknown')
        # 定义workspace目录
        workspace_dir = Path(__file__).parent.parent.parent / "workspace"

        # 先检查是否已经建立项目，再决定是否创建项目，若项目创建失败，退出节点并返回错误信息
        if not judge_project_exit(project_name, workspace_dir):
            try:
                creating_result, creating_information = create_project(project_name, workspace_path=workspace_dir)
                if creating_result:
                    logger.info(f"Project '{project_name}' created successfully.")
                else:
                    logger.error(f"Failed to create project: {creating_information}")
                    return {
                        "result": False,
                        "response_content": response_content,
                        "code": generated_code,
                        "system_error": f"Fail to create project: {creating_information}"
                    }
            except Exception as e:
                logger.error(f"Failed to creat project: {e}")
                return {
                    "result": False,
                    "response_content": response_content,
                    "code": generated_code,
                    "system_error": f"Fail to create project: {e}"
                }
        else:
            logger.info(f"Project '{project_name}' already exists. Skipping creation step.")

        # 在项目文件下创建源文件目录
        try:
            source_files_dir = workspace_dir.joinpath(project_name, f"{project_name}.srcs", "sources_1", "new")
            source_files_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Source directory created: {source_files_dir}")
        except Exception as e: 
            logger.error(f"Failed to create source files directory: {e}")
            return {
                "result": False,
                "response_content": response_content,
                "code": generated_code,
                "system_error": f"Fail to create source files directory: {e}"
            }
        
        # 保存代码文件
        code_file_path = source_files_dir / f"{module_name}.v"
        try:
            with open(code_file_path, 'w', encoding='gb18030') as f:
                f.write(generated_code)
            logger.info(f"Code saved to: {code_file_path}")
            save_message = f"Code saved to {code_file_path}"
        except Exception as e:
            logger.error(f"Failed to save code file: {e}")
            return {
                "result": False,
                "response_content": response_content,
                "code": generated_code,
                "system_error": f"Fail to save the code file: {e}"
            }
        
        # 将代码提交至 vivado 项目中
        try:
            adding_result, adding_message = add_files_to_project(project_name, workspace_path=workspace_dir, source_files=[str(code_file_path)])
            if adding_result:
                logger.info(adding_message)
            else:
                logger.error(adding_message)
                return {
                    "result": False,
                    "response_content": response_content,
                    "code": generated_code,
                    "system_error": f"Fail to add the code file to project: {adding_message}", 
                }
        except Exception as e:
            logger.error(f"Failed to add sources to {project_name}: {e}")
            return {
                "result": False,
                "response_content": response_content,
                "code": generated_code,
                "system_error": f"Fail to add the code file to project: {e}", 
            }

        # 采用 vivado 进行语法验证
        is_valid, validation_message = validate_verilog_syntax_vivado(project_name, workspace_dir, [str(code_file_path)])

        if is_valid:
            logger.info(f"{validation_message}")
            
            return {
                "result": True,
                "response_content": response_content,
                "code": generated_code,
                "save_message": save_message,
                "syntax_error": ""
            }
        else:
            logger.warning(f"{validation_message}")

            syntax_err = get_error_info(validation_message)
            return {
                "result": False,
                "response_content": response_content,
                "code": generated_code,
                "save_message": save_message,
                "syntax_error": syntax_err
            }
    
    else:
        logger.warning("No Verilog code found in coder response")

        return {
            "result": False,
            "response_content": response_content,
            "code": "",
            "save_message": "",
            "syntax_error": ""
        }
