# -*- coding: utf-8 -*-
# SPDX-License-Identifier: MIT

import os
import subprocess
import tempfile
from typing import Dict, Any, Optional
from langchain_core.tools import tool


@tool
def iverilog_compile_tool(verilog_code: str, module_name: str = None, workspace_path: str = None) -> Dict[str, Any]:
    """
    使用iverilog编译Verilog代码
    
    Args:
        verilog_code: Verilog代码内容
        module_name: 模块名称，如果不提供则从代码中自动提取
        workspace_path: 工作空间路径，如果不提供则使用默认路径
    
    Returns:
        编译结果字典，包含成功状态、输出信息等
    """
    try:
        # 如果没有提供模块名，尝试从代码中提取
        if module_name is None:
            import re
            module_match = re.search(r'module\s+(\w+)', verilog_code)
            if module_match:
                module_name = module_match.group(1)
            else:
                module_name = "top"  # 默认名称
        
        # 确定工作目录
        if workspace_path:
            work_dir = workspace_path
            os.makedirs(work_dir, exist_ok=True)
        else:
            work_dir = tempfile.mkdtemp()
        
        # 创建临时Verilog文件（添加时间戳避免冲突）
        import time
        timestamp = int(time.time())
        verilog_file = os.path.join(work_dir, f"{module_name}_{timestamp}.v")
        
        with open(verilog_file, 'w', encoding='utf-8') as f:
            f.write(verilog_code)
        
        # 编译命令
        output_file = os.path.join(work_dir, f"{module_name}_{timestamp}.vvp")
        cmd = ["iverilog", "-o", output_file, verilog_file]
        
        # 执行编译
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            cwd=work_dir,
            timeout=30
        )
        
        return {
            "success": result.returncode == 0,
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "verilog_file": verilog_file,
            "output_file": output_file if result.returncode == 0 else None,
            "work_dir": work_dir
        }
        
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "error": "编译超时",
            "timeout": True
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"编译过程中发生错误: {str(e)}"
        }


@tool
def iverilog_simulate_tool(vvp_file: str, testbench_code: str = None, simulation_time: str = "1000") -> Dict[str, Any]:
    """
    使用vvp运行iverilog编译后的仿真文件。
    
    Args:
        vvp_file: iverilog编译生成的.vvp文件路径
        testbench_code: 测试台代码（可选）
        simulation_time: 仿真时间，默认1000个时间单位
    
    Returns:
        仿真结果字典，包含success、output、error等信息
    """
    try:
        if not os.path.exists(vvp_file):
            return {
                "success": False,
                "error": f"仿真文件不存在: {vvp_file}"
            }
        
        work_dir = os.path.dirname(vvp_file)
        
        # 如果提供了测试台代码，先编译测试台
        if testbench_code:
            testbench_file = os.path.join(work_dir, "testbench.v")
            with open(testbench_file, 'w', encoding='utf-8') as f:
                f.write(testbench_code)
            
            # 重新编译包含测试台的代码
            module_file = vvp_file.replace('.vvp', '.v')
            new_vvp_file = os.path.join(work_dir, "testbench.vvp")
            compile_cmd = ["iverilog", "-o", new_vvp_file, module_file, testbench_file]
            
            compile_result = subprocess.run(
                compile_cmd,
                capture_output=True,
                text=True,
                cwd=work_dir,
                timeout=30
            )
            
            if compile_result.returncode != 0:
                return {
                    "success": False,
                    "error": f"测试台编译失败: {compile_result.stderr}",
                    "compile_stdout": compile_result.stdout,
                    "compile_stderr": compile_result.stderr
                }
            
            vvp_file = new_vvp_file
        
        # 运行仿真
        cmd = ["vvp", vvp_file]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=work_dir,
            timeout=60
        )
        
        return {
            "success": result.returncode == 0,
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "vvp_file": vvp_file,
            "work_dir": work_dir
        }
        
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "error": "仿真超时",
            "timeout": True
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"仿真过程中发生错误: {str(e)}"
        }


@tool
def iverilog_full_test_tool(verilog_code: str, testbench_code: str, module_name: str = None, workspace_path: str = None) -> Dict[str, Any]:
    """
    使用iverilog进行完整的编译和仿真测试
    
    Args:
        verilog_code: 主模块Verilog代码
        testbench_code: 测试台代码
        module_name: 模块名称，如果不提供则从代码中自动提取
        workspace_path: 工作空间路径
    
    Returns:
        测试结果字典
    """
    # 如果没有提供模块名，尝试从代码中提取
    if module_name is None:
        import re
        module_match = re.search(r'module\s+(\w+)', verilog_code)
        if module_match:
            module_name = module_match.group(1)
        else:
            module_name = "top"  # 默认名称
    
    # 首先编译主模块
    compile_result = iverilog_compile_tool(verilog_code, module_name, workspace_path)
    
    if not compile_result["success"]:
        return {
            "success": False,
            "stage": "compile",
            "compile_result": compile_result
        }
    
    # 然后运行仿真
    simulate_result = iverilog_simulate_tool(compile_result["output_file"], testbench_code)
    
    return {
        "success": simulate_result["success"],
        "stage": "simulate" if compile_result["success"] else "compile",
        "compile_result": compile_result,
        "simulate_result": simulate_result
    }