# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

import json
import logging
import os
from pathlib import Path
from typing import Annotated, Literal, Dict, Any
from pprint import pprint
from unicodedata import name
import copy

from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.types import Command, interrupt

from agents.fpga_agents import (
    planner_agent,
    coder_agent, 
    tester_agent,
    code_planner_agent,
    test_planner_agent,
)

from utils.verilog_extractor import extract_verilog_code, validate_verilog_syntax, validate_verilog_logic
from utils.vivado_operation import *
from utils.judge_same_code import judge_same_code

from .types import State

logger = logging.getLogger(__name__)

def print_state(state: State, node_name: str) -> None:
    print(f"\n=== [{node_name}] Current State ===")
    pprint(state["messages"])
    print("=== End of State ===\n")


def planner_node(state: State, config: RunnableConfig) -> Command[Literal["coder", "human_feedback", "__end__"]]:
    """FPGA Planner node - analyzes requirements and creates module specifications."""
    logger.info("Starting FPGA planning...")
    
    # Invoke planner agent  调用planner智能体
    response = planner_agent.invoke(state, config)
    
    # Extract JSON from response
    planning_result = {}
    try:
        # Find JSON in the response
        response_content = response["messages"][-1].content
        
        # Try to extract JSON from the response
        import re
        json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', response_content, re.DOTALL)
        if json_match:
            json_str = json_match.group(0)
            planning_result = json.loads(json_str)
            
            logger.info(f"Planning completed for module: {planning_result.get('module_name', 'unknown')}")
        else:
            logger.warning("No valid JSON found in planner response")
            planning_result["has_enough_context"] = False
            planning_result["additional_info_needed"] = "No valid JSON found in planner response"
            return Command(
                goto="__end__",
            )
            
    except (json.JSONDecodeError, KeyError) as e:
        logger.error(f"Error parsing planner response: {e}")
        planning_result["has_enough_context"] = False
        planning_result["additional_info_needed"] = "Failed to parse planning response"
        return Command(
            goto="__end__",
        )
    
    # Check if we have enough context to proceed
    module_name = planning_result.get("module_name", "unname")
    if planning_result.get("has_enough_context", False):
        return Command(
            update={
                "current_plan": planning_result,
                "messages": [AIMessage(content=response_content, name="planner")],
                "module_name": module_name,
                "project_name": module_name,  # 项目名称与模块名称同步
                "module_description": planning_result.get("module_description", ""),
                "module_definition": planning_result.get("module_definition", ""),
                "requirements": planning_result.get("requirements", ""),
                "has_enough_context": True,
                "additional_info_needed": "",
            },
            goto="human_feedback",
        )
    else:
        # Need more information from user
        additional_info = planning_result.get("additional_info_needed", "More information needed")
        return Command(
            update={
                "messages": [AIMessage(content=f"I need more information to proceed: {additional_info}", name="planner")],
                "has_enough_context": False,
                "additional_info_needed": additional_info,
            },
            goto="human_feedback",
        )


def code_planner_node(state: State, config: RunnableConfig) -> Command[Literal["human_feedback", "coder"]]:
    """ FPGA Code_Planner Agent - 根据实现需求采用自然语言描述FPGA模块的设计 """
    logger.info("Starting FPGA code planning...")

    # Invoke code_planner agent 调用code_planner智能体
    response = code_planner_agent.invoke(state, config)
    response_content = response["messages"][-1].content

    if response_content:
        logger.info(f"FPGA code design generated for module: {state.get('module_name', 'unknown')}")

        return Command(
            update={
                "messages": [AIMessage(content=response_content, name="code_planner")],
                "additional_info_needed": "",
            },
            goto="human_feedback",
        )
    else:
        logger.error(f"Fail to generate FPGA code design for module: {state.get('module_name', 'unknown')}")

        return Command(
            update={
                "additional_info_needed": "Fail to generate FPGA code design",
            },
            goto="human_feedback",
        )


