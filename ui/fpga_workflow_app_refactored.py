import streamlit as st
import threading
import time
from workflow_manager import StreamlitFPGAWorkflow
from ui_state_manager import UIStateManager
from ui_components import UIComponents

# 设置页面配置
st.set_page_config(
    page_title="FPGA智能开发工作流程",
    page_icon="🚀",
    layout="wide"
)


class FPGAWorkflowApp:
    """
    FPGA工作流程应用主控制器
    协调工作流程管理器、UI状态管理器和UI组件之间的交互
    """
    
    def __init__(self):
        # 初始化各个管理器
        self.ui_state = UIStateManager()
        self.ui_components = UIComponents(self.ui_state)
        
        # 初始化工作流程管理器
        if "fpga_workflow" not in st.session_state:
            st.session_state.fpga_workflow = StreamlitFPGAWorkflow()
            st.session_state.fpga_workflow.initialize_config()
        
        self.workflow_manager = st.session_state.fpga_workflow
    
    def run(self):
        """运行主应用"""
        # 渲染页面头部
        self.ui_components.render_page_header()
        
        # 检查并处理工作流程消息
        messages_updated = self._process_workflow_messages()
        
        # 如果有消息更新，重新运行页面
        if messages_updated:
            st.rerun()
        
        # 渲染聊天消息
        self.ui_components.render_chat_messages()
        
        # 分隔线
        st.markdown("---")
        
        # 处理用户输入
        self._handle_user_input()
        
        # 渲染侧边栏
        self._handle_sidebar_actions()
        
        # 渲染页面底部
        self.ui_components.render_page_footer()
        
        # 自动刷新检查（如果工作流程正在运行）
        if self.workflow_manager.is_running():
            time.sleep(2)
            st.rerun()
    
    def _process_workflow_messages(self) -> bool:
        """处理工作流程消息队列"""
        messages_updated = False
        workflow_messages = self.workflow_manager.get_messages_from_queue()
        
        for msg_type, content in workflow_messages:
            if msg_type == "message":
                self.ui_state.add_message(content["role"], content["content"])
                messages_updated = True
            elif msg_type == "interrupt":
                # 处理中断
                self.ui_state.set_current_interrupt(content)
                self.ui_state.add_message("assistant", f"💬 {content}")
                messages_updated = True
            elif msg_type in ["info", "error", "success", "warning"]:
                self.ui_state.add_message("assistant", content)
                messages_updated = True
        
        return messages_updated
    
    def _handle_user_input(self):
        """处理用户输入"""
        if self.ui_state.is_waiting_for_response():
            # 处理中断响应
            user_response = self.ui_components.render_interrupt_input()
            if user_response:
                self._handle_interrupt_response(user_response)
        else:
            # 处理正常输入
            user_input = self.ui_components.render_normal_input(self.workflow_manager.is_running())
            if user_input:
                self._handle_normal_input(user_input)
    
    def _handle_interrupt_response(self, user_response: str):
        """处理中断响应"""
        # 添加用户响应到聊天记录
        self.ui_state.add_message("user", user_response)
        
        # 清除中断状态
        self.ui_state.clear_interrupt_state()
        
        # 恢复工作流程
        self.workflow_manager.add_user_response(user_response)
        
        st.rerun()
    
    def _handle_normal_input(self, user_input: str):
        """处理正常用户输入"""
        # 添加用户消息到聊天记录
        self.ui_state.add_message("user", user_input)
        
        # 启动工作流程
        self.workflow_manager.workflow_running = True
        # 在新线程中运行工作流程
        self.workflow_manager.workflow_task = threading.Thread(
            target=self.workflow_manager.run_workflow,
            args=(user_input,),
            daemon=True
        )
        self.workflow_manager.workflow_task.start()
        
        st.rerun()
    
    def _handle_sidebar_actions(self):
        """处理侧边栏操作"""
        actions = self.ui_components.render_sidebar(self.workflow_manager.is_running())
        
        if actions["clear_chat"]:
            self._clear_chat_history()
        
        if actions["export_chat"]:
            self._export_chat_history()
    
    def _clear_chat_history(self):
        """清除聊天记录"""
        self.ui_state.clear_messages()
        self.workflow_manager.reset()
        st.rerun()
    
    def _export_chat_history(self):
        """导出聊天记录"""
        self.ui_components.render_export_download()


def main():
    """主函数"""
    app = FPGAWorkflowApp()
    app.run()


if __name__ == "__main__":
    main()