# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

# class MessagesState(TypedDict):
#     messages: Annotated[list[AnyMessage], add_messages]

from langgraph.graph import MessagesState

class State(MessagesState):
    """State for the agent system, extends MessagesState with next field."""

    # Runtime Variables
    current_plan: str = ""                  # 当前的计划，用于后续的代码生成和测试流程

    module_name: str = ""                   # 项目名称，与module_name同步，由plan_agent生成
    project_name: str = ""                  # 项目名称，与module_name同步，由plan_agent生成
    module_description: str = ""            # 模块的描述（用于模块的实现），由plan_agent生成
    module_definition: str = ""             # 模块的定义，即模块头，包含模块名称和IO端口部分（用于模块的实现），由plan_agent生成

    module_code: str = ""                   # 模块的设计代码，由code_agent生成
    testbench_code: str = ""                # 模块的测试代码，由test_agent生成

    requirements: str = ""                  # 记录人类的要求
    
    has_enough_context: bool = False        # 是否需要更多信息的标志位，标识plan_agent生成的计划是否足够后续运行
    additional_info_needed: str = ""        # 各个agent运行出现异常时，向人类反馈的文本
    auto_accepted_plan: bool = False        # 是否自动的接受可行的计划
