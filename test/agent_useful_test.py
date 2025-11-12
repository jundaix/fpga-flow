from agents import coder_agent, code_syntax_err_analyst
from langchain_core.messages import HumanMessage
import time
from utils import parse_llm_json_first, parse_llm_json_first
import json

def agent_test():
    validation_message = """counter_8bit_enable_reset.v:21: syntax error
                            counter_8bit_enable_reset.v:23: Syntax in assignment statement l-value."""

    code = """
// Module: counter_8bit_enable_reset
// Description:
//   This module implements an 8-bit synchronous binary counter with enable and 
//   synchronous active-low reset functionality. The counter increments by 1 on each
//   rising edge of the clock when enable is asserted. If the reset is asserted low,
//   the counter resets to 0 synchronously at the next clock rising edge.

module counter_8bit_enable_reset (
    input wire clk,          // Clock input
    input wire rst_n,        // Active low synchronous reset input
    input wire enable,       // Enable counting when high
    output reg [7:0] count   // 8-bit counter output
);

    // Sequential logic: count update
    // On each rising edge of clk, check reset and enable signals.
    always @(posedge clk) begin
        if (!rst_n) begin
            // When reset is active (low), reset count to zero synchronously
            count <= 8'd0
        end else if (enable) begin
            // If enable is high, increment count by 1
            cnt <= count + 1'b1;
        end else begin
            // If enable is low, hold the current count value
            count <= count;
        end
    end

endmodule
    """

    request = f"""
            Please parse the following syntax error content and provide a clear and concise description of the error.\
            syntax error message:\n{validation_message}\nThe verilog code with syntax error:\n{code}
    """
    start_time = time.time()
    print(f"开始处理的时间：{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(start_time))}")

    response = code_syntax_err_analyst.invoke({"messages": [HumanMessage(content=request)]})
    response_content = response["messages"][-1].content

    # for event in coder_agent.stream({"messages": [{"role": "user", "content": fpga_request}]}):
    #     for value in event.values():
    #         messages = value.get("messages", [])
    #         if messages:
    #             for m in messages:
    #                 print(f"{m.type}: 【{m}】")
    #         else:
    #             print(value)

    is_json, json_result = parse_llm_json_first(response_content)
    if is_json:
        for error in json_result:
            print(f"数据类型：{type(error)}")
            print(f"语法错误类型: {error.get('error_type', '未知')}\n错误解释: {error.get('error_explanation', '无')}\n错误相关代码：{error.get('error_code_example', '无')}\n\n")
    else:
        print(f"识别存在问题:\n{response_content}")


    end_time = time.time()
    print(f"处理时间: {end_time - start_time} 秒")

def syntax_list_analyse():
    """ 将语法错误列表解析为字符串（列表元素仅为字典） """
    syntax_list = [
        {"error_type": "syntax error1", "error_explanation": "syntax error message1", "error_code_example": "code with syntax error1"},
        {"error_type": "syntax error2", "error_explanation": "syntax error message2", "error_code_example": "code with syntax error2"},
    ]
    syntax_list_str = json.dumps(syntax_list, ensure_ascii=False, indent=2, sort_keys=True)
    prompt_text = "Some grammatical errors you need to avoid:\n" + syntax_list_str
    print(prompt_text)

if __name__ == "__main__":
    # agent_test()
    syntax_list_analyse()