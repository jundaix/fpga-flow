# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT
import subprocess
import os
import re
from typing import Optional, List, Dict
 

def extract_verilog_code(text: str) -> Optional[str]:
    """
    从文本中提取Verilog/SystemVerilog代码块。
    
    Args:
        text: 包含Verilog代码的文本
        
    Returns:
        提取的Verilog代码，如果没有找到则返回None
    """
    # 尝试匹配代码块格式
    patterns = [
        # 标准markdown代码块
        r'```(?:verilog|systemverilog|sv)\s*\n(.*?)\n```',
        # 无语言标识的代码块，但包含module关键字
        r'```\s*\n(.*?module\s+.*?)\n```',
        # 直接的module定义（不在代码块中）
        r'(module\s+\w+.*?endmodule)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        if match:
            code = match.group(1).strip()
            # 验证是否包含module关键字
            if 'module' in code.lower():
                return code
    
    return None


def validate_verilog_syntax(file_paths, output_file=None):
    """
    使用iverilog验证Verilog文件语法正确性
    
    Args:
        file_paths: Verilog文件路径列表或单个文件路径
        output_file: 输出文件路径，如果为None则只验证不输出
        
    Returns:
        tuple: (bool, str) - (语法是否正确, 错误信息或成功信息)
    """    
    # 处理单个文件路径的情况
    if isinstance(file_paths, str):
        file_paths = [file_paths]
    
    # 检查文件是否存在
    for file_path in file_paths:
        if not file_path or not os.path.exists(file_path):
            return False, f"文件不存在: {file_path}"
    
    try:
        # 构建iverilog命令
        cmd = ["iverilog", "-g2012", "-Wall"]
        
        if output_file is None:
            # 验证模式：只验证不输出
            cmd.extend(["-t", "null"])
        else:
            # 输出模式：生成输出文件
            cmd.extend(["-o", output_file])
        
        # 添加所有输入文件
        cmd.extend(file_paths)
        
        # 执行命令
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
        )
        error_msg = result.stderr.strip() if result.stderr else "0 errors 0 warnings"
        # 如果返回码为0，说明语法正确
        if result.returncode == 0:
            if output_file is None:
                return True, f"语法验证通过 {result.stdout}{error_msg}"
            else:
                return True, f"编译成功\n{result.stdout}+{error_msg}\n输出文件: {output_file}"
        else:
            # 返回iverilog的具体错误信息
            return False, f"iverilog错误:\n{error_msg}"
        
    except subprocess.TimeoutExpired:
        return False, "iverilog验证超时"
    except FileNotFoundError:
        # 如果iverilog不可用，log请安装iverilog
        return False, "iverilog未找到，请确保已安装iverilog"
    except Exception as e:
        return False, f"验证过程出错: {str(e)}"


def validate_verilog_logic(output_file):
    """
    使用vvp指令验证Verilog逻辑正确性
    
    Args:
        output_file: 编译输出文件名
        
    Returns:
        tuple: (bool, str) - (逻辑验证是否通过, 仿真输出信息或错误信息)
    """    
    # 确保output_file是字符串类型
    output_file_str = str(output_file)
    
    # 检查编译输出文件是否存在
    if not os.path.exists(output_file_str):
        return False, f"编译输出文件不存在: {output_file_str}"
    try:     
        # 使用vvp运行仿真
        sim_cmd = ["vvp", output_file_str]
        
        # 使用Popen进行实时输出
        print("\n=== 开始仿真 ===")
        print(f"执行命令: {' '.join(sim_cmd)}")
        print("=== 仿真输出 ===")
        
        process = subprocess.Popen(
            sim_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        # 收集输出用于后续分析
        simulation_output = ""
        
        # 实时读取并显示输出
        while True:
            output = process.stdout.readline()
            if output == '' and process.poll() is not None:
                break
            if output:
                print(output)  # 实时显示
                simulation_output += output  # 收集用于分析
                import sys
                sys.stdout.flush()  # 强制刷新输出缓冲区
        
        # 等待进程完成
        return_code = process.poll()
        print("=== 仿真结束 ===")
        
        # 创建一个模拟的result对象来保持后续代码兼容
        class SimResult:
            def __init__(self, returncode, stdout, stderr=""):
                self.returncode = returncode
                self.stdout = stdout
                self.stderr = stderr
        
        sim_result = SimResult(return_code, simulation_output)
        
        # 清理编译生成的文件
        try:
            if os.path.exists(output_file_str):
                os.remove(output_file_str)
        except:
            pass  # 忽略清理错误
               
        # 如果返回码为0，说明语法正确
        print("仿真错误码为:",sim_result.returncode)
        if sim_result.returncode  == 0 and "ERROR" not in sim_result.stderr.upper() and "ERROR" not in sim_result.stdout.upper():
            return True, f"仿真通过 {sim_result.stdout}\n{sim_result.stderr}"
        else:
            # 返回iverilog的具体错误信息
            return False, f"仿真未通过:\n{sim_result.stdout}\n{sim_result.stderr}"        
        
    except subprocess.TimeoutExpired:
        return False, "仿真执行超时"
    except FileNotFoundError as e:
        if "vvp" in str(e):
            return False, "vvp未找到，请确保已安装iverilog工具链"
        else:
            return False, f"工具未找到: {str(e)}"
    except Exception as e:
        return False, f"逻辑验证过程出错: {str(e)}"


validate_verilog_logic(r"E:\biye_over\ai_fpga_4.0\simple-fpga-flow\workspace\counter_8bit_enable_reset\sim\sim_counter_8bit_enable_reset.out")