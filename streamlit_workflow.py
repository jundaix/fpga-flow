#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Streamlit UI for FPGA Interactive Workflow
Streamlit版本的交互式FPGA开发工作流程

这个模块提供了一个基于Streamlit的Web界面，用户可以通过浏览器
与FPGA开发智能体团队进行交互，完成从需求分析到代码生成的完整流程。

特性:
- 状态持久化
- 工作流中断恢复
- 实时对话历史显示
- 响应式UI设计
"""

import os
import sys
import logging
import json
import traceback
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path

import streamlit as st
from langchain_core.messages import AIMessage, HumanMessage, BaseMessage
from langgraph.types import Command

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from graph.builder import build_graph_with_memory
from graph.types import State

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Streamlit页面配置
st.set_page_config(
    page_title="FPGA智能开发工作流程",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

class StreamlitFPGAWorkflow:
    """
    基于Streamlit的FPGA交互式工作流程类
    
    提供完整的FPGA开发流程Web界面，包括：
    1. 需求分析和规划
    2. 代码生成
    3. 测试台生成
    4. 仿真验证
    5. 调试优化
    """
    
    def __init__(self):
        """初始化Streamlit FPGA工作流程"""
        self.graph = self._build_graph()
        self._init_session_state()
    
    def _build_graph(self):
        """构建工作流程图"""
        return build_graph_with_memory()
    
    def _init_session_state(self):
        """初始化Streamlit会话状态"""
        # 工作流状态
        if 'workflow_state' not in st.session_state:
            st.session_state.workflow_state = {
                "messages": [],
                "auto_accepted_plan": False,
                "current_plan": "",
                "module_name": "",
                "project_name": "",
                "module_description": "",
                "module_definition": "",
                "module_code": "",
                "testbench_code": "",
                "requirements": "",
                "has_enough_context": False,
                "additional_info_needed": "",
                "is_complete": False,
                "error_message": ""
            }
        
        # UI状态
        if 'chat_history' not in st.session_state:
            st.session_state.chat_history = []
        
        if 'workflow_running' not in st.session_state:
            st.session_state.workflow_running = False
        
        if 'current_interrupt' not in st.session_state:
            st.session_state.current_interrupt = None
        
        if 'thread_id' not in st.session_state:
            st.session_state.thread_id = f"default"
        
        if 'workflow_config' not in st.session_state:
            st.session_state.workflow_config = {
                "configurable": {"thread_id": st.session_state.thread_id},
                "recursion_limit": 100,
            }
    
    def _add_to_chat_history(self, role: str, content: str, timestamp: Optional[str] = None):
        """添加消息到聊天历史"""
        if timestamp is None:
            timestamp = datetime.now().strftime("%H:%M:%S")
        
        st.session_state.chat_history.append({
            "role": role,
            "content": content,
            "timestamp": timestamp
        })
    
    def _display_chat_history(self):
        """显示聊天历史（已弃用，现在直接在主界面显示）"""
        # 此方法已被新的布局替代，保留以防其他地方调用
        pass
    
    def _display_workflow_status(self):
        """显示工作流状态"""
        st.sidebar.subheader("📊 工作流状态")
        
        # 显示当前状态
        if st.session_state.workflow_running:
            st.sidebar.success("🔄 工作流运行中...")
        elif st.session_state.current_interrupt:
            st.sidebar.warning("⏸️ 等待用户输入")
        else:
            st.sidebar.info("⏹️ 工作流空闲")
        
        # 显示项目信息
        state = st.session_state.workflow_state
        if state.get("project_name"):
            st.sidebar.write(f"**项目名称:** {state['project_name']}")
        if state.get("module_name"):
            st.sidebar.write(f"**模块名称:** {state['module_name']}")
        
        # 显示进度
        progress_items = [
            ("需求分析", bool(state.get("requirements"))),
            ("模块规划", bool(state.get("current_plan"))),
            ("代码生成", bool(state.get("module_code"))),
            ("测试生成", bool(state.get("testbench_code"))),
        ]
        
        st.sidebar.write("**进度:**")
        for item, completed in progress_items:
            icon = "✅" if completed else "⏳"
            st.sidebar.write(f"{icon} {item}")
    
    def _display_project_files(self):
        """显示项目文件"""
        st.sidebar.subheader("📁 项目文件")
        
        state = st.session_state.workflow_state
        project_name = state.get("project_name")
        
        if not project_name:
            st.sidebar.info("暂无项目文件")
            return
        
        # 检查工作空间目录
        workspace_dir = Path(__file__).parent / "workspace" / project_name
        
        if workspace_dir.exists():
            # 显示源代码文件
            src_dir = workspace_dir / "src"
            if src_dir.exists():
                st.sidebar.write("**源代码:**")
                for file_path in src_dir.glob("*.v"):
                    if st.sidebar.button(f"📄 {file_path.name}", key=f"src_{file_path.name}"):
                        self._show_file_content(file_path)
            
            # 显示测试文件
            test_dir = workspace_dir / "test"
            if test_dir.exists():
                st.sidebar.write("**测试文件:**")
                for file_path in test_dir.glob("*.v"):
                    if st.sidebar.button(f"🧪 {file_path.name}", key=f"test_{file_path.name}"):
                        self._show_file_content(file_path)
        else:
            st.sidebar.info("项目目录不存在")
    
    def _show_file_content(self, file_path: Path):
        """显示文件内容"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            st.subheader(f"📄 {file_path.name}")
            st.code(content, language='verilog')
        except Exception as e:
            st.error(f"无法读取文件 {file_path.name}: {e}")
    
    def _process_user_input(self, user_input: str):
        """处理用户输入"""
        if not user_input.strip():
            st.warning("请输入有效的内容")
            return
        
        # 添加用户消息到聊天历史
        self._add_to_chat_history("user", user_input)
        
        # 处理中断恢复
        if st.session_state.current_interrupt:
            self._handle_interrupt_response(user_input)
        else:
            # 开始新的工作流
            self._start_new_workflow(user_input)
    
    def _start_new_workflow(self, user_input: str):
        """开始新的工作流"""
        try:
            # 重置状态
            st.session_state.workflow_state["messages"] = [
                {"role": "user", "content": user_input}
            ]
            st.session_state.workflow_running = True
            st.session_state.current_interrupt = None
            
            # 运行工作流
            self._run_workflow()
            
        except Exception as e:
            logger.error(f"启动工作流失败: {e}")
            st.error(f"启动工作流失败: {e}")
            self._add_to_chat_history("system", f"错误: {e}")
            st.session_state.workflow_running = False
    
    def _handle_interrupt_response(self, user_response: str):
        """处理中断响应"""
        try:
            # 清除当前中断
            interrupt_info = st.session_state.current_interrupt
            st.session_state.current_interrupt = None
            st.session_state.workflow_running = True
            
            # 使用Command恢复执行，而不是重新开始工作流
            self._resume_workflow_with_response(user_response)
            
        except Exception as e:
            logger.error(f"处理中断响应失败: {e}")
            st.error(f"处理中断响应失败: {e}")
            self._add_to_chat_history("system", f"错误: {e}")
            st.session_state.workflow_running = False
    
    def _resume_workflow_with_response(self, user_response: str):
        """使用用户响应恢复工作流执行"""
        try:
            config = st.session_state.workflow_config
            
            # 创建恢复命令
            resume_command = Command(resume=user_response)
            
            # 使用恢复命令继续执行工作流
            self._run_workflow_stream_with_resume(resume_command, config)
            
        except Exception as e:
            logger.error(f"恢复工作流失败: {e}")
            # 如果恢复失败，尝试手动更新状态后重新运行
            st.session_state.workflow_state["messages"].append(
                HumanMessage(content=user_response, name="user")
            )
            self._run_workflow()
    
    def _run_workflow_stream_with_resume(self, resume_command, config):
        """使用恢复命令执行工作流流处理"""
        current_state = resume_command
        
        while True:
            stream_finished = True
            
            # 使用stream方法运行工作流
            for s in self.graph.stream(current_state, config=config, stream_mode="values"):
                # 检查是否有中断
                if "__interrupt__" in s:
                    interrupts = s["__interrupt__"]
                    if interrupts:
                        interrupt_info = interrupts[0]  # 取第一个中断
                        if hasattr(interrupt_info, 'resumable') and interrupt_info.resumable:
                            # 获取中断消息
                            interrupt_message = interrupt_info.value if hasattr(interrupt_info, 'value') else str(interrupt_info)
                            
                            # 设置中断状态
                            st.session_state.current_interrupt = {
                                "message": interrupt_message,
                                "info": interrupt_info
                            }
                            
                            # 添加中断消息到聊天历史
                            self._add_to_chat_history("assistant", interrupt_message)
                            
                            st.session_state.workflow_running = False
                            return  # 等待用户响应
                
                # 处理正常流输出
                self._process_stream_output(s)
            
            # 如果没有中断，工作流完成
            if stream_finished:
                st.session_state.workflow_running = False
                self._add_to_chat_history("system", "工作流已完成")
                break
    
    def _run_workflow(self):
        """运行工作流"""
        try:
            config = st.session_state.workflow_config
            state = st.session_state.workflow_state
            
            self._run_workflow_stream(state, config)
            
        except Exception as e:
            logger.error(f"工作流执行失败: {e}")
            st.error(f"工作流执行失败: {e}")
            self._add_to_chat_history("system", f"工作流执行失败: {e}")
            st.session_state.workflow_running = False
    
    def _run_workflow_stream(self, current_state, config):
        """执行工作流流处理"""
        while True:
            stream_finished = True
            
            # 使用stream方法运行工作流
            for s in self.graph.stream(current_state, config=config, stream_mode="values"):
                # 检查是否有中断
                if "__interrupt__" in s:
                    interrupts = s["__interrupt__"]
                    if interrupts:
                        interrupt_info = interrupts[0]  # 取第一个中断
                        if hasattr(interrupt_info, 'resumable') and interrupt_info.resumable:
                            # 获取中断消息
                            interrupt_message = interrupt_info.value if hasattr(interrupt_info, 'value') else str(interrupt_info)
                            
                            # 设置中断状态
                            st.session_state.current_interrupt = {
                                "message": interrupt_message,
                                "info": interrupt_info
                            }
                            
                            # 添加中断消息到聊天历史
                            self._add_to_chat_history("assistant", interrupt_message)
                            
                            st.session_state.workflow_running = False
                            return  # 等待用户响应
                
                # 处理正常流输出
                self._process_stream_output(s)
            
            # 如果没有中断，工作流完成
            if stream_finished:
                st.session_state.workflow_running = False
                self._add_to_chat_history("system", "工作流已完成")
                break
    
    def _process_stream_output(self, s: Dict[str, Any]):
        """处理流输出"""
        try:
            if isinstance(s, dict):
                # 更新工作流状态
                st.session_state.workflow_state.update(s)
                
                # 处理新消息
                if "messages" in s and s["messages"]:
                    last_message = s["messages"][-1]
                    if hasattr(last_message, 'content') and hasattr(last_message, 'name'):
                        # 添加AI消息到聊天历史
                        self._add_to_chat_history(
                            "assistant", 
                            f"[{last_message.name}] {last_message.content}"
                        )
                    elif isinstance(last_message, dict):
                        content = last_message.get('content', str(last_message))
                        role = last_message.get('role', 'assistant')
                        self._add_to_chat_history(role, content)
                        
        except Exception as e:
            logger.error(f"处理流输出失败: {e}")
    
    def _reset_workflow(self):
        """重置工作流"""
        # 重置会话状态
        st.session_state.workflow_state = {
            "messages": [],
            "auto_accepted_plan": False,
            "current_plan": "",
            "module_name": "",
            "project_name": "",
            "module_description": "",
            "module_definition": "",
            "module_code": "",
            "testbench_code": "",
            "requirements": "",
            "has_enough_context": False,
            "additional_info_needed": "",
            "is_complete": False,
            "error_message": ""
        }
        st.session_state.chat_history = []
        st.session_state.workflow_running = False
        st.session_state.current_interrupt = None
        
        # 生成新的线程ID
        st.session_state.thread_id = f"streamlit_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        st.session_state.workflow_config["configurable"]["thread_id"] = st.session_state.thread_id
        
        st.success("工作流已重置")
    
    def run(self):
        """运行Streamlit应用"""
        # 页面标题
        st.title("🚀 FPGA智能开发工作流程")
        
        # 侧边栏
        with st.sidebar:
            st.title("🛠️ 控制面板")
            
            # 重置按钮
            if st.button("🔄 重置工作流", type="secondary"):
                self._reset_workflow()
                st.rerun()
            
            st.markdown("---")
            
            # 显示工作流状态
            self._display_workflow_status()
            
            st.markdown("---")
            
            # 显示项目文件
            self._display_project_files()
        
        # 主界面 - ChatGPT 风格布局
        # 创建聊天历史容器（占据大部分空间）
        chat_container = st.container(height=500)
        
        with chat_container:
            if not st.session_state.chat_history:
                st.info("💡 欢迎使用 FPGA 智能开发工作流程！请在下方输入您的设计需求开始对话...")
            else:
                # 显示聊天历史
                for i, msg in enumerate(st.session_state.chat_history):
                    with st.chat_message(msg["role"]):
                        st.write(f"**[{msg['timestamp']}]** {msg['content']}")
        
        # 状态提示区域
        status_container = st.container()
        with status_container:
            if st.session_state.current_interrupt:
                st.warning(f"💭 等待您的回应: {st.session_state.current_interrupt['message']}")
            elif st.session_state.workflow_running:
                st.info("🔄 工作流运行中，请稍候...")
        
        # 输入区域（固定在底部）
        input_container = st.container()
        with input_container:
            with st.form(key="user_input_form", clear_on_submit=True):
                user_input = st.text_area(
                    "💬 请输入您的消息:",
                    placeholder="例如: 设计一个8位计数器，带使能和复位功能",
                    height=80,
                    disabled=st.session_state.workflow_running,
                    label_visibility="collapsed"
                )
                
                # 创建两列布局用于按钮
                col1, col2, col3 = st.columns([6, 1, 1])
                
                with col2:
                    submit_button = st.form_submit_button(
                        "📤 发送",
                        type="primary",
                        disabled=st.session_state.workflow_running,
                        use_container_width=True
                    )
                
                with col3:
                    clear_button = st.form_submit_button(
                        "🗑️ 清空",
                        type="secondary",
                        use_container_width=True
                    )
                
                if submit_button and user_input:
                    self._process_user_input(user_input)
                    st.rerun()
                
                if clear_button:
                    # 清空输入框的逻辑会通过 clear_on_submit=True 自动处理
                    pass

def main():
    """主函数"""
    try:
        workflow = StreamlitFPGAWorkflow()
        workflow.run()
    except Exception as e:
        st.error(f"应用启动失败: {e}")
        st.exception(e)

if __name__ == "__main__":
    main()