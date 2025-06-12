#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
启动Streamlit FPGA工作流应用

这个脚本用于启动基于Streamlit的FPGA开发工作流Web界面。
"""

import os
import sys
import subprocess
from pathlib import Path

def main():
    """启动Streamlit应用"""
    # 获取当前脚本所在目录
    current_dir = Path(__file__).parent
    streamlit_app = current_dir / "streamlit_workflow.py"
    
    # 检查streamlit_workflow.py是否存在
    if not streamlit_app.exists():
        print(f"错误: 找不到 {streamlit_app}")
        sys.exit(1)
    
    # 设置环境变量
    env = os.environ.copy()
    env['PYTHONPATH'] = str(current_dir)
    
    # 构建streamlit命令
    cmd = [
        sys.executable, "-m", "streamlit", "run", 
        str(streamlit_app),
        "--server.port=8501",
        "--server.address=localhost",
        "--browser.gatherUsageStats=false"
    ]
    
    print("🚀 启动FPGA智能开发工作流程...")
    print(f"📂 工作目录: {current_dir}")
    print(f"🌐 访问地址: http://localhost:8501")
    print("\n按 Ctrl+C 停止服务器\n")
    
    try:
        # 启动streamlit应用
        subprocess.run(cmd, cwd=current_dir, env=env)
    except KeyboardInterrupt:
        print("\n👋 服务器已停止")
    except Exception as e:
        print(f"❌ 启动失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()