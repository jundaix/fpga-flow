import re
import logging
import json
from typing import Any

logger = logging.getLogger(__name__)

def get_json_info(source_content: Any) -> (bool, Any):
    """ 从 source_content 中提取 json 信息 """
    json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', source_content, re.DOTALL)

    try:
        if json_match:
            json_str = json_match.group(0)
            result = json.loads(json_str)

            return True, result

        else:
            return False, "There is no json content in the reply!"

    except (json.JSONDecodeError, KeyError) as e:
        logger.error(f"Error parsing coordinator response: {e}")
        return False, f"Error parsing coordinator response: {e}"

def get_error_info(source_content: str) -> str:
    pattern = r'^(?i:error:|critical warning:).*'
    matches = re.findall(pattern, source_content, flags=re.MULTILINE)

    return "\n".join(matches) + ("\n" if matches else "")


if __name__ == "__main__":
    std_message = """
INFO: [USF-XSim-98] Fetching design files from 'sim_1'...
INFO: [USF-XSim-2] XSim::Compile design
INFO: [USF-XSim-61] Executing 'COMPILE and ANALYZE' step in 'd:/Pycharm_Project/fpga-flow/workspace/counter_8bit_enable_reset/counter_8bit_enable_reset.sim/sim_1/behav/xsim'
INFO: [VRFC 10-2263] Analyzing Verilog file "d:/Pycharm_Project/fpga-flow/workspace/counter_8bit_enable_reset/counter_8bit_enable_reset.srcs/sim_1/new/tb_counter_8bit_enable_reset.v" into library xil_defaultlib
INFO: [VRFC 10-311] analyzing module counter_8bit_enable_reset
INFO: [VRFC 10-2263] Analyzing Verilog file "d:/Pycharm_Project/fpga-flow/workspace/counter_8bit_enable_reset/counter_8bit_enable_reset.sim/sim_1/behav/xsim/glbl.v" into library xil_defaultlib
INFO: [VRFC 10-311] analyzing module glbl
INFO: [USF-XSim-69] 'compile' step finished in '1' seconds
INFO: [USF-XSim-3] XSim::Elaborate design
INFO: [USF-XSim-61] Executing 'ELABORATE' step in 'd:/Pycharm_Project/fpga-flow/workspace/counter_8bit_enable_reset/counter_8bit_enable_reset.sim/sim_1/behav/xsim'
WARNING: [XSIM 43-4100] "d:/Pycharm_Project/fpga-flow/workspace/counter_8bit_enable_reset/counter_8bit_enable_reset.sim/sim_1/behav/xsim/glbl.v" Line 6. Module glbl has a timescale but at least one module in design doesn't have timescale.
INFO: [Common 17-206] Exiting Webtalk at Tue Jun 24 14:47:10 2025...
INFO: [USF-XSim-69] 'elaborate' step finished in '5' seconds
INFO: [USF-XSim-4] XSim::Simulate design
INFO: [USF-XSim-61] Executing 'SIMULATE' step in 'd:/Pycharm_Project/fpga-flow/workspace/counter_8bit_enable_reset/counter_8bit_enable_reset.sim/sim_1/behav/xsim'
INFO: [USF-XSim-98] *** Running xsim
INFO: [USF-XSim-8] Loading simulator feature
INFO: [USF-XSim-96] XSim completed. Design snapshot 'counter_8bit_enable_reset_behav' loaded.
INFO: [USF-XSim-97] XSim simulation ran for 1000ns
INFO: [Simtcl 6-17] Simulation restarted
INFO: [USF-XSim-61] Executing 'ELABORATE' step in 'd:/Pycharm_Project/fpga-flow/workspace/counter_8bit_enable_reset/counter_8bit_enable_reset.sim/sim_1/behav/xsim'
WARNING: [XSIM 43-4100] "d:/Pycharm_Project/fpga-flow/workspace/counter_8bit_enable_reset/counter_8bit_enable_reset.sim/sim_1/behav/xsim/glbl.v" Line 6. Module glbl has a timescale but at least one module in design doesn't have timescale.
INFO: [Common 17-206] Exiting Webtalk at Tue Jun 24 14:47:10 2025...
# add_files -fileset syntax_check {d:/Pycharm_Project/fpga-flow/workspace/counter_8bit_enable_reset/counter_8bit_enable_reset.srcs/sim_1/new/tb_counter_8bit_enable_reset.v}
# check_syntax -fileset syntax_check
CRITICAL WARNING: [HDL 9-3086] 'string' is an unknown type [d:/Pycharm_Project/fpga-flow/workspace/counter_8bit_enable_reset/counter_8bit_enable_reset.srcs/sim_1/new/tb_counter_8bit_enable_reset.v:67]
CRITICAL WARNING: [HDL 9-3881] system call 'sformatf' not allowed in this dialect. Use SystemVerilog mode [d:/Pycharm_Project/fpga-flow/workspace/counter_8bit_enable_reset/counter_8bit_enable_reset.srcs/sim_1/new/tb_counter_8bit_enable_reset.v:85]
CRITICAL WARNING: [HDL 9-3881] system call 'sformatf' not allowed in this dialect. Use SystemVerilog mode [d:/Pycharm_Project/fpga-flow/workspace/counter_8bit_enable_reset/counter_8bit_enable_reset.srcs/sim_1/new/tb_counter_8bit_enable_reset.v:99]
CRITICAL WARNING: [HDL 9-3881] system call 'sformatf' not allowed in this dialect. Use SystemVerilog mode [d:/Pycharm_Project/fpga-flow/workspace/counter_8bit_enable_reset/counter_8bit_enable_reset.srcs/sim_1/new/tb_counter_8bit_enable_reset.v:113]
# delete_fileset syntax_check
INFO: [Common 17-206] Exiting Vivado at Tue Jun 24 14:49:20 2025...
WARNING: [Vivado 12-1022] No filesets matching 'syntax_check'
INFO: [Vivado 12-4796] No errors or warning reported.
INFO: [Common 17-206] Exiting Vivado at Tue Jun 24 14:51:51 2025...
[PASS]                                                                                                                  Counting to max passed at time 955000: count = 57
[PASS]                                                                                                                  Counting to max passed at time 965000: count = 58
[PASS]                                                                                                                  Counting to max passed at time 975000: count = 59
[PASS]                                                                                                                  Counting to max passed at time 985000: count = 5a
[PASS]                                                                                                                  Counting to max passed at time 995000: count = 5b
INFO: [USF-XSim-96] XSim completed. Design snapshot 'tb_counter_8bit_enable_reset_behav' loaded.
INFO: [USF-XSim-97] XSim simulation ran for 1000ns
[PASS] Counting at cycle 244: Count=ff at time 2655000
[PASS] Counting at cycle 245: Count=00 at time 2665000
[PASS] Counting at cycle 246: Count=01 at time 2675000
[PASS] Counting at cycle 247: Count=02 at time 2685000
[PASS] Counting at cycle 248: Count=03 at time 2695000
[PASS] Counting at cycle 249: Count=04 at time 2705000
[PASS] Test 5: Count=00 at time 2725000
Error: [ERROR] Counting mismatch at cycle 0: Expected=01, Got=02 at time 2745000
    """

    err_result = get_error_info(std_message)
    print(err_result)

