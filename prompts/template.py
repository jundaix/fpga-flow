# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
加载和渲染基于 Jinja2 模板的“系统提示”, 即system prompt, 并将渲染后的内容插入到一个消息列表(message list)中, 配合 langgraph 的对话代理(agent)一起使用。
"""

import os
import dataclasses
from datetime import datetime
from jinja2 import Environment, FileSystemLoader, select_autoescape
from langgraph.prebuilt.chat_agent_executor import AgentState
from config.configuration import Configuration

# Initialize Jinja2 environment
env = Environment(
    loader=FileSystemLoader(os.path.dirname(__file__)),             # 从脚本所在目录加载后缀为.md的模板文件
    autoescape=select_autoescape(),                                 # 对HTML/XML自动转义以确保安全
    trim_blocks=True,                                               # 去掉模板中多余的空行和行首空格
    lstrip_blocks=True,
)


def get_prompt_template(prompt_name: str) -> str:
    """
    Load and return a prompt template using Jinja2.
    只按名称(不带 .md)载入对应模板, 并直接调用 .render() 返回原始字符串

    Args:
        prompt_name: Name of the prompt template file (without .md extension)

    Returns:
        The template string with proper variable substitution syntax
    """
    try:
        template = env.get_template(f"{prompt_name}.md")
        return template.render()
    except Exception as e:
        raise ValueError(f"Error loading template {prompt_name}: {e}")


def apply_prompt_template(
    prompt_name: str, state: AgentState, configurable: Configuration = None
) -> list:
    """
    Apply template variables to a prompt template and return formatted messages.

    Args:
        prompt_name: Name of the prompt template to use
        state: Current agent state containing variables to substitute

    Returns:
        List of messages with the system prompt as the first message
    """
    # Convert state to dict for template rendering
    # 先把当前时间加入，再合并state(如用户输入，对话历史等), 如果有配置对象, 也展平成键值对加入
    state_vars = {
        "CURRENT_TIME": datetime.now().strftime("%a %b %d %Y %H:%M:%S %z"),
        **state,
    }

    # Add configurable variables
    if configurable:
        state_vars.update(dataclasses.asdict(configurable))

    try:
        # 提取系统模板，并返回带system消息的完整消息列表
        template = env.get_template(f"{prompt_name}.md")
        system_prompt = template.render(**state_vars)
        return [{"role": "system", "content": system_prompt}] + state["messages"]
    except Exception as e:
        raise ValueError(f"Error applying template {prompt_name}: {e}")
