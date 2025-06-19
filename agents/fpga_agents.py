# -*- coding: utf-8 -*-
# SPDX-License-Identifier: MIT

from langgraph.prebuilt import create_react_agent
from typing import List, Dict, Any

from prompts.template import apply_prompt_template

from llms.llm import get_llm_by_type
from config.agents import AGENT_LLM_MAP


def create_fpga_agent(agent_name: str, agent_type: str, tools: list, prompt_template: str):
    """ 采用工厂模式创建具有一致配置的FPGA特定代理 """
    return create_react_agent(
        name=agent_name,
        model=get_llm_by_type(AGENT_LLM_MAP.get(agent_type, "basic")),      # 根据agent类型从AGENT_LLM_MAP读取llm类型（默认为basic）
        tools=tools,                                                        # 可以使用的工具，当前不使用，默认为空
        prompt=lambda state: apply_prompt_template(prompt_template, state),
        # 将prompt参数设成了一个匿名函数，接收当前 Agent 的对话状态state，
        # 调用apply_prompt_template从对应的.md文件中提取模板并与state的内容进行渲染，返回结构化的信息
        # 每当Agent“要生成下一条回复”时，执行这个函数，动态地把最新的上下文带入模板里，保证系统提示（System Prompt）始终和当前对话状态同步
    )

# FPGA Planner Agent - 制定开发计划和任务分解
planner_agent = create_fpga_agent(
    "planner", 
    "planner", 
    [], 
    "fpga_planner"
)

# FPGA Coder Agent - 生成Verilog/SystemVerilog代码
coder_agent = create_fpga_agent(
    "coder", 
    "coder", 
    [], 
    "fpga_coder"
)

tester_agent = create_fpga_agent(
    "tester",
    "tester",
    [],
    "fpga_tester"
)

# 导出所有FPGA智能体
__all__ = [
    "planner_agent", 
    "coder_agent",
    "tester_agent"
]