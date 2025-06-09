import datetime
import streamlit as st
from typing import List, Dict, Any


class UIStateManager:
    """
    Streamlit UI状态管理器
    负责管理Streamlit的session state和UI相关的状态
    """
    
    def __init__(self):
        self.initialize_session_state()
    
    def initialize_session_state(self):
        """初始化session state"""
        if "messages" not in st.session_state:
            st.session_state.messages = [
                {
                    "role": "assistant", 
                    "content": "🚀 欢迎使用FPGA智能开发工作流程！\n\n这个工具将帮助您完成从需求分析到代码生成的完整FPGA开发流程。\n\n请描述您的FPGA设计需求，例如：\n- 设计一个8位计数器，带使能和复位功能\n- 实现一个FIFO缓冲器，深度为16，数据位宽8位", 
                    "timestamp": datetime.datetime.now()
                }
            ]
        
        if "waiting_for_response" not in st.session_state:
            st.session_state.waiting_for_response = False
        
        if "current_interrupt" not in st.session_state:
            st.session_state.current_interrupt = None
        
        if "workflow_state" not in st.session_state:
            st.session_state.workflow_state = None
    
    def add_message(self, role: str, content: str):
        """添加消息到聊天记录"""
        st.session_state.messages.append({
            "role": role,
            "content": content,
            "timestamp": datetime.datetime.now()
        })
    
    def get_messages(self) -> List[Dict[str, Any]]:
        """获取所有消息"""
        return st.session_state.messages
    
    def clear_messages(self):
        """清除所有消息并重置为初始状态"""
        st.session_state.messages = [
            {
                "role": "assistant", 
                "content": "🚀 欢迎使用FPGA智能开发工作流程！\n\n开发记录已清除。请描述您的新FPGA设计需求。", 
                "timestamp": datetime.datetime.now()
            }
        ]
        self.clear_interrupt_state()
    
    def set_waiting_for_response(self, waiting: bool):
        """设置是否等待用户回应"""
        st.session_state.waiting_for_response = waiting
    
    def is_waiting_for_response(self) -> bool:
        """检查是否正在等待用户回应"""
        return st.session_state.waiting_for_response
    
    def set_current_interrupt(self, interrupt_info: Any):
        """设置当前中断信息"""
        st.session_state.current_interrupt = interrupt_info
        self.set_waiting_for_response(True)
    
    def get_current_interrupt(self) -> Any:
        """获取当前中断信息"""
        return st.session_state.current_interrupt
    
    def clear_interrupt_state(self):
        """清除中断状态"""
        st.session_state.waiting_for_response = False
        st.session_state.current_interrupt = None
    
    def set_workflow_state(self, state: Any):
        """设置工作流程状态"""
        st.session_state.workflow_state = state
    
    def get_workflow_state(self) -> Any:
        """获取工作流程状态"""
        return st.session_state.workflow_state
    
    def get_message_statistics(self) -> Dict[str, int]:
        """获取消息统计信息"""
        messages = self.get_messages()
        total_messages = len(messages)
        user_messages = len([msg for msg in messages if msg["role"] == "user"])
        assistant_messages = len([msg for msg in messages if msg["role"] == "assistant"])
        
        return {
            "total": total_messages,
            "user": user_messages,
            "assistant": assistant_messages
        }
    
    def export_chat_history(self) -> str:
        """导出聊天记录为文本格式"""
        chat_history = ""
        for msg in self.get_messages():
            role = "用户" if msg["role"] == "user" else "助手"
            chat_history += f"[{msg['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}] {role}: {msg['content']}\n\n"
        return chat_history
    
    def get_export_filename(self) -> str:
        """生成导出文件名"""
        return f"fpga_development_log_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"