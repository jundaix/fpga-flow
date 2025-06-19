# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

from typing import Literal

# 定义可以使用的LLM类型
LLMType = Literal["basic", "reasoning", "vision"]

# 定义运行的代理和使用的LLM类型的映射
AGENT_LLM_MAP: dict[str, LLMType] = {
    "planner": "basic",
    "coder": "basic",
    "tester": "basic",
}
