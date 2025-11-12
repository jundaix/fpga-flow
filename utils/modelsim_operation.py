""" 
    该代码旨在通过 tcl 指令驱动 ModelSim/Questa 进行仿真
"""

import os
import tempfile
import subprocess
from pathlib import Path
from typing import Tuple, Optional, List, Dict
import re

def output_filter(source_output: str) -> str:
    """
    从 ModelSim/Questa 的标准输出中筛选以下行（保持原始顺序）：
    1) 以 "# [单词]" 开头的行（如: # [INFO], # [PASS]）
    2) 以 "# ** 单词:" 开头的行（如: # ** Error:, # ** Note:）
    3) 以 "#    Time:"（# 后空白 + Time:）开头的行
    返回拼接后的字符串（用 '\n' 连接）
    """
    # 组合三类规则的正则（逐行匹配）
    pattern = re.compile(
        r"^(?:"
        r"#\s\[[A-Za-z]+\].*"        # 1) # [WORD]...
        r"|#\s\*\*\s[A-Za-z]+:.*"    # 2) # ** Word:...
        r"|#\s+Time:.*"              # 3) # <spaces>Time:...
        r")$",
        flags=re.MULTILINE
    )

    matches = [m.group(0) for m in pattern.finditer(source_output)]
    return "\n".join(matches)

def get_err_warn_info(source_output: str) -> str:
    """
    从 ModelSim/Questa 输出中提取最后一个形如:
        # Errors: X, Warnings: Y
    的行。
    如果没有匹配则返回空字符串。
    """
    pattern = re.compile(
        r"^#\s*Errors:\s*\d+\s*,\s*Warnings:\s*\d+\s*$",
        flags=re.MULTILINE | re.IGNORECASE
    )
    matches = pattern.findall(source_output)

    return matches[-1] if matches else ""

def run_modelsim_tcl_script_in_memory(
    tcl_script: str,
    vsim_path: str = r"D:\ModelSim\ModelSim\win64\vsim.exe",                            # vsim.exe 路径
    modelsim_ini: Optional[str] = r"D:\ModelSim\ModelSim_Vivado_lib_2020.2\modelsim.ini",   # 可选：指定 modelsim.ini 路径
    work_dir: Optional[str] = None,                                                      # 可选：设置工作目录（生成 work 库/日志的地方），一般就是.xpr所在位置
    timeout: int = 120,                                                                  # 可选：秒，超时终止
    extra_args: Optional[list] = None                                                    # 可选：追加给 vsim 的其它参数，比如 ["-wlf", "sim.wlf"]
) -> Tuple[str, str, int]:
    """
    用 ModelSim/Questa 在命令行执行内存中的 Tcl/DO 脚本（不打开 GUI）。
    返回 (stdout, stderr, returncode)。
    - returncode=0 通常表示成功（前提：脚本里用 onerror/ -onfinish exit 控制，0 表示没有错误为普遍的定义，其它返回码错误值可以根据实际情况自定义）
    """
    # 准备日志目录（可按需自定义）
    log_dir = (Path(__file__).resolve().parent.parent / "modelsim_log")
    log_dir.mkdir(parents=True, exist_ok=True)

    # 将 Tcl 内容写入临时文件
    with tempfile.NamedTemporaryFile(delete=False, mode="w", suffix=".tcl") as tmp_file:
        tmp_file.write(tcl_script)
        tcl_script_path = tmp_file.name

    # 组织命令
    cmd = [vsim_path, "-c"]  # -c: console/batch 模式
    if modelsim_ini:
        cmd += ["-modelsimini", modelsim_ini]
    if extra_args:
        cmd += list(extra_args)
    cmd += ["-do", tcl_script_path]  # 执行我们的 Tcl

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=work_dir or None,        # 在指定工作目录执行（例如你的工程根）
            creationflags=0x08000000 if os.name == "nt" else 0,  # Windows: CREATE_NO_WINDOW（可选）
        )
        stdout, stderr = proc.communicate(timeout=timeout)
        rc = proc.returncode
    except subprocess.TimeoutExpired:
        proc.kill()
        stdout, stderr = proc.communicate()
        rc = 124  # 约定 124 代表外部调用超时
    finally:
        # 清理临时 Tcl 文件
        try:
            os.remove(tcl_script_path)
        except OSError:
            pass

    return stdout.decode(errors="ignore"), stderr.decode(errors="ignore"), rc


