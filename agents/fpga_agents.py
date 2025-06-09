# -*- coding: utf-8 -*-
# SPDX-License-Identifier: MIT

from langgraph.prebuilt import create_react_agent
from typing import List, Dict, Any

from prompts.template import apply_prompt_template

from llms.llm import get_llm_by_type
from config.agents import AGENT_LLM_MAP


def create_fpga_agent(agent_name: str, agent_type: str, tools: list, prompt_template: str):
    """Factory function to create FPGA-specific agents with consistent configuration."""
    return create_react_agent(
        name=agent_name,
        model=get_llm_by_type(AGENT_LLM_MAP.get(agent_type, "basic")),
        tools=tools,
        prompt=lambda state: apply_prompt_template(prompt_template, state),
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