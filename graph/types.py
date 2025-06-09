# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

from langgraph.graph import MessagesState

class State(MessagesState):
    """State for the agent system, extends MessagesState with next field."""

    # Runtime Variables
    current_plan: str = ""

    module_name: str = ""
    project_name: str = ""  # 项目名称，与module_name同步
    module_description: str = ""
    module_definition: str = ""

    module_code: str = ""
    testbench_code: str = ""

    requirements: str = ""
    
    has_enough_context: bool = False
    additional_info_needed: str = ""
    auto_accepted_plan: bool = False


