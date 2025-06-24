import numpy as np
from .embedding import embedding_model

def cosine_similarity_np(a: list[float], b: list[float]) -> float:
    a_arr = np.array(a, dtype=np.float64)
    b_arr = np.array(b, dtype=np.float64)

    # np.dot 计算点积，np.linalg.norm 计算 L2 范数
    num = np.dot(a_arr, b_arr)
    den = np.linalg.norm(a_arr) * np.linalg.norm(b_arr)
    if den == 0:
        return 0.0
    return num / den

if __name__ == "__main__":
    # 设置嵌入的文本
    test_str_a1 = """
// 8-bit counter with enable and synchronous active low reset
module counter_8bit_enable_reset (
    input wire clk,            // Clock input
    input wire rst_n,          // Active low synchronous reset input
    input wire enable,         // Enable signal to increment counter
    output reg [7:0] count     // 8-bit counter output
);

// Synchronous counter logic
always @(posedge clk) begin
    if (!rst_n) begin
        // When reset is active (low), reset the counter to zero
        count <= 8'b0;
    end else if (enable) begin
        // When enable is high, increment the counter
        count <= count + 1'b1;
    end
    // When enable is low, hold the current count value
end

endmodule
    """

    test_str_a2 = """
`timescale 1ns/1ps

module tb_counter_8bit_enable_reset;

    // Clock period definition
    parameter CLK_PERIOD = 10;

    // Inputs to the module under test (dut)
    reg clk;
    reg rst_n;
    reg enable;

    // Outputs from the dut
    wire [7:0] count;

    // Instantiate the counter module (module under test)
    counter_8bit_enable_reset uut (
        .clk(clk),
        .rst_n(rst_n),
        .enable(enable),
        .count(count)
    );

    // Clock generation: 10ns period clock (100 MHz for example)
    initial begin
        clk = 0;
        forever #(CLK_PERIOD/2) clk = ~clk;
    end

    // Test sequence
    initial begin
        // Initialization of signals
        rst_n = 0;
        enable = 0;

        // Assert reset for 3 clock cycles
        repeat (3) @(posedge clk);
        rst_n = 1; // Release reset
        @(posedge clk);

        // Check reset effect: counter should be zero
        check_count(8'd0, "Reset Release Check");

        // Enable counting
        enable = 1;

        // Count upwards from 0 to 10
        count_up(8'd10);

        // Disable enable: count should remain constant
        enable = 0;
        hold_count(5);  // Hold for 5 clock cycles

        // Enable again and count to max (255) to test overflow wrap-around
        enable = 1;
        count_to_max_and_overflow();

        // Final test passed
        $display("[PASS] All test cases passed successfully at time %0t", $time);
        # (CLK_PERIOD * 10);
        $finish;
    end

    // Task to check the output count with assertion
    task check_count;
        input [7:0] expected;
        input string test_name;
    begin
        if (count !== expected) begin
            $error("[ERROR] %s failed at time %0t: expected %0h, got %0h", test_name, $time, expected, count);
            $finish;
        end else begin
            $display("[PASS] %s passed at time %0t: count = %0h", test_name, $time, count);
        end
    end
    endtask

    // Task: Count up for N cycles while enable is high and check correctness
    task count_up;
        input [7:0] cycles;
        integer i;
    begin
        for (i = 0; i < cycles; i = i + 1) begin
            @(posedge clk);
            check_count(i + 1, $sformatf("Counting up cycle %0d", i+1));
        end
    end
    endtask

    // Task: Hold the current count value for given clock cycles while enable is low
    task hold_count;
        input integer cycles;
        integer i;
        reg [7:0] stat_count;
    begin
        stat_count = count;
        for (i = 0; i < cycles; i = i +1) begin
            @(posedge clk);
            check_count(stat_count, $sformatf("Hold count cycle %0d", i+1));
        end
    end
    endtask

    // Task: Count from current position to max (255), then overflow to zero, verifying correct wrap-around
    task count_to_max_and_overflow;
        integer i;
        reg [7:0] start_val;
    begin
        start_val = count;
        // Count up until 255
        for (i = start_val; i < 8'd255; i = i + 1) begin
            @(posedge clk);
            check_count(i + 1, $sformatf("Counting to max from %0d", i+1));
        end
        // Next count should wrap around to 0
        @(posedge clk);
        check_count(8'd0, "Counter Overflow Wraparound Check");
    end
    endtask

endmodule
    """

    test_str_a3 = """
`timescale 1ns/1ps

module tb_counter_8bit_enable_reset;

// Clock period definition
parameter CLK_PERIOD = 10;

// Inputs to the module under test (dut)
reg clk;
reg rst_n;
reg enable;

// Outputs from the dut
wire [7:0] count;

// Instantiate the counter module (module under test)
counter_8bit_enable_reset uut (
    .clk(clk),
    .rst_n(rst_n),
    .enable(enable),
    .count(count)
);

// Clock generation: 10ns period clock (100 MHz for example)
initial begin
    clk = 0;
    forever #(CLK_PERIOD/2) clk = ~clk;
end

// Test sequence
initial begin
    // Initialization of signals
    rst_n = 0;
    enable = 0;

    // Assert reset for 3 clock cycles
    repeat (3) @(posedge clk);
    rst_n = 1; // Release reset
    @(posedge clk);

    // Check reset effect: counter should be zero
    check_count(8'd0, "Reset Release Check");

    // Enable counting
    enable = 1;

    // Count upwards from 0 to 10
    count_up(8'd10);

    // Disable enable: count should remain constant
    enable = 0;
    hold_count(5);  // Hold for 5 clock cycles

    // Enable again and count to max (255) to test overflow wrap-around
    enable = 1;
    count_to_max_and_overflow();

    // Final test passed
    $display("[PASS] All test cases passed successfully at time %0t", $time);
    # (CLK_PERIOD * 10);
    $finish;
end

// Task to check the output count with assertion
task check_count;
    input [7:0] expected;
    input [1023:0] test_name;  // Large enough fixed-size reg as workaround for string type
    integer i;
    reg [8*64:1] name_str;    // Convert reg to string for display
    begin
        // Convert reg to string (if printable characters)
        // Since we cannot use string type or $sformatf, just print the reg as is
        if (count !== expected) begin
            $error("[ERROR] %s failed at time %0t: expected %0h, got %0h", test_name, $time, expected, count);
            $finish;
        end else begin
            $display("[PASS] %s passed at time %0t: count = %0h", test_name, $time, count);
        end
    end
endtask

// Task: Count up for N cycles while enable is high and check correctness
task count_up;
    input [7:0] cycles;
    integer i;
begin
    for (i = 0; i < cycles; i = i + 1) begin
        @(posedge clk);
        check_count(i + 1, "Counting up cycle");
    end
end
endtask

// Task: Hold the current count value for given clock cycles while enable is low
task hold_count;
    input integer cycles;
    integer i;
    reg [7:0] stat_count;
begin
    stat_count = count;
    for (i = 0; i < cycles; i = i +1) begin
        @(posedge clk);
        check_count(stat_count, "Hold count cycle");
    end
end
endtask

// Task: Count from current position to max (255), then overflow to zero, verifying correct wrap-around
task count_to_max_and_overflow;
    integer i;
    reg [7:0] start_val;
begin
    start_val = count;
    // Count up until 255
    for (i = start_val; i < 8'd255; i = i + 1) begin
        @(posedge clk);
        check_count(i + 1, "Counting to max");
    end
    // Next count should wrap around to 0
    @(posedge clk);
    check_count(8'd0, "Counter Overflow Wraparound Check");
end
endtask

endmodule
    """

    test_str_b = """
// 8-bit counter with enable and synchronous active low reset
module counter_8bit_enable_reset (
    input wire clk,            // Clock input
    input wire rst_n,          // Active low synchronous reset input
    input wire enable,         // Enable signal to increment counter
    output reg [7:0] count     // 8-bit counter output
);

// Synchronous counter logic
always @(posedge clk) begin
    if (!rst_n) begin
        // When reset is active (low), reset the counter to zero
        count <= 8'b0;
    end else if (enable) begin
        // When enable is high, increment the counter
        count <= count + 1'b1;
    end 
    // When enable is low, hold the current count value
end

endmodule
    """
    # 计算嵌入向量
    embedding_a1 = embedding_model.embed_query(test_str_a1)
    embedding_a2 = embedding_model.embed_query(test_str_a2)
    embedding_a3 = embedding_model.embed_query(test_str_a3)
    embedding_b = embedding_model.embed_query(test_str_b)

    # 计算余弦相似度
    cos_sim_1 = cosine_similarity_np(embedding_a1, embedding_b)
    print(f"余弦相似度_1：{cos_sim_1}")

    cos_sim_2 = cosine_similarity_np(embedding_a2, embedding_b)
    print(f"余弦相似度_2：{cos_sim_2}")

    cos_sim_3 = cosine_similarity_np(embedding_a3, embedding_b)
    print(f"余弦相似度_3：{cos_sim_3}")