def validate_verilog_syntax_modelsim(rtl_files: Optional[List[Path | str]] = None):
    """
    验证 Verilog 文件是否通过 ModelSim 语法检查。
    输入:
        rtl_files : Verilog 文件路径列表
    输出:
        (is_valid: bool, message: str)
    """
    if rtl_files is None or len(rtl_files) == 0:
        return False, "The rtl_files list is empty."

    # 保证都是绝对路径
    rtl_files = [Path(f).resolve() for f in rtl_files]

    # 验证文件是否存在
    non_exist_files = []
    for f in rtl_files:
        if not f.exists():
            non_exist_files.append(f)
    if non_exist_files:
        return False, f"The following files do not exist: {non_exist_files}"

    rtl_files_str = ' '.join([f'"{str(f).replace("\\", "/")}"' for f in rtl_files])

    tcl_top = """
    onerror {quit -code 2}
    transcript file compile.log
    if { [file exists work] == 0 } { vlib work }
    vmap work work
    """

    tcl_files = f"""
    set RTL_FILES [list {rtl_files_str}]
    """
    
    tcl_complete = """
    vlog -work work -sv -lint +acc {*}$RTL_FILES
    quit -code 0
    """

    tcl_command = tcl_top + tcl_files + tcl_complete
    stdout, stderr, return_code = run_modelsim_tcl_script_in_memory(tcl_command)

    if return_code != 0:
        std_filted = output_filter(stdout)
        # return False, f"The current Verilog code has syntax issues. Details: {std_filted}"
        return False, f"当前的Verilog代码存在语法错误: {std_filted}"
    else:
        return True, "ModelSim syntax check passed."


def collect_ip_files(project_dir: Optional[Path] = None, project_name: Optional[str] = None, ip_names: Optional[List[str]] = None) -> Dict[str, List[str]]:
    """
    采集 Vivado 工程中 IP 的仿真相关文件。
    输入:
        project_dir : 工程根目录 (包含 <project_name>.xpr 的目录)
        project_name: 工程名 (与 .xpr 文件同名, 用于定位 *.gen / *.ip_user_files 等)
        ip_names    : 需要采集的 IP 目录名列表 (如 ["fifo_test", ...])
    输出:
        {
          "behav_v" : [ ... ],   # 行为模型 (simulation 下的 *.v/*.sv)
          "rfs_v"   : [ ... ],   # RFS / core (hdl 下的 *.v/*.sv)
          "wrapper_v": [ ... ],  # sim 下的 *.v/*.sv (通常是 wrapper/顶层封装)
          "includer": [ ... ],   # 头文件目录 (含有 .vh/.svh 的目录, 用于 +incdir)
        }
    规则:
      1) 优先保留 <project_name>.gen 下的文件；若在 ip_user_files 中出现同名(同 basename)文件则跳过。
      2) 仅处理 Verilog/SystemVerilog；VHDL 可按需扩展。
    """
    # 工程目录默认当前路径
    if project_dir is None:
        project_dir = Path.cwd()
    else:
        project_dir = Path(project_dir)

    # Vivado 工程派生目录
    gen_root = project_dir / f"{project_name}.gen" / "sources_1" / "ip"
    ipstatic_root = project_dir / f"{project_name}.ip_user_files" / "ipstatic"

    # 四类输出
    behav_v: List[str]   = []  # simulation 下 *.v/*.sv
    rfs_v: List[str]     = []  # hdl 下 *.v/*.sv
    wrapper_v: List[str] = []  # sim 下 *.v/*.sv
    includer_dirs_set    = set()  # 目录集合去重

    # 已收集的 basename (用于 “优先 .gen” 去重)
    seen_basenames = set()

    def norm(p: Path) -> str:
        # 路径统一转成绝对路径，并将 Windows 的 \ 替换成 /
        return str(p.resolve()).replace("\\", "/")

    def add_verilog_files_from_dir(dir_path: Path, kind: str):
        """将 dir_path 中的 *.v/*.sv 归类到 kind in {'behav','rfs','wrapper'}"""
        nonlocal behav_v, rfs_v, wrapper_v, seen_basenames
        if not dir_path.is_dir():
            return

        # 如果该目录下有 .vh / .svh 文件，则将目录加入 includer 集合（用于 +incdir）
        # glob 返回一个生成器（可以遍历所有匹配的 Path 对象）,此处是为了找到目录下所有的.vh，.svh，.v，.sv文件
        header_hit = False
        for pat in ("*.vh", "*.svh"):
            if any(dir_path.glob(pat)):
                header_hit = True
                break
        if header_hit:
            includer_dirs_set.add(norm(dir_path))

        # 源文件收集
        files = []
        for pat in ("*.v", "*.sv"):
            files.extend(dir_path.glob(pat))
        for f in files:
            b = f.name  # basename
            if b in seen_basenames:         # 如果之前收集过同名文件，则跳过
                continue

            if kind == "behav":
                behav_v.append(norm(f))
            elif kind == "rfs":
                rfs_v.append(norm(f))
            elif kind == "wrapper":
                wrapper_v.append(norm(f))

            seen_basenames.add(b)

    # 1) 先扫 .gen (高优先级)
    for ip in ip_names:
        add_verilog_files_from_dir(gen_root / ip / "simulation", kind="behav")
        add_verilog_files_from_dir(gen_root / ip / "hdl",        kind="rfs")
        add_verilog_files_from_dir(gen_root / ip / "sim",        kind="wrapper")

    # 2) 再扫 ip_user_files/ipstatic (低优先级; 仅添加未在 .gen 出现过的同名文件)
    #    注意：ip_user_files 下没有按 ip_name 再分子目录的惯例，直接在 hdl/simulation 下找
    add_verilog_files_from_dir(ipstatic_root / "simulation", kind="behav")
    add_verilog_files_from_dir(ipstatic_root / "hdl",        kind="rfs")

    return {
        "behav_v": behav_v,
        "rfs_v": rfs_v,
        "wrapper_v": wrapper_v,
        "includer": sorted(includer_dirs_set),
    }