def coder_node(state: State, config: RunnableConfig) -> Command[Literal["human_feedback"]]:
    """FPGA Coder node - generates Verilog/SystemVerilog code."""
    logger.info("Starting FPGA code generation...")
        
    # Invoke coder agent 调用coder智能体
    response = coder_agent.invoke(state, config)
    response_content = response["messages"][-1].content
    
    # Extract generated code using verilog_extractor  提取生成内容中的代码部分
    generated_code = extract_verilog_code(response_content)
    
    if generated_code:
        logger.info(f"Code generated for module: {state.get('module_name', 'unknown')}")
        
        # 先保存代码到文件，无论语法是否正确
        project_name = state.get('project_name', state.get('module_name', 'unknown'))
        module_name = state.get('module_name', 'unknown')
        
        # 定义workspace目录
        workspace_dir = Path(__file__).parent.parent / "workspace"

        # 创建项目
        try:
            creating_result, creating_information = create_project(project_name, workspace_path=workspace_dir)
            if creating_result:
                logger.info(f"Project '{project_name}' created successfully.")
            else:
                logger.error(f"Failed to create project: {creating_information}")
        except Exception as e:
            logger.error(f"Failed to creat project: {e}")
        
        # 在项目文件下创建源文件目录
        try:
            source_files_dir = workspace_dir.joinpath(project_name, f"{project_name}.srcs", "sources_1", "new")
            source_files_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Source directory created: {source_files_dir}")
        except Exception as e: 
            logger.error(f"Failed to create source files directory: {e}")
        
        # 保存代码文件
        code_file_path = source_files_dir / f"{module_name}.v"
        try:
            with open(code_file_path, 'w', encoding='gb18030') as f:
                f.write(generated_code)
            logger.info(f"Code saved to: {code_file_path}")
            save_message = f"Code saved to {code_file_path}"
        except Exception as e:
            logger.error(f"Failed to save code file: {e}")
            save_message = f"Failed to save code: {e}"
            is_valid = False
            validation_message = f"File save failed: {e}"
        
        # 将代码提交至 vivado 项目中
        try:
            adding_result, adding_message = add_files_to_project(project_name, workspace_path=workspace_dir, source_files=[str(code_file_path)])
            if adding_result:
                logger.info(adding_message)
            else:
                logger.error(adding_message)
        except Exception as e:
            logger.error(f"Failed to add sources to {project_name}: {e}")
       
        # 采用Vivado进行语法验证
        is_valid, validation_message = validate_verilog_syntax_vivado(project_name, workspace_dir, [str(code_file_path)])
        
        if is_valid:
            logger.info(f"{validation_message}")
            return Command(
                update={
                    "messages": [AIMessage(content=f"{response_content}\n\n{save_message}\nSyntax validation: PASSED - {validation_message}", name="coder")],
                    "module_code": generated_code,
                    "additional_info_needed": "",
                },
                goto="human_feedback",
            )
        else:
            logger.warning(f"{validation_message}")
            return Command(
                update={
                    "messages": [AIMessage(content=f"{response_content}\n\n{save_message}\nSyntax validation: FAILED\n{validation_message}", name="coder")],
                    "module_code": generated_code,
                    "additional_info_needed": f"语法错误，请你手动解决这个问题",
                },
                goto="human_feedback",
                )
    else:
        logger.warning("No Verilog code found in coder response")
        return Command(
            update={
                "messages": [AIMessage(content=f"Failed to extract Verilog code from response:\n{response_content} . Please check the requirements.", name="coder")],
                "additional_info_needed": f"生成内容为:{generated_code}\n其中没有提取到verilog代码",
            },
            goto="human_feedback",
        )


