from typing import List, Any, Dict
from langgraph.graph import MessagesState
from pydantic import Field

class State_coder(MessagesState):
    """ 用于维护子任务代码编写的 agent 的状态 """
    module_requirements: str = ""                           # 暂时用于适配 Verilog-eval 数据集的实现
    module_name: str = ""                                   # 模块名称或问题名称，用于标识保存位置

    module_code: str = ""                                   # 记录 LLM 输出的当前的代码实现

    syntax_error_source: str = ""                           # 上一次语法错误的原始反馈信息
    module_code_syntax_error: List[Dict[str, str]]          # 保存 LLM 曾经出现过的各项语法错误，每一项分别包含错误类型，错误解释，错误代码案例
    module_code_logic_error: str = ""                       # 记录 LLM 输出的当前代码实现中存在的逻辑错误
    else_error: str = ""                                    # 记录其它情况放下的错误反馈

    is_syntax_error: bool = False                           # 指出这次代码生成任务是否出现语法错误
    is_logic_error: bool = False                            # 指出这次代码生成是否出现逻辑错误
    is_else_error: bool = False                             # 指出这次代码生成是否出现其他错误（如代码生成失败）

    trying_times: int = 0                                    # 记录当前任务下出错后的重试次数
    MAX_TRY_TIMES: int = 5                                # 定义最大重试次数


def updata_list(state, list_entries: str, value: Any) -> List[Any]:
    if not isinstance(value, list):
        value = [value]
    new_list = state[list_entries] + value
    return new_list
