import streamlit as st
import datetime
import time
from typing import Optional
from ui_state_manager import UIStateManager


class UIComponents:
    """
    Streamlit UI组件管理器
    负责渲染各种UI组件和页面布局
    """
    
    def __init__(self, ui_state: UIStateManager):
        self.ui_state = ui_state
    
    def render_page_header(self):
        """渲染页面头部"""
        st.title("🚀 FPGA智能开发工作流程")
        st.markdown("---")
    
    def render_chat_messages(self):
        """渲染聊天消息区域"""
        st.subheader("💬 开发流程记录")
        chat_container = st.container()
        
        with chat_container:
            for message in self.ui_state.get_messages():
                with st.chat_message(message["role"]):
                    st.write(message["content"])
                    st.caption(f"时间: {message['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}")
    
    def render_interrupt_input(self) -> Optional[str]:
        """渲染中断响应输入区域"""
        st.subheader("⏸️ 等待您的回应")
        st.info("工作流程需要您的确认或输入才能继续...")
        
        with st.form(key="interrupt_response_form", clear_on_submit=True):
            col1, col2 = st.columns([4, 1])
            
            with col1:
                user_response = st.text_area(
                    "请输入您的回应：",
                    height=100,
                    placeholder="请输入您的回应...",
                    label_visibility="collapsed"
                )
            
            with col2:
                st.write("")
                st.write("")
                respond_button = st.form_submit_button("回应 💬", type="primary", use_container_width=True)
        
        if respond_button and user_response:
            return user_response
        return None
    
    def render_normal_input(self, workflow_running: bool) -> Optional[str]:
        """渲染正常输入区域"""
        st.subheader("✍️ 发送消息")
        
        # 显示工作流程状态
        if workflow_running:
            st.info("🔄 工作流程正在运行中，请稍候...")
        
        with st.form(key="chat_form", clear_on_submit=True):
            col1, col2 = st.columns([4, 1])
            
            with col1:
                user_input = st.text_area(
                    "请描述您的FPGA设计需求：",
                    height=100,
                    placeholder="例如：设计一个8位计数器，带使能和复位功能",
                    label_visibility="collapsed",
                )
            
            with col2:
                st.write("")
                st.write("")
                send_button = st.form_submit_button(
                    "开始开发 🚀", 
                    type="primary", 
                    use_container_width=True,
                )
        
        if send_button and user_input:
            return user_input
        return None
    
    def render_sidebar(self, workflow_running: bool) -> dict:
        """渲染侧边栏，返回用户操作结果"""
        actions = {
            "clear_chat": False,
            "export_chat": False
        }
        
        with st.sidebar:
            st.header("⚙️ 工作流程控制")
            
            # 清除记录按钮
            if st.button("🗑️ 清除开发记录", type="secondary"):
                actions["clear_chat"] = True
            
            # 导出记录
            if st.button("📥 导出开发记录"):
                actions["export_chat"] = True
            
            st.markdown("---")
            
            # 状态信息
            self._render_status_info(workflow_running)
            
            # 使用说明
            self._render_usage_guide()
            
            # 相关链接
            self._render_related_links()
        
        return actions
    
    def _render_status_info(self, workflow_running: bool):
        """渲染状态信息"""
        st.markdown("### 📊 状态信息")
        stats = self.ui_state.get_message_statistics()
        
        st.metric("总消息数", stats["total"])
        st.metric("用户消息", stats["user"])
        st.metric("系统回复", stats["assistant"])
        
        if workflow_running:
            st.success("🔄 工作流程运行中")
        elif self.ui_state.is_waiting_for_response():
            st.warning("⏸️ 等待用户回应")
        else:
            st.info("⏹️ 工作流程空闲")
    
    def _render_usage_guide(self):
        """渲染使用说明"""
        st.markdown("---")
        st.markdown("### 📋 使用说明")
        st.markdown("""
        1. 在输入框中描述您的FPGA设计需求
        2. 点击"开始开发"按钮启动工作流程
        3. 根据系统提示进行交互确认
        4. 查看生成的代码和测试结果
        5. 使用侧边栏管理开发记录
        """)
    
    def _render_related_links(self):
        """渲染相关链接"""
        st.markdown("---")
        st.markdown("### 🔗 相关链接")
        st.markdown("""
        - [FPGA设计指南](https://example.com/fpga-guide)
        - [Verilog语法参考](https://example.com/verilog)
        - [仿真工具文档](https://example.com/simulation)
        """)
    
    def render_export_download(self):
        """渲染导出下载按钮"""
        chat_history = self.ui_state.export_chat_history()
        filename = self.ui_state.get_export_filename()
        
        st.download_button(
            label="下载开发记录",
            data=chat_history,
            file_name=filename,
            mime="text/plain"
        )
    
    def render_page_footer(self):
        """渲染页面底部"""
        st.markdown("---")
        st.markdown(
            "<div style='text-align: center; color: gray;'>🚀 FPGA智能开发工作流程 v2.0 | 基于Streamlit构建 | 支持完整开发流程</div>",
            unsafe_allow_html=True
        )
    
    def show_success_message(self, message: str):
        """显示成功消息"""
        st.success(message)
    
    def show_error_message(self, message: str):
        """显示错误消息"""
        st.error(message)
    
    def show_info_message(self, message: str):
        """显示信息消息"""
        st.info(message)
    
    def show_warning_message(self, message: str):
        """显示警告消息"""
        st.warning(message)