def validate_verilog_logic_modelsim(project_dir: Optional[Path | str] = None,
                                     project_name: Optional[str] = None,
                                     ip_names: Optional[List[str]] = None,
                                     rtl_files: Optional[List[Path | str]] = None,
                                     tb_file: Optional[Path | str] = None,
                                     tb_model: Optional[str] = None,
                                     ) -> Tuple[bool, str]:
    """
    验证 Verilog 逻辑是否能在 Modelsim 中仿真通过。
    输入:
        project_dir : 工程根目录 (包含 <project_name>.xpr 的目录)
        project_name: 工程名 (与 .xpr 文件同名, 用于定位 *.gen / *.ip_user_files 等)
        ip_names    : 需要采集的 IP 目录名列表 (如 ["fifo_test", ...])
        rtl_files   : 需要仿真的 RTL 文件列表
    输出:
        是否能在 Modelsim 中仿真通过 (bool)
    注意：
        1）输入的路径请采用绝对路径
        2）project_dir, project_name, rtl_files, tb_file, tb_model 必填
    """
    # 检查是否存在空的项
    if any([project_dir is None, project_name is None, rtl_files is None, tb_file is None, tb_model is None]):
        non_para = []
        for p in [project_dir, project_name, rtl_files, tb_file, tb_model]:
            if p is None:
                non_para.append(p)
        return False, f"One or more input parameters are None: {non_para}"

    # 保证路径为绝对路径
    if isinstance(project_dir, str):
        project_dir = Path(project_dir)
    if isinstance(project_dir, Path):
        project_dir = project_dir.resolve()
    
    # 保证所有路径都为绝对路径
    rtl_files = [Path(f).resolve() for f in rtl_files]
    tb_file = Path(tb_file).resolve()

    # 验证文件是否存在
    non_exist_files = []
    for f in rtl_files + [tb_file]:
        if not f.exists():
            non_exist_files.append(f)
    if non_exist_files:
        return False, f"The following files do not exist: {non_exist_files}"

    # 提取 IP 相关文件
    if ip_names:
        ip_files_dict = collect_ip_files(project_dir, project_name, ip_names)
        ip_behav = ip_files_dict.get("behav_v", [])
        ip_rfs = ip_files_dict.get("rfs_v", [])
        ip_wrapper = ip_files_dict.get("wrapper_v", [])
        ip_includer = ip_files_dict.get("includer", [])
    else:
        ip_behav = []
        ip_rfs = []
        ip_wrapper = []
        ip_includer = []

    ''' 构造 tcl 指令（为了避免与 tcl 指令中的双引号冲突，此处 tcl 指令字符串采用单引号） '''
    # 顶层指令
    tcl_top = '''
    onerror {quit -code 3}
    transcript file sim_tb.log
    '''
    # 工程文件相关
    rtl_files_str = ' '.join([f'"{str(f).replace("\\", "/")}"' for f in rtl_files])
    ip_behav_str = ' '.join([f'"{str(f).replace("\\", "/")}"' for f in ip_behav])
    ip_rfs_str = ' '.join([f'"{str(f).replace("\\", "/")}"' for f in ip_rfs])
    ip_wrapper_str = ' '.join([f'"{str(f).replace("\\", "/")}"' for f in ip_wrapper])
    ip_includer_str = ' '.join([f'"{str(f).replace("\\", "/")}"' for f in ip_includer])
    tb_file_str = f'{str(tb_file).replace("\\", "/")}'
    proj_dir_str = f'{str(project_dir).replace("\\", "/")}'

    tcl_files = f'''
    set PROJ "{proj_dir_str}"
    set PROJ_NAME "{project_name}"

    set RTL_FILES [list {rtl_files_str}]
    set TB_FILE "{tb_file_str}"
    set TOP_TB "{tb_model}"

    set IP_WRAPPER_V [list {ip_wrapper_str}]
    set IP_BEHAV_V [list {ip_behav_str}]
    set IP_CORE_RFS_V [list {ip_rfs_str}]
    set IP_INCDIRS [list {ip_includer_str}]

    set XILINX_VIVADO "D:/Vivado/Xilinx.2020.2/Vivado/2020.2"
    '''

    tcl_set_glbl = '''
    if {![info exists XILINX_VIVADO]} {
        puts "NOTE: XILINX_VIVADO not set, will try project glbl.v"
    }
    set GLBL_VIVADO "$XILINX_VIVADO/data/verilog/src/glbl.v"
    set GLBL_PROJ   "$PROJ/$PROJ_NAME.ip_user_files/sim_scripts/fifo_test/modelsim/glbl.v"
    if {[file exists $GLBL_VIVADO]} {
        set GLBL_FILE $GLBL_VIVADO
    } else {
        set GLBL_FILE $GLBL_PROJ
    }
    '''

    # 建立库与映射
    tcl_xil = '''
    if {![file exists work]}           { vlib work }
    if {![file exists xil_defaultlib]} { vlib xil_defaultlib }
    vmap work work
    vmap xil_defaultlib xil_defaultlib
    '''

    # 收集 include 目录，生成 +incdir 选项
    tcl_incdir = '''
    set INCOPTS_LIST {}
    foreach d $IP_INCDIRS {
        lappend INCOPTS_LIST "+incdir+$d"
    }
    '''

    # 编译程序
    tcl_complete = '''
    vlog -work xil_defaultlib +acc "$GLBL_FILE"

    if {[llength $IP_BEHAV_V]} {
    vlog -work xil_defaultlib +acc {*}$INCOPTS_LIST {*}$IP_BEHAV_V
    }
    if {[llength $IP_CORE_RFS_V]} {
        vlog -work xil_defaultlib +acc {*}$INCOPTS_LIST {*}$IP_CORE_RFS_V
    }
    if {[llength $IP_WRAPPER_V]} {
        vlog -work xil_defaultlib +acc {*}$INCOPTS_LIST {*}$IP_WRAPPER_V
    }

    if {[llength $RTL_FILES]} {
        vlog -work xil_defaultlib -sv +acc {*}$INCOPTS_LIST {*}$RTL_FILES
    }
    vlog -work work -sv +acc {*}$INCOPTS_LIST "$TB_FILE"
    '''

    # 启动仿真并退出
    tcl_sim = '''
    vsim -c -t ps -onfinish exit \
        -L xil_defaultlib -L xpm -L unisims_ver -L unimacro_ver -L secureip \
        work.$TOP_TB xil_defaultlib.glbl

    run 500 ms
    quit -code 0
    '''

    ''' 组装 tcl 指令 '''
    tcl_common = tcl_top + tcl_files + tcl_set_glbl + tcl_xil + tcl_incdir + tcl_complete + tcl_sim
    # with open("tcl_common.tcl", "w") as f:
    #     f.write(tcl_common)

    # 执行指令
    std_mes, err_mes, return_code = run_modelsim_tcl_script_in_memory(tcl_common, work_dir=str(project_dir.parent))

    # print(f"标准输出:\n{std_mes}")
    # print(f"错误输出:\n{err_mes}")
    # print(f"返回码: {return_code}")

    # print("*" * 100)
    # print(f"过滤后的输出结果:\n{output_filter(std_mes)}")
    # print(f"错误警告信息统计:\n{get_err_warn_info(std_mes)}")

    # 过滤输出结果以及错误信息统计
    filtered_mes = output_filter(std_mes)
    err_warn_info = get_err_warn_info(std_mes)
    
    ''' 根据输出结果解析仿真输出结果 '''
    # 如果返回码不为 0，说明当前程序或是系统出现错误
    if return_code != 0:
        return False, f"Some error occurred during simulation using ModelSim. Error message:\n{filtered_mes}"
    else:
        if "Errors: 0" not in err_warn_info:
            return False, f"The Verilog code passed syntax checking (compiled successfully),but functional simulation issues were encountered.Simulation results:\n{filtered_mes}"
        else:
            return True, f"Simulation completed successfully."
    