def test_planner_node(state: State, config: RunnableConfig) -> Command[Literal["human_feedback", "tester"]]:
    """ FPGA Test_Planner Agent - 根据实现需求设计FPGA模块的测试（采用自然语言描述） """
    logger.info("Starting FPGA test planning...")

    state_copy = copy.deepcopy(state)

    # 筛选上下文，排除编写代码部分的聊天内容
    state_copy["messages"] = [
        m for m in state["messages"]
        if m.name not in ["code_planner", "coder", "user_code"]
    ]

    # Invoke test_planner agent 调用test_planner智能体
    response = test_planner_agent.invoke(state_copy, config)
    response_content = response["messages"][-1].content

    if response_content:
        logger.info(f"FPGA test design generated for module: {state.get('module_name', 'unknown')}")

        return Command(
            update={
                "messages": [AIMessage(content=response_content, name="test_planner")],
                "additional_info_needed": "",
            },
            goto="human_feedback",
        )
    else:
        logger.error(f"Fail to generate FPGA test design for module: {state.get('module_name', 'unknown')}")

        return Command(
            update={
                "additional_info_needed": "Fail to generate FPGA test design",
            },
            goto="human_feedback",
        )


def tester(state: State, config: RunnableConfig) -> Command[Literal["human_feedback"]]:
    """FPGA Tester node - generates test benches and test cases."""
    logger.info("Starting FPGA test generation...")

    state_copy = copy.deepcopy(state)

    # 筛选上下文，排除编写代码部分的聊天内容
    state_copy["messages"] = [
        m for m in state["messages"]
        if m.name not in ["code_planner", "coder", "user_code"]
    ]
    
    # Invoke tester agent
    response = tester_agent.invoke(state_copy, config)
    response_content = response["messages"][-1].content
    
    # Extract testbench code using verilog_extractor
    testbench_code = extract_verilog_code(response_content)
   
    if testbench_code:
        logger.info("Testbench code extracted successfully")

        project_name = state.get('project_name', state.get('module_name', 'unknown'))
        module_name = state.get('module_name', 'unknown')
        
        # 定义workspace目录
        workspace_dir = Path(__file__).parent.parent / "workspace"

        # 读取源码
        try:
            source_file = workspace_dir.joinpath(project_name, f"{project_name}.srcs", "sources_1", "new", f"{module_name}.v")
            with open(source_file, 'r', encoding='gb18030') as f:
                source_code = f.read()
            logger.info(f"Source code read from {source_file}")
        except Exception as e:
            logger.error(f"Failed to read source file: {e}")

        # 验证新生成的代码是否为源代码（当前存在对话时输出的testbench为源设计代码，并非testbench）
        try:
            if judge_same_code(source_code, testbench_code):
                logger.warning("The generated code is source code, not a testbench!")
                return Command(
                    update={
                        "messages": [AIMessage(content=f"{response_content}\n\nThe generated code is source code,\
                         not a testbench!", name="tester")],
                        "additional_info_needed": f"生成内容为:{response_content}\n其中的testbench代码与源代码重复，请检查！",
                    },
                    goto="human_feedback",
                )
        except Exception as e:
            logger.warning(f"Failed to judge code similarity: {e}")

        # 先保存测试台代码到文件，无论语法是否正确
        # 创建目录
        try:
            sim_dir = workspace_dir.joinpath(project_name, f"{project_name}.srcs", "sim_1", "new")
            sim_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Directory created: {workspace_dir}")
        except Exception as e:
            logger.error(f"Failed to create directory: {e}")
        
        # 保存代码文件
        testbench_file_path = sim_dir / f"tb_{module_name}.v"
        try:
            with open(testbench_file_path, 'w', encoding='gb18030') as f:
                f.write(testbench_code)
            logger.info(f"Code saved to: {testbench_file_path}")
            save_message = f"Code saved to {testbench_file_path}"
        except Exception as e:
            logger.error(f"Failed to save code file: {e}")
            save_message = f"Failed to save code: {e}"
            is_valid = False
            validation_message = f"File save failed: {e}"

        # 将仿真文件添加至vivado项目中
        try:
            adding_result, adding_message = add_sim_files_to_project(project_name, workspace_dir, [str(testbench_file_path)])
            if adding_result:
                logger.info(adding_message)
            else:
                logger.error(adding_message)
        except Exception as e:
            logger.error(f"Failed to add sim files to project {project_name}: {e}")

        # 验证语法,需要组合源代码和测试代码
        is_valid, validation_message = validate_verilog_syntax_vivado(project_name, workspace_dir, [str(testbench_file_path)])
        if is_valid:
            logger.info(f"Testbench syntax : {validation_message}")

            return Command(
                update={
                    "messages": [AIMessage(content=f"{response_content}\n\n{save_message}\n\
                        Syntax validation: PASSED - {validation_message}", name="tester")],
                    "testbench_code": testbench_code,
                    "additional_info_needed": "",
                },
                goto="human_feedback",
            )
        else:
            logger.warning(f"Testbench syntax validation failed: {validation_message}")
            return Command(
                update={
                    "messages": [AIMessage(content=f"{response_content}\n\n{save_message}\nSyntax validation: FAILED\n\
                        {validation_message}", name="tester")],
                    "testbench_code": testbench_code,
                    "additional_info_needed": f"testbench代码编译出现错误，请你手动解决这个问题",
                },
                goto="human_feedback",
            )
    else:
        logger.warning("No testbench code found in tester response")
        return Command(
            update={
                "messages": [AIMessage(content="Failed to extract testbench code from response. Please review.", name="tester")],
                "additional_info_needed": f"生成内容为:{response_content}\n没有提取到testbench的verilog代码",
            },
            goto="human_feedback",
        )


