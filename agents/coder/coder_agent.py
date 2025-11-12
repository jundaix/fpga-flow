"""
    FPGA Coder Agent - 生成Verilog/SystemVerilog代码
"""

from langgraph.graph import MessagesState
from pydantic import BaseModel, Field

from ..fpga_agents import create_fpga_agent


# Your output will be processed by subsequent programs (not by humans), so your output must follow the format below:
# output_format = """
# You must adjust your output results according to the following requirements:
# Only output the code body; apart from code comments, no explanations or ``` fences are allowed; the 'analysis' and 'plan' content prior to code generation must be excluded.
# """

# ''' 通过 Pydantic 约束模型的输出格式 '''
# class Code_Output(BaseModel):
#     code: str = Field(
#         ...,
#         min_length=1,
#         description="Only the output code body"
#     )

#     # 严禁多余字段
#     model_config = {"extra": "forbid"}


# def coder_agent_pre_hook(state: MessagesState):
#     """ 添加一段关于输出格式的约束要求 """
#     state["messages"].append(HumanMessage(content=output_format))

#     return {"messages": state["messages"]}


coder_agent = create_fpga_agent(
    agent_name="coder", 
    agent_type="coder", 
    tools=[], 
    prompt_template="code_writer",
)