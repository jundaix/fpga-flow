# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

# class MessagesState(TypedDict):
#     messages: Annotated[list[AnyMessage], add_messages]
from typing import Dict, List, Any

from langgraph.graph import MessagesState

class State(MessagesState):
    """State for the agent system, extends MessagesState with next field."""

    # 用于保存运行过程中的重要上下文信息
    module_name: str = ""                               # 模块名称
    project_name: str = ""                              # 项目名称，当前定义下与模块名称一致
    module_descrption: str = ""                         # 模块描述，根据人类的需求给出模块所实现的功能的描述
    module_interface: str = ""                          # 模块接口，根据人类的需求给出模块的输入输出端口（即Verilog的module头部信息）
    has_enough_context: bool = False                    # 指出当前的 协调者 是否从人类这里得到了充足的信息，若是自动化处理应该设定为 True
    requirement: str = ""                               # 记录这个模块的实现要求

    timing_proposing: str = ""                     # 记录这个模块的时序特征描述（由专门的 agent 生成）
    sub_module_choose: List[Dict[str, Any]] = []        # 用于后续调用子模块时采用，各个调用的子模块以及其参数设置均由这个列表保存

    module_code_plan: str = ""                          # 记录这个模块的代码实现计划（由专门的 agent 生成，自然语言文本编写）
    module_code: str = ""                               # 记录这个模块的代码实现（由专门的 agent 生成，Verilog代码编写）
    module_code_syntax_error = ""                       # 经过多轮迭代后若代码仍存在语法错误，则进行记录

    testbench_code_plan: str = ""                       # 记录这个模块的测试代码实现计划（由专门的 agent 生成，自然语言文本编写
    testbench_code: str = ""                            # 记录这个模块的测试代码实现（由专门的 agent 生成，Verilog代码编写）
    testbench_code_syntax_error = ""                    # 经过多轮迭代后若测试代码仍存在语法错误，则进行记录

    logic_result: bool = False                          # 记录这个模块的逻辑验证是否通过，若通过则为 True，初始默认设置为 False
    logic_error: str = ""                               # 若逻辑验证未通过，则记录这个模块的逻辑验证错误信息

    additional_info_needed: str = ""                      # 各个 agent 运行出现异常时，向人类反馈的文本
    auto_accepted_plan: bool = False                    # 若自动生成的计划被人类接受，则为 True，初始默认设置为 False

    task_finished: Dict[str, bool] = {                  # 用于向 planner 声明当前已经完成了哪些任务
        "timing_analyse": False,
        "module_code_writing": False,
        "testbench_writing": False,
        "logic_test": False
    }
    next_step: str = "None"                             # 用于保存 planner 给出的下一步的操作
    next_step_suggest: str = ""                         # 用于保存 planner 给出的下一步的建议   
