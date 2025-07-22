from graph.types import State
from agents.fpga_agents import code_planner_agent, coder_agent
from utils.verilog_extractor import extract_verilog_code
from utils.vivado_operation import *

from langgraph.types import Command
from langchain_core.runnables import RunnableConfig
from langchain_core.messages import AIMessage, HumanMessage

import logging
import copy

logger = logging.getLogger(__name__)

def code_plan_node(state: State, config: RunnableConfig) -> Command:
    """ 代码计划节点，编写代码生成计划，用于后续代码编写节点 """

    logger.info(f"Code Planner node start ...")

    # 整理用户需求内容
    requirement_message = f"""
    Please write a Verilog implementation plan based on the following module information:
    Module Name: {state["module_name"]}
    Module Description: {state["module_descrption"]}
    Module Interface: {state["module_interface"]}
    Requirement: {state["requirement"]}
    """

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
                "additional_info_needed": "Fail to generate FPGA code design",
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
    
    # 调用对应智能体生成 Verilog 代码
    response = coder_agent.invoke(state_copy, config)
    response_content = response["messages"][-1].content

    # 提取回答中的 Verilog 代码
    generated_code = extract_verilog_code(response_content)

    if generated_code:
        logger.info(f"Code generated for module: {state.get('module_name', 'unknown')}")

        # 先保存代码到文件，无论语法是否正确
        project_name = state.get('project_name', state.get('module_name', 'unknown'))
        module_name = state.get('module_name', 'unknown')
        # 定义workspace目录
        workspace_dir = Path(__file__).parent.parent / "workspace"

        # 先检查是否已经建立项目，再决定是否创建项目，若项目创建失败，退出节点并返回错误信息
        if not judge_project_exit(project_name, workspace_dir):
            try:
                creating_result, creating_information = create_project(project_name, workspace_path=workspace_dir)
                if creating_result:
                    logger.info(f"Project '{project_name}' created successfully.")
                else:
                    logger.error(f"Failed to create project: {creating_information}")
                    return Command(
                        update={
                            "additional_info_needed": f"Fail to create project: {creating_information}",
                        }, 
                    )
            except Exception as e:
                logger.error(f"Failed to creat project: {e}")
                return Command(
                    update={
                        "additional_info_needed": f"Fail to create project: {e}",
                    }, 
                )
        else:
            logger.info(f"Project '{project_name}' already exists. Skipping creation step.")

        # 在项目文件下创建源文件目录
        try:
            source_files_dir = workspace_dir.joinpath(project_name, f"{project_name}.srcs", "sources_1", "new")
            source_files_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Source directory created: {source_files_dir}")
        except Exception as e: 
            logger.error(f"Failed to create source files directory: {e}")
            return Command(
                update={
                    "additional_info_needed": f"Fail to create source files directory: {e}",
                }, 
            )
        
        # 保存代码文件
        code_file_path = source_files_dir / f"{module_name}.v"
        try:
            with open(code_file_path, 'w', encoding='gb18030') as f:
                f.write(generated_code)
            logger.info(f"Code saved to: {code_file_path}")
            save_message = f"Code saved to {code_file_path}"
        except Exception as e:
            logger.error(f"Failed to save code file: {e}")
            return Command(
                update={
                    "additional_info_needed": f"Fail to save the code file: {e}",
                }, 
            )
        
        # 将代码提交至 vivado 项目中
        try:
            adding_result, adding_message = add_files_to_project(project_name, workspace_path=workspace_dir, source_files=[str(code_file_path)])
            if adding_result:
                logger.info(adding_message)
            else:
                logger.error(adding_message)
                return Command(
                    update={
                        "additional_info_needed": f"Fail to add the code file to project!\n{adding_message}",
                    }, 
                )
        except Exception as e:
            logger.error(f"Failed to add sources to {project_name}: {e}")
            return Command(
                update={
                    "additional_info_needed": f"Fail to add the code file to project: {e}",
                }, 
            )

        # 采用vivado 进行语法验证
        is_valid, validation_message = validate_verilog_syntax_vivado(project_name, workspace_dir, [str(code_file_path)])
        if is_valid:
            logger.info(f"{validation_message}")
            return Command(
                update={
                    "messages": [AIMessage(content=f"{response_content}\n\n{save_message}\nSyntax validation: PASSED - {validation_message}", name="coder")],
                    "module_code": generated_code,
                    "additional_info_needed": "",
                    "task_finished.module_code_writing": True,
                },
            )
        else:
            logger.warning(f"{validation_message}")
            return Command(
                update={
                    "messages": [AIMessage(content=f"{response_content}\n\n{save_message}\nSyntax validation: FAILED\n{validation_message}", name="coder")],
                    "module_code": generated_code,
                    "module_code_syntax_error": validation_message, # (需要设计一个函数从中提取错误信息)
                    "additional_info_needed": f"Some error occurred while compiling the RTL code! Please solve this problem.",
                },
            )
    
    else:
        logger.warning("No Verilog code found in coder response")
        return Command(
            update={
                "messages": [AIMessage(content=f"Failed to extract Verilog code from response:\n{response_content} . Please check the requirements.", name="coder")],
                "additional_info_needed": f"The generated content is: {generated_code}\nNo Verilog code was extracted!",
            },
        )
        
