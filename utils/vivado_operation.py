import subprocess
import tempfile
import os
from typing import List
import re
from pathlib import Path


def get_std_information(std_message: str):
    pattern = (
        r'^(?:'
          # 以大写单词+冒号或[大写单词]开头
        r'[A-Z]+(?: [A-Z]+)*:|\[[A-Z]+(?: [A-Z]+)*\]'
        r'|'
          # 以“error:”或“critical warning:”开头，不区分大小写
        r'(?:(?i:error:|critical warning:))'
        r').*'
    )
    matches = re.findall(pattern, std_message, flags=re.MULTILINE)

    std_info = ""

    for line in matches:
        std_info = std_info + line + "\n"
    
    return std_info

def run_vivado_tcl_script_in_memory(tcl_script):
    """
    使用 Vivado 运行内存中的 TCL 脚本。
    Args:
        tcl_script (str): 要执行的 TCL 脚本内容。
    Returns:
        tuple: (stdout, stderr) - 包含标准输出和标准错误的元组。
    """
    vivado_path = r"D:\Vivado\Xilinx\Vivado\2018.3\bin\vivado.bat"          # 设置自身vivado.bat的位置
    log_dir = (Path(__file__).resolve().parent.parent).joinpath("vivado_log")

    # 创建临时文件
    with tempfile.NamedTemporaryFile(delete=False, mode="w", suffix=".tcl") as tmp_file:
        # 写入 TCL 脚本
        tmp_file.write(tcl_script)
        tcl_script_path = tmp_file.name
    
    # 确保日志目录存在
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # 定义日志文件的路径
    log_file = os.path.join(log_dir, "vivado.log")
    jou_file = os.path.join(log_dir, "vivado.jou")


    # 通过 -source 参数传递 TCL 脚本文件给 Vivado
    process = subprocess.Popen(
        [vivado_path, "-mode", "batch", "-source", tcl_script_path, 
         "-log", log_file, "-journal", jou_file],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    # 捕获输出和错误
    stdout, stderr = process.communicate()

    # 删除临时文件
    os.remove(tcl_script_path)

    return stdout.decode(), stderr.decode()

def create_project(project_name:str, workspace_path:str, part="xc7z020clg484-1") -> tuple[bool, str]:
    """
    使用 Vivado 创建一个新的项目。
    Args:
        project_name (str): 项目名称。  
        workspace_path (str): 工作区路径。
        part (str): FPGA 部分。
    """
    # 定义TCL脚本模板
    # 创建一个空的Vivado项目
    workspace_path = os.path.normpath(workspace_path)
    project_path = os.path.normpath(os.path.join(workspace_path, project_name))
    project_file = os.path.join(project_path, f"{project_name}.xpr")
    
    # 检查 .xpr 文件是否已存在
    if os.path.exists(project_file):
        print("项目文件已存在")
        return  True, f"The project '{project_name}' already exists. Skipping creation step."

    # Ensure workspace directory exists
    os.makedirs(workspace_path, exist_ok=True)

    # TCL script template
    tcl_script = f"""create_project {project_name} {project_path.replace('\\', '/')} -part {part}"""
    # 执行TCL脚本
    stdout_source, stderr_source = run_vivado_tcl_script_in_memory(tcl_script)

    # 保留输出中的有效信息
    stdout = get_std_information(stdout_source)
    stderr = get_std_information(stderr_source)

    if stderr_source == "":
        return True, f"The project '{project_name}' was created successfully.\nExecution output:\n{stdout}\n{stderr}"
    else:
        return False, f"Failed to create project '{project_name}'.\nExecution output:\n{stdout}{stderr}"

def add_files_to_project(
    project_name: str,
    workspace_path: str,
    source_files: List[str] = []
) -> tuple[bool, str]:
    """
    将源文件添加到 Vivado 项目中。
    Args:
        project_name (str): Vivado 项目名称。
        workspace_path (str): 工作区路径。
        source_files (List[str]): 源文件路径列表。
    """
    # Normalize and validate paths
    workspace_path = os.path.normpath(workspace_path)
    project_path = os.path.normpath(os.path.join(workspace_path, project_name))
    project_file = os.path.join(project_path, f"{project_name}.xpr")
    
    if not os.path.exists(project_file):
        return False, f"Project {project_name} not found at {project_file}"
    
    # Generate TCL commands for files
    def format_files(file_list: List[str]) -> str:
        return "\n    ".join([f"add_files {{{os.path.normpath(f).replace('\\', '/')}}}" 
                            for f in file_list])
    
    tcl_script = f"""
    open_project {{{project_file.replace('\\', '/')}}}
    {format_files(source_files)}
    update_compile_order -fileset sources_1
    """
    
    stdout_source, stderr_source = run_vivado_tcl_script_in_memory(tcl_script)
    stdout = get_std_information(stdout_source)
    stderr = get_std_information(stderr_source)
    
    if stderr == "":
        return True, f"Added {len(source_files)} sources to {project_name}"
    else:
        return False, f"Failed to add {len(source_files)} sources to {project_name}.\nExecution output:\n{stdout}{stderr}"

def add_sim_files_to_project(
    project_name: str,
    workspace_path: str,
    source_files: List[str] = []
) -> tuple[bool, str]:
    # Normalize and validate paths
    workspace_path = os.path.normpath(workspace_path)
    project_path = os.path.normpath(os.path.join(workspace_path, project_name))
    project_file = os.path.join(project_path, f"{project_name}.xpr")

    if not os.path.exists(project_file):
        return False, f"Project {project_name} not found at {project_file}"

    # Generate TCL commands for files
    def format_files(file_list: List[str]) -> str:
        return "\n    ".join([f"add_files -fileset sim_1 {{{os.path.normpath(f).replace('\\', '/')}}}" 
                            for f in file_list])
    
    tcl_script = f"""
    open_project {{{project_file.replace('\\', '/')}}}
    set_property SOURCE_SET sources_1 [get_filesets sim_1]
    {format_files(source_files)}
    update_compile_order -fileset sim_1
    """

    stdout_source, stderr_source = run_vivado_tcl_script_in_memory(tcl_script)
    stdout = get_std_information(stdout_source)
    stderr = get_std_information(stderr_source)

    if stderr == "":
        return True, f"Added {len(source_files)} sim files to {project_name}"
    else:
        return False, f"Failed to add {len(source_files)} sim files to {project_name}.\nExecution output:\n{stdout}{stderr}"

# def set_top_sim_module(
#     project_name: str,
#     workspace_path: str,
#     top_module: str
#     ) -> tuple[bool, str]:
#     """
#     设置 Vivado 项目的顶层模块。
#     Args:
#         project_name (str): Vivado 项目名称。
#         workspace_path (str): 工作区路径。
#         top_module (str): 顶层模块名称。
#     Returns:
#         tuple: (bool, str) - (设置是否成功, 设置结果信息)
#     """
#     # Normalize and validate paths
#     workspace_path = os.path.normpath(workspace_path)
#     project_path = os.path.normpath(os.path.join(workspace_path, project_name))
#     project_file = os.path.join(project_path, f"{project_name}.xpr")

#     if not os.path.exists(project_file):
#         return False, f"Project {project_name} not found at {project_file}"
    
#     top_file_name = Path(top_module).stem

#     tcl_script = f"""
#     open_project {{{project_file.replace('\\', '/')}}}
#     set_property top {top_file_name} [get_filesets sim_1]
#     set_property top_lib xil_defaultlib [get_filesets sim_1]
#     update_compile_order -fileset sim_1
#     """

#     stdout, stderr_source = run_vivado_tcl_script_in_memory(tcl_script)
#     stderr = get_std_information(stderr_source)

#     if stderr == "":
#         return True, f"Set top module {top_file_name} for project {project_name} successfully."
#     else:
#         return False, f"Failed to set top module {top_file_name} for project {project_name}.\nError: {stderr}"

def validate_verilog_syntax_vivado(    
    project_name: str,
    workspace_path: str,
    checked_files: List[str] = []
    ) -> tuple[bool, str]:
    """
    使用 Vivado 验证 Verilog 文件的语法正确性。
    Args:
        project_name (str): Vivado 项目名称。
        workspace_path (str): 工作区路径。
        checked_files (List[str]): 要验证的源文件路径列表。
    Returns:
        tuple: (bool, str) - (验证是否通过, 验证结果信息)
    """
    # Normalize and validate paths
    workspace_path = os.path.normpath(workspace_path)
    project_path = os.path.normpath(os.path.join(workspace_path, project_name))
    project_file = os.path.join(project_path, f"{project_name}.xpr")

    if not os.path.exists(project_file):
        return False, f"Project {project_name} not found at {project_file}"
    
    def format_files(file_list: List[str]) -> str:
        return "\n    ".join([f"add_files -fileset syntax_check {{{os.path.normpath(f).replace('\\', '/')}}}" 
                            for f in file_list])

    tcl_open_project = f"open_project {{{project_file.replace('\\', '/')}}}"
    tcl_delete_fileset = """
    if { [llength [get_filesets syntax_check]] } {
    delete_fileset syntax_check
    }
    """
    tcl_check = f"""
    create_fileset syntax_check
    {format_files(checked_files)}
    check_syntax -fileset syntax_check
    delete_fileset syntax_check
    """

    tcl_script = tcl_open_project + tcl_delete_fileset + tcl_check

    try:
        stdout_source, stderr_source = run_vivado_tcl_script_in_memory(tcl_script)

        stdout = get_std_information(stdout_source)
        stderr = get_std_information(stderr_source)

        if "No errors or warning reported." in stdout:
            return True, f"Syntax check passed!\n{stdout}\n{stderr}"
        else:
            return False, f"Syntax check failed!\n{stdout}\n{stderr}"
    except Exception as e:
        return False, f"An error occurred during syntax checking with Vivado:\n{e}"

def contains_error(message: str) -> bool:
    return bool(re.search(r'\berror\b', message, flags=re.IGNORECASE))

def validate_verilog_logic_vivado(
    project_name: str,
    workspace_path: str,
    test_module: str
) -> tuple[bool, str]:
    """
    使用 Vivado 验证 Verilog 文件的逻辑正确性。
    Args:
        project_name (str): Vivado 项目名称。
        workspace_path (str): 工作区路径。
        test_module (str): 顶层模块名称。
    Returns:
        tuple: (bool, str) - (验证是否通过, 验证结果信息)
    """
    # Normalize and validate paths
    workspace_path = os.path.normpath(workspace_path)
    project_path = os.path.normpath(os.path.join(workspace_path, project_name))
    project_file = os.path.join(project_path, f"{project_name}.xpr")

    if not os.path.exists(project_file):
        return False, f"Project {project_name} not found at {project_file}"

    test_file_name = Path(test_module).stem

    # 要求最大仿真时间为1s的指令
    set_sim_time = "set_property -name {xsim.simulate.runtime} -value {1s} -objects [get_filesets sim_1]"
    
    tcl_script = f"""
    open_project {{{project_file.replace('\\', '/')}}}
    set_property top {test_file_name} [get_filesets sim_1]
    set_property top_lib xil_defaultlib [get_filesets sim_1]
    update_compile_order -fileset sim_1
    {set_sim_time}
    launch_simulation
    run_all
    close_sim
    """

    stdout_source, stderr_source = run_vivado_tcl_script_in_memory(tcl_script)

    stdout = get_std_information(stdout_source)
    stderr = get_std_information(stderr_source)

    if stderr == "" and not contains_error(stdout):
        return True, f"Simulation passed:\n{stdout}\n{stderr}"
    else:
        return False, f"Simulation failed:\n{stdout}\nError message:\n{stderr}"

if __name__ == "__main__":
    # validate, message = validate_verilog_logic_vivado("counter_8bit_enable_async_reset", "D:/Pycharm_Project/fpga-flow/workspace", "tb_counter_8bit_enable_async_reset")
    
    # if validate:
    #     print(f"验证正确：{message}")
    # else:
    #     print(f"验证出错：{message}")

    print("测试结束")