def logic_test_node(state: State) -> Command[Literal["__end__"]]:
    """ 该节点专门用于逻辑测试：原本处于tester内部的逻辑测试操作移至此处 """
    logger.info("Starting logic test...")

    project_name = state.get('project_name', state.get('module_name', 'unknown'))
    module_name = state.get('module_name', 'unknown')
    workspace_dir = Path(__file__).parent.parent / "workspace"
    testbench_file_path = workspace_dir.joinpath(project_name, f"{project_name}.srcs", "sim_1", "new", f"tb_{module_name}")

    # 执行逻辑验证
    logic_is_valid, logic_validation_message = validate_verilog_logic_vivado(project_name, workspace_dir, str(testbench_file_path))

    if logic_is_valid:
        logger.info(f"Testbench logic : {logic_validation_message}")
        return Command(
            goto="__end__",
        )
    else:
        logger.warning(f"Testbench logic validation failed: {logic_validation_message}")
        return Command(
            goto="__end__"
        )


def human_feedback_node(
    state,
) -> Command[Literal["planner", "coder", "tester", "__end__"]]:
    # check if the plan is auto accepted
    auto_accepted_plan = state.get("auto_accepted_plan", False)

    #从上一条消息判断是哪个节点发过来的
    last_message = state["messages"][-1]
    last_message_name = last_message.name
    #log一下上个节点名称
    logger.info(f"last message name: {last_message_name}")

    if last_message_name == "planner":
        print("\nplanner")
        if not state.get("has_enough_context", False):
            additional_info = state.get("additional_info_needed", "")
            logger.info(f"当前计划的状态: has_enough_context：{state.get('has_enough_context')}, 需要更多信息: {additional_info}")
            if not additional_info:
                return Command(
                update={
                    "messages": [
                        HumanMessage(content="你想让我提供哪些信息呢？", name="user"),
                    ],
                },
                goto="planner",
            )
            else:
                feedback = interrupt(f"Planner需要更多的信息: {additional_info}")
                return Command(
                    update={
                        "messages": [
                            HumanMessage(content=feedback, name="user"),
                        ],
                        "additional_info_needed": "",
                    },
                    goto="planner",
                )
        if not auto_accepted_plan:
            feedback = str(interrupt("Please Review the Plan.如果没有问题,请输入[ok]")).strip()
            # if the feedback is not accepted, return the planner node            
            if feedback.upper() == "OK":
                #用户接收了计划。
                logger.info("Plan is accepted by user.")
                return Command(
                    goto="code_planner"
                )
            else:
                return Command(
                    update={
                        "messages": [
                            HumanMessage(content=feedback, name="user"),
                        ],
                    },
                    goto="planner",
                )
    
    elif last_message_name == "code_planner":
        print("code_planner")
        additional_info = state.get("additional_info_needed", "")
        # 对于计划制定时出现异常情况
        if additional_info:
            feedback = str(interrupt(f"code_planner运行时出现异常:\n{additional_info}"))
            return Command(
                update={
                    "messages": [HumanMessage(content=feedback, name="user_code"), ],
                    "additional_info_needed": "",
                },
                goto="code_planner"
            )
        # 对于正常情况
        else:
            if not state.get("auto_accepted_plan", False):
                feedback = str(interrupt("Please Review the Code Plan.如果没有问题,请输入[ok]")).strip()
                if feedback.upper() == "OK":
                    #用户接收了计划。
                    logger.info("Code plan is accepted by user.")
                    return Command(
                        goto="coder"
                    )
                else:
                    return Command(
                        update={
                            "messages": [HumanMessage(content=feedback, name="user_code")],
                            "additional_info_needed": "",
                        },
                        goto="code_planner",
                    )
            
    elif last_message_name == "coder":
        print("coder")
        additional_info = state.get("additional_info_needed", "")
        if additional_info:
            feedback = interrupt(f"coder遇到了问题:\n{additional_info}")
            return Command(
                update={
                    "messages": [HumanMessage(content=feedback, name="user_code")],
                    "additional_info_needed": "",
                }, 
                goto="coder",
            )

        feedback = str(interrupt("Please Review the Code.如果没有问题,请输入[ok]")).strip()
        # if the feedback is not accepted, return the coder node
        if feedback.upper() == "OK":
            #用户接收了代码。
            feedback = interrupt("测试代码需要我来帮你写吗？还是你自己提供？自己提供请输入[1]需要我帮你写请输入[2]").strip()
            if feedback == "1":
                return Command(
                    goto="__end__",
                )
            elif feedback == "2":
                return Command(
                    goto="test_planner",
                )
            else:
                return Command(
                    goto="__end__",
                )
        else:
            return Command(
                update={
                    "messages": [
                        HumanMessage(content=feedback, name="user_code"),
                    ],
                },
                goto="coder",
            )
    
    elif last_message_name == "test_planner":
        print("test_planner")
        additional_info = state.get("additional_info_needed", "")
        # 对于计划制定时出现异常情况
        if additional_info:
            feedback = str(interrupt(f"test_planner运行时出现异常:\n{additional_info}"))
            return Command(
                update={
                    "messages": [HumanMessage(content=feedback, name="user_test"), ],
                    "additional_info_needed": "",
                },
                goto="test_planner"
            )
        # 对于正常情况
        else:
            if not state.get("auto_accepted_plan", False):
                feedback = str(interrupt("Please Review the Test Plan.如果没有问题,请输入[ok]")).strip()
                if feedback.upper() == "OK":
                    #用户接收了计划。
                    logger.info("Test plan is accepted by user.")
                    return Command(
                        goto="tester"
                    )
                else:
                    return Command(
                        update={
                            "messages": [HumanMessage(content=feedback, name="user_test")],
                            "additional_info_needed": "",
                        },
                        goto="test_planner",
                    )

    elif last_message_name == "tester":
        print("tester")
        additional_info = state.get("additional_info_needed", "")
        if additional_info:
            feedback = interrupt(f"tester遇到了问题:\n{additional_info}")
            return Command(
                update={
                    "messages": [
                        HumanMessage(content=feedback, name="user_test"),
                    ],
                    "additional_info_needed": "",
                },
                goto="tester",
            )
        feedback = str(interrupt("Please Review the testbecnh Code.如果没有问题,请输入[ok]")).strip()
        # if the feedback is not accepted, return the coder node
        if feedback.upper() == "OK":
            #用户接收了代码。
            return Command(
                goto="logic_test",
            )
        else:
            return Command(
                update={
                    "messages": [
                        HumanMessage(content=feedback, name="user_test"),
                    ],
                },
                goto="tester",
            )

