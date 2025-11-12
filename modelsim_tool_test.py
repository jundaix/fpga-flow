from utils import run_modelsim_tcl_script_in_memory, output_filter, get_err_warn_info, collect_ip_files, validate_verilog_logic_modelsim, validate_verilog_syntax_modelsim
from pathlib import Path

work_space = Path(__file__).parent / "workspace"

# 执行语法检查（针对源码）
compile_tcl = r"""
onerror {quit -code 2}
transcript file compile.log
if { [file exists work] == 0 } { vlib work }
vmap work work
set SRC_ROOT "D:/Vivado_Project/Base_test/Base_test/Base_test.srcs"
set RTL_FILES [list "$SRC_ROOT/sources_1/new/counter_8bit_1.v"]
vlog -work work -sv -lint +acc {*}$RTL_FILES
quit -code 0
"""

# 执行仿真
sim_tcl = r"""
onerror {quit -code 3}
transcript file sim.log
if { [file exists work] == 0 } { vlib work }
vmap work work
set SRC_ROOT "D:/Vivado_Project/Base_test/Base_test/Base_test.srcs"
set RTL_FILE [list "$SRC_ROOT/sources_1/new/counter_8bit_1.v" "$SRC_ROOT/sources_1/new/counter_8bit.v"]
set TB_FILE  "$SRC_ROOT/sim_1/new/tb_counter_8bit_1.v"
set TOP_TB   "tb_counter_8bit_1"
vlog -work work -sv +acc {*}$RTL_FILE "$TB_FILE"
vsim -c -t ps -onfinish exit work.$TOP_TB
run 100 ms
quit -code 0
"""

# 执行包含 IP 核的仿真
sim_tcl_ip = r"""
onerror {quit -code 3}
transcript file sim_fifo_tb.log

# === 1) 工程根（把这行改成你的实际绝对路径：就是包含 Base_test.srcs 的目录）===
set PROJ "D:/Vivado_Project/Base_test"   ;# ←← 修改为你的“Base_test”路径

# === 2) 文件路径 ===
# 设计与 TB
set RTL_FILES [list \
    "$PROJ/Base_test/Base_test.srcs/sources_1/new/fifo_demo_top.v" \
]
set TB_FILE   "$PROJ/Base_test/Base_test.srcs/sim_1/new/tb_fifo_demo_top.v"
set TOP_TB    "tb_fifo_demo_top"

# Vivado FIFO IP 仿真文件（行为模型优先）
set IP_WRAPPER_V     "$PROJ/Base_test/Base_test.gen/sources_1/ip/fifo_test/sim/fifo_test.v"
set IP_BEHAV_V       "$PROJ/Base_test/Base_test.gen/sources_1/ip/fifo_test/simulation/fifo_generator_vlog_beh.v"
set IP_CORE_RFS_V    "$PROJ/Base_test/Base_test.gen/sources_1/ip/fifo_test/hdl/fifo_generator_v13_2_rfs.v"

# 设置 Vivado 安装目录
set XILINX_VIVADO     "D:/Vivado/Xilinx.2020.2/Vivado/2020.2"

# glbl.v：优先从 Vivado 安装目录拿；否则回退到工程里的 modelsim/glbl.v
if {![info exists XILINX_VIVADO]} {
    puts "NOTE: XILINX_VIVADO not set, will try project glbl.v"
}
set GLBL_VIVADO "$XILINX_VIVADO/data/verilog/src/glbl.v"
set GLBL_PROJ   "$PROJ/Base_test/Base_test.ip_user_files/sim_scripts/fifo_test/modelsim/glbl.v"
if {[info exists XILINX_VIVADO] && [file exists $GLBL_VIVADO]} {
    set GLBL_FILE $GLBL_VIVADO
} else {
    set GLBL_FILE $GLBL_PROJ
}

# === 3) 建库与映射（xil_defaultlib + work）===
if {![file exists work]}           { vlib work }
if {![file exists xil_defaultlib]} { vlib xil_defaultlib }
vmap work work
vmap xil_defaultlib xil_defaultlib

# 提示：xpm/unisims_ver/unimacro_ver/secureip 等库的 vmap 通常在 modelsim.ini 里配好了；
# 运行 vsim 时记得用 -modelsimini 指向那份 Vivado 预编译库的 modelsim.ini。

# === 5) 编译顺序 ===
# 5.1 glbl.v（到 xil_defaultlib）
vlog -work xil_defaultlib +acc "$GLBL_FILE"

# 5.2 IP 仿真源（到 xil_defaultlib）
#     先行为模型，再 rfs，再 wrapper，避免依赖次序问题
vlog -work xil_defaultlib +acc "$IP_BEHAV_V"
vlog -work xil_defaultlib +acc "$IP_CORE_RFS_V"
vlog -work xil_defaultlib +acc "$IP_WRAPPER_V"

# 5.3 你的 RTL 与 TB
vlog -work xil_defaultlib -sv +acc {*}$RTL_FILES
vlog -work work          -sv +acc "$TB_FILE"

# === 6) 启动仿真 ===
# -L：把 Vivado 的库都带上（名字要与 modelsim.ini 的映射一致）
# 顶层加载：你的 testbench + glbl
vsim -c -t ps -onfinish exit \
    -L xil_defaultlib -L xpm -L unisims_ver -L unimacro_ver -L secureip \
    work.$TOP_TB xil_defaultlib.glbl

run 100 ms
quit -code 0
"""

def test_main():
    out, err, rc = run_modelsim_tcl_script_in_memory(sim_tcl, work_dir=r"D:\Vivado_Project\Base_test")
    out_filtered = output_filter(out)
    err_warn_info = get_err_warn_info(out)
    print(f"返回码：\n{rc}")
    print(f"系统错误输出：\n{err}")
    print(f"运行输出结果：\n{out}")
    print(f"筛选后的运行输出结果：\n{out_filtered}")
    print(f"错误警告信息：\n{err_warn_info}")

def test_collect_ip_files():
    test_workspace = "D:/Vivado_Project/Base_test/Base_test"
    ip_files = collect_ip_files(Path(test_workspace), "Base_test", ["fifo_test"])

    for k, v in ip_files.items():
        print(f"{k}: {v}")

def test_tcl_sim():
    result, result_mes = validate_verilog_logic_modelsim(project_dir=r"D:/Vivado_Project/Base_test/Base_test",
                                    project_name="Base_test",
                                    ip_names=["fifo_test"],
                                    rtl_files=[r"D:/Vivado_Project/Base_test/Base_test/Base_test.srcs/sources_1/new/counter_8bit_1.v"],
                                    tb_file=r"D:/Vivado_Project/Base_test/Base_test/Base_test.srcs/sim_1/new/tb_counter_8bit_1.v",
                                    tb_model="tb_counter_8bit_1")

    print(f"运行结果：\n{result}")
    print(f"运行结果信息：\n{result_mes}")

def test_syntax():
    result, result_mes = validate_verilog_syntax_modelsim(rtl_files=[r"D:/Vivado_Project/Base_test/Base_test/Base_test.srcs/sources_1/new/counter_8bit_1.v"])
    print(f"语法检查结果：\n{result}")
    print(f"语法检查信息：\n{result_mes}")



if __name__ == "__main__":
    # test_collect_ip_files()
    test_main()
    # test_tcl_sim()
    # test_syntax()

    print("测试完成")
