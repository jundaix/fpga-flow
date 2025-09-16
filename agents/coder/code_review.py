"""
    该 Agent 比对代码实现和实现要求，判断是否满足需要
"""

from langgraph.graph import MessagesState
from langchain_core.messages import HumanMessage

from ..fpga_agents import create_fpga_agent


output_format = """
Your output will be processed by subsequent programs (not by humans), so your output must follow the format below:

```json
{
    "reason": "Your reasoning when comparing code implementations and checking for logical errors",
    "meet_requirements": true/false,
    "error_explanation": "If the code has logical errors or does not meet the requirements, provide a detailed explanation of the errors and their locations. If the code is correct, this field should be empty."
}
```
"""

def code_review_pre_hook(state: MessagesState):
    """ 添加一段关于输出格式的约束要求 """
    state["messages"].append(HumanMessage(content=output_format))
    return {"llm_input_messages": state["messages"]}

code_review = create_fpga_agent(
    "code_review",
    "analyst",
    [],
    "fpga_code_review",
    pre_hook=code_review_pre_hook,
)