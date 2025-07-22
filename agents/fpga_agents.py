# -*- coding: utf-8 -*-
# SPDX-License-Identifier: MIT

from langgraph.prebuilt import create_react_agent
from typing import List, Dict, Any, Optional

from prompts.template import apply_prompt_template

from llms.llm import get_llm_by_type
from config.agents import AGENT_LLM_MAP

from pydantic import BaseModel, Field


def create_fpga_agent(agent_name: str, agent_type: str, tools: list, prompt_template: str, structured_output: Any = None):
    """ 采用工厂模式创建具有一致配置的FPGA特定代理 """
    # 定义代理采用的 llm
    llm = get_llm_by_type(AGENT_LLM_MAP.get(agent_type, "basic"))           # 根据agent类型从AGENT_LLM_MAP读取llm类型（默认为basic）

    # 若要求 agent 进行结构化输出，则进行对应的设计
    if structured_output:
        llm = llm.with_structured_output(structured_output)

    return create_react_agent(
        name=agent_name,
        model=llm,
        tools=tools,                                                        # 可以使用的工具，当前不使用，默认为空
        prompt=lambda state: apply_prompt_template(prompt_template, state),
        # 将prompt参数设成了一个匿名函数，接收当前 Agent 的对话状态state，
        # 调用apply_prompt_template从对应的.md文件中提取模板并与state的内容进行渲染，返回结构化的信息
        # 每当Agent“要生成下一条回复”时，执行这个函数，动态地把最新的上下文带入模板里，保证系统提示（System Prompt）始终和当前对话状态同步
    )

# FPGA Coordinator Agent - 与用户交互，了解用户需求，整理实现内容，并按照要求进行结构化输出
coordinator_agent = create_fpga_agent(
    "coordinator", 
    "coordinator", 
    [], 
    "fpga_coordinator"
)

# FPGA Planner Agent - 利用已有的各个功能型 Agent 运行 Verilog 的开发流程
planner_agent = create_fpga_agent(
    "planner", 
    "planner", 
    [], 
    "fpga_planner"
)

# FPGA Time Analyse Agent - 根据功能的实现要求指出模块的时序特性
time_analyse_agent = create_fpga_agent(
    "time_analyst", 
    "analyst", 
    [], 
    "fpga_time_analyst"
)

# FPGA Code_Planner Agent - 根据实现需求采用自然语言描述FPGA模块的设计
code_planner_agent = create_fpga_agent(
    "code_planner", 
    "planner", 
    [],
    "fpga_code_planner"
)

# FPGA Coder Agent - 生成Verilog/SystemVerilog代码
coder_agent = create_fpga_agent(
    "coder", 
    "coder", 
    [], 
    "fpga_coder"
)

# FPGA Test_Planner Agent - 根据实现需要针对FPGA模块编写测试计划
test_planner_agent = create_fpga_agent(
    "test_planner", 
    "planner", 
    [],
    "fpga_test_planner"
)

tester_agent = create_fpga_agent(
    "tester",
    "tester",
    [],
    "fpga_tester"
)

# 导出所有FPGA智能体
__all__ = [
    "coordinator_agent",
    "planner_agent", 
    "time_analyse_agent",
    "coder_agent",
    "tester_agent", 
    "code_planner_agent", 
    "test_planner_agent"
]
