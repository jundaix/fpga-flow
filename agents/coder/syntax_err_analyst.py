"""
    该 Agent 在验证出现语法错误时，会返回错误类型和错误代码示例
"""

from langgraph.graph import MessagesState
from langchain_core.messages import HumanMessage

from ..fpga_agents import create_fpga_agent


output_format = """
Your output will be processed by subsequent programs (not by humans), so your output must follow the format below:

<error_type>
Identify the type of syntax error
</error_type>
<error_code_example>
Provide erroneous code examples
</error_code_example>
"""

def syntax_err_analyst_pre_hook(state: MessagesState):
    """ 添加一段关于输出格式的约束要求 """
    state["messages"].append(HumanMessage(content=output_format))

    return {"llm_input_messages": state["messages"]}

code_syntax_err_analyst = create_fpga_agent(
    "syntax_err_analys",
    "analyst",
    [],
    "fpga_syntax_analysis",
    pre_hook=syntax_err_analyst_pre_hook,
)