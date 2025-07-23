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

logger = logging.getLogger(__name__)

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

    requirement_message = f"""
    Please write a testbench code based on the following information:
    Module Name: {state["module_name"]}
    Module Description: {state["module_descrption"]}
    Module Interface: {state["module_interface"]}
    Test Plan: {state["testbench_code_plan"]}
    """

    state_copy = copy.deepcopy(state)
    state_copy["messages"] = [
        HumanMessage(content=requirement_message, name="user_test")
    ]

    # 调用智能体生成对应的testbench代码
    response = tester_agent.invoke(state_copy, config)
    response_content = response["messages"][-1].content

    # 从回应中提取 tetsbench 代码
    testbench_code = extract_verilog_code(response_content)

    if testbench_code:
        logger.info("Testbench code extracted successfully")

        project_name = state.get('project_name', state.get('module_name', 'unknown'))
        module_name = state.get('module_name', 'unknown')
        # 定义workspace目录
        workspace_dir = Path(__file__).parent.parent.parent / "workspace"

        # 先判定项目是否已经建立，则认为当前操作非法（未建立项目则不存在可以实例化的源码）
        if not judge_project_exit(project_name, workspace_dir):
            return Command(
                update={
                    "additional_info_needed": f"Project '{project_name}' does not exist, meaning there is not the source code file.\nPlease check if the previous steps are completed!",
                }
            )

        # 读取源码
        try:
            source_file = workspace_dir.joinpath(project_name, f"{project_name}.srcs", "sources_1", "new", f"{module_name}.v")
            with open(source_file, 'r', encoding='gb18030') as f:
                source_code = f.read()
            logger.info(f"Source code read from {source_file}")
        except Exception as e:
            logger.error(f"Failed to read source file: {e}")
            return Command(
                update={
                    "additional_info_needed": f"[System Error] Fail to read the source file: {e}",
                }
            )

        # 验证新生成的代码是否为源代码（当前存在对话时输出的testbench为源设计代码，并非testbench）
        try:
            if judge_same_code(source_code, testbench_code):
                logger.warning("The generated code is source code, not a testbench!")
                return Command(
                    update={
                        "messages": [AIMessage(content=f"{response_content}\n\nThe generated code is source code,\
                         not a testbench!", name="tester")],
                        "additional_info_needed": f"The generated content is: {response_content}\nThe testbench code is repeated with the source code, please check!",
                    },
                )
        except Exception as e:
            logger.warning(f"Failed to judge code similarity: {e}")
            return Command(
                update={
                    "additional_info_needed": f"[System Error] Fail to judge code similarity: {e}",
                }
            )

        # 先保存测试台代码到文件，无论语法是否正确
        # 创建目录
        try:
            sim_dir = workspace_dir.joinpath(project_name, f"{project_name}.srcs", "sim_1", "new")
            sim_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Directory created: {workspace_dir}")
        except Exception as e:
            logger.error(f"Failed to create directory: {e}")
            return Command(
                update={
                    "additional_info_needed": f"[System Error] Fail to create sim files directory: {e}",
                }, 
            )
        
        # 保存代码文件
        testbench_file_path = sim_dir / f"tb_{module_name}.v"
        try:
            with open(testbench_file_path, 'w', encoding='gb18030') as f:
                f.write(testbench_code)
            logger.info(f"Code saved to: {testbench_file_path}")
            save_message = f"Code saved to {testbench_file_path}"
        except Exception as e:
            logger.error(f"Failed to save code file: {e}")
            return Command(
                update={
                    "additional_info_needed": f"[System Error] Fail to save the testbench file: {e}",
                }, 
            )

        # 将仿真文件添加至 vivado 项目中
        try:
            adding_result, adding_message = add_sim_files_to_project(project_name, workspace_dir, [str(testbench_file_path)])
            if adding_result:
                logger.info(adding_message)
            else:
                logger.error(adding_message)
                return Command(
                    update={
                        "additional_info_needed": f"[System Error] Fail to add the testbench file to project!\n{adding_message}",
                    }, 
                )
        except Exception as e:
            logger.error(f"Failed to add sim files to project {project_name}: {e}")
            return Command(
                update={
                    "additional_info_needed": f"[System Error] Fail to add the testbench file to project!\n{e}",
                }, 
            )

        # 语法验证
        is_valid, validation_message = validate_verilog_syntax_vivado(project_name, workspace_dir, [str(testbench_file_path)])
        if is_valid:
            logger.info(f"Testbench syntax : {validation_message}")

            return Command(
                update={
                    "messages": [AIMessage(content=f"{response_content}\n\n{save_message}\n\
                        Syntax validation: PASSED - {validation_message}", name="tester")],
                    "testbench_code": testbench_code,
                    "testbench_code_syntax_error": "",
                    "additional_info_needed": "",
                    "task_finished": update_dict_value(state, "task_finished", "testbench_writing", True),
                },
            )
        else:
            logger.warning(f"Testbench syntax validation failed: {validation_message}")

            syntax_err = get_error_info(validation_message)
            return Command(
                update={
                    "messages": [AIMessage(content=f"{response_content}\n\n{save_message}\n\
                        Syntax validation: FAILED\n{syntax_err}", name="tester")],
                    "testbench_code": testbench_code,
                    "testbench_code_syntax_error": syntax_err,
                    "additional_info_needed": f"Some syntax error occurred while compiling the testbench code! Please solve this problem.",
                    "task_finished": update_dict_value(state, "task_finished", "testbench_writing", False),
                },
            )
    else:
        logger.warning("No testbench code found in tester response")
        
        return Command(
            update={
                "messages": [AIMessage(content=f"Failed to extract testbench code from response {response_content}. Please review!", name="tester")],
                "testbench_code": "",
                "testbench_code_syntax_error": "",
                "additional_info_needed": f"The generated content is: {response_content}\nNo testbench code was extracted!",
                "task_finished": update_dict_value(state, "task_finished", "testbench_writing", False),
            },
        )

