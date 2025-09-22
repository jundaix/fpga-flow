"""
    FPGA Coder Agent - 生成Verilog/SystemVerilog代码
"""

from langgraph.graph import MessagesState
from langchain_core.messages import HumanMessage

from ..fpga_agents import create_fpga_agent


output_format = """
Your output will be processed by subsequent programs (not by humans), so your output must follow the format below:
<think>
 <analyze>
 </analyze>
 <plan>
 </plan>
</think>
```verilog

```
"""

def coder_agent_pre_hook(state: MessagesState):
    """ 添加一段关于输出格式的约束要求 """
    state["messages"].append(HumanMessage(content=output_format))

    return {"llm_input_messages": state["messages"]}

coder_agent = create_fpga_agent(
    "coder", 
    "coder", 
    [], 
    "code_writer",
    pre_hook=coder_agent_pre_hook
)