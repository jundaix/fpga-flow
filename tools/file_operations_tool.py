# -*- coding: utf-8 -*-
# SPDX-License-Identifier: MIT

import os
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from langchain_core.tools import tool


@tool
def write_file_tool(file_path: str, content: str, encoding: str = "utf-8") -> Dict[str, Any]:
    """
    将内容写入指定文件。
    
    Args:
        file_path: 文件路径
        content: 文件内容
        encoding: 文件编码，默认utf-8
    
    Returns:
        操作结果字典
    """
    try:
        # 确保目录存在
        file_path = Path(file_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 写入文件
        with open(file_path, 'w', encoding=encoding) as f:
            f.write(content)
        
        return {
            "success": True,
            "message": f"文件已成功写入: {file_path}",
            "file_path": str(file_path),
            "file_size": len(content),
            "encoding": encoding
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"写入文件失败: {str(e)}",
            "file_path": str(file_path)
        }


@tool
def read_file_tool(file_path: str, encoding: str = "utf-8") -> Dict[str, Any]:
    """
    读取指定文件的内容。
    
    Args:
        file_path: 文件路径
        encoding: 文件编码，默认utf-8
    
    Returns:
        读取结果字典
    """
    try:
        file_path = Path(file_path)
        
        if not file_path.exists():
            return {
                "success": False,
                "error": f"文件不存在: {file_path}"
            }
        
        with open(file_path, 'r', encoding=encoding) as f:
            content = f.read()
        
        return {
            "success": True,
            "content": content,
            "file_path": str(file_path),
            "file_size": len(content),
            "encoding": encoding
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"读取文件失败: {str(e)}",
            "file_path": str(file_path)
        }


@tool
def create_directory_tool(dir_path: str) -> Dict[str, Any]:
    """
    创建目录（包括父目录）。
    
    Args:
        dir_path: 目录路径
    
    Returns:
        操作结果字典
    """
    try:
        dir_path = Path(dir_path)
        dir_path.mkdir(parents=True, exist_ok=True)
        
        return {
            "success": True,
            "message": f"目录已创建: {dir_path}",
            "dir_path": str(dir_path)
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"创建目录失败: {str(e)}",
            "dir_path": str(dir_path)
        }


@tool
def list_files_tool(dir_path: str, pattern: str = "*", recursive: bool = False) -> Dict[str, Any]:
    """
    列出目录中的文件。
    
    Args:
        dir_path: 目录路径
        pattern: 文件匹配模式，默认"*"
        recursive: 是否递归搜索子目录
    
    Returns:
        文件列表结果字典
    """
    try:
        dir_path = Path(dir_path)
        
        if not dir_path.exists():
            return {
                "success": False,
                "error": f"目录不存在: {dir_path}"
            }
        
        if not dir_path.is_dir():
            return {
                "success": False,
                "error": f"路径不是目录: {dir_path}"
            }
        
        if recursive:
            files = list(dir_path.rglob(pattern))
        else:
            files = list(dir_path.glob(pattern))
        
        file_list = []
        for file in files:
            file_info = {
                "path": str(file),
                "name": file.name,
                "is_file": file.is_file(),
                "is_dir": file.is_dir(),
                "size": file.stat().st_size if file.is_file() else 0
            }
            file_list.append(file_info)
        
        return {
            "success": True,
            "files": file_list,
            "count": len(file_list),
            "dir_path": str(dir_path),
            "pattern": pattern,
            "recursive": recursive
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"列出文件失败: {str(e)}",
            "dir_path": str(dir_path)
        }


@tool
def save_verilog_project_tool(project_data: Dict[str, Any], workspace_path: str) -> Dict[str, Any]:
    """
    保存完整的Verilog项目到工作空间。
    
    Args:
        project_data: 项目数据字典，包含代码、测试台、报告等
        workspace_path: 工作空间路径
    
    Returns:
        保存结果字典
    """
    try:
        workspace = Path(workspace_path)
        workspace.mkdir(parents=True, exist_ok=True)
        
        saved_files = []
        
        # 创建目录结构
        src_dir = workspace / "src"
        testbench_dir = workspace / "testbench"
        reports_dir = workspace / "reports"
        simulation_dir = workspace / "simulation"
        
        for dir_path in [src_dir, testbench_dir, reports_dir, simulation_dir]:
            dir_path.mkdir(exist_ok=True)
        
        # 保存主模块代码
        if "verilog_code" in project_data:
            import time
            
            # 生成唯一文件名（添加时间戳避免覆盖）
            timestamp = int(time.time())
            verilog_file = src_dir / f"verilog_code_{timestamp}.v"
            with open(verilog_file, 'w', encoding='utf-8') as f:
                f.write(project_data["verilog_code"])
            saved_files.append(str(verilog_file))
        
        # 保存测试台代码
        if "testbench_code" in project_data:
            import time
            
            # 生成唯一文件名（添加时间戳避免覆盖）
            timestamp = int(time.time())
            testbench_file = testbench_dir / f"testbench_code_{timestamp}.v"
            with open(testbench_file, 'w', encoding='utf-8') as f:
                f.write(project_data["testbench_code"])
            saved_files.append(str(testbench_file))
        
        # 保存其他代码文件
        if "additional_files" in project_data:
            for filename, content in project_data["additional_files"].items():
                file_path = src_dir / filename
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                saved_files.append(str(file_path))
        
        # 保存开发计划
        if "development_plan" in project_data:
            plan_file = reports_dir / "development_plan.json"
            with open(plan_file, 'w', encoding='utf-8') as f:
                json.dump(project_data["development_plan"], f, ensure_ascii=False, indent=2)
            saved_files.append(str(plan_file))
        
        # 保存测试结果
        if "test_results" in project_data:
            test_file = reports_dir / "test_results.json"
            with open(test_file, 'w', encoding='utf-8') as f:
                json.dump(project_data["test_results"], f, ensure_ascii=False, indent=2)
            saved_files.append(str(test_file))
        
        # 保存调试报告
        if "debug_report" in project_data:
            debug_file = reports_dir / "debug_report.json"
            with open(debug_file, 'w', encoding='utf-8') as f:
                json.dump(project_data["debug_report"], f, ensure_ascii=False, indent=2)
            saved_files.append(str(debug_file))
        
        # 保存项目信息
        project_info = {
            "project_name": project_data.get("project_name", "unknown"),
            "description": project_data.get("description", ""),
            "created_files": saved_files,
            "workspace_path": str(workspace)
        }
        
        info_file = workspace / "project_info.json"
        with open(info_file, 'w', encoding='utf-8') as f:
            json.dump(project_info, f, ensure_ascii=False, indent=2)
        saved_files.append(str(info_file))
        
        return {
            "success": True,
            "message": f"项目已保存到: {workspace}",
            "workspace_path": str(workspace),
            "saved_files": saved_files,
            "file_count": len(saved_files)
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"保存项目失败: {str(e)}",
            "workspace_path": str(workspace_path)
        }


@tool
def copy_file_to_root_tool(source_file: str, target_name: str = None) -> Dict[str, Any]:
    """
    将文件复制到项目根目录。
    
    Args:
        source_file: 源文件路径
        target_name: 目标文件名，如果不提供则使用源文件名
    
    Returns:
        复制结果字典
    """
    try:
        source_path = Path(source_file)
        
        if not source_path.exists():
            return {
                "success": False,
                "error": f"源文件不存在: {source_file}"
            }
        
        # 获取项目根目录（假设是fpga-flow目录）
        current_dir = Path.cwd()
        if "fpga-flow" in str(current_dir):
            root_dir = current_dir
        else:
            # 尝试找到fpga-flow目录
            for parent in current_dir.parents:
                if parent.name == "fpga-flow":
                    root_dir = parent
                    break
            else:
                root_dir = current_dir
        
        # 确定目标文件名
        if target_name:
            target_path = root_dir / target_name
        else:
            target_path = root_dir / source_path.name
        
        # 复制文件
        import shutil
        shutil.copy2(source_path, target_path)
        
        return {
            "success": True,
            "message": f"文件已复制到根目录: {target_path}",
            "source_file": str(source_path),
            "target_file": str(target_path),
            "root_dir": str(root_dir)
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"复制文件失败: {str(e)}",
            "source_file": str(source_file)
        }