import datetime
import sys
import os
import queue
import time
import threading
from typing import Dict, Any, Optional

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from graph.types import State
from graph.builder import build_graph_with_memory
from langchain_core.messages import HumanMessage, AIMessage


class StreamlitFPGAWorkflow:
    """
    Streamlit版本的FPGA工作流程管理器
    负责工作流程的执行和状态管理，与UI逻辑分离
    """
    
    def __init__(self):
        self.graph = self._build_graph()
        self.state = State()
        self.config = {}
        self.workflow_running = False
        self.message_queue = queue.Queue()
        self.workflow_task = None

    def _build_graph(self):
        """构建工作流程图"""
        return build_graph_with_memory()
    
    def initialize_config(self):
        """初始化配置"""
        self.config = {
            "configurable": {"thread_id": "default"},
            "recursion_limit": 100,
        }
    
    def run_workflow(self, user_input: str):
        """运行工作流程"""
        try:
            # 创建初始状态
            self.state = {
                # Runtime Variables
                "messages": [{"role": "user", "content": user_input}],
                "auto_accepted_plan": False,
            }    
            # 运行工作流程
            self.message_queue.put(("info", "🔄 开始处理您的需求..."))
            final_state = self._run_workflow_with_ui_interrupts()
            
            # 处理最终结果
            if "error_message" in final_state:
                self.message_queue.put(("error", f"❌ 工作流程执行失败: {final_state['error_message']}"))
            else:
                self.message_queue.put(("success", "✅ 工作流程执行完成！"))
                
        except Exception as e:
            self.message_queue.put(("error", f"❌ 执行过程中发生错误: {str(e)}"))
        finally:
            self.workflow_running = False
    
    def _run_workflow_with_ui_interrupts(self) -> State:
        """运行带UI中断处理的工作流程"""
        from langgraph.types import Command
                
        last_message_cnt = 0
        final_state = self.state
        current_state = self.state
        
        while True:
            stream_finished = True
            
            # 开始流式执行
            for s in self.graph.stream(self.state, config=self.config, stream_mode="values"):
                
                # 检查是否有中断
                if "__interrupt__" in s:
                    interrupts = s["__interrupt__"]
                    self.message_queue.put(("info", f"⏸️ 检测到中断,工作流程需要您的确认才能继续"))
                    
                    for interrupt_info in interrupts:
                        # Interrupt对象有resumable和value属性，不是字典
                        if hasattr(interrupt_info, 'resumable') and interrupt_info.resumable:
                            # 获取中断的值（用户需要回应的内容）
                            interrupt_value = interrupt_info.value if hasattr(interrupt_info, 'value') else str(interrupt_info)
                            self.message_queue.put(("interrupt", interrupt_value))
                            
                            # 直接设置中断状态
                            self.current_interrupt = interrupt_info
                            self.interrupt_state = final_state

                            # 等待UI层处理中断并提供用户输入
                            return final_state
                        else:
                            self.message_queue.put(("warning", f"⚠️ 不可恢复的中断: {interrupt_info}"))
                
                # 正常处理流输出
                result = self._process_stream_output(s, last_message_cnt)
                if isinstance(result, tuple):
                    final_state, last_message_cnt = result
                else:
                    final_state = result
            
            # 如果流正常结束（没有中断），退出while循环
            if stream_finished:
                break
        
        return final_state
    

    
    def add_user_response(self, user_response: str):
        """添加用户响应到当前状态"""
        if hasattr(self, 'interrupt_state') and self.interrupt_state:
            self.interrupt_state["messages"].append(
                HumanMessage(content=user_response, name="user")
            )
            # 清除中断状态，让流程继续
            self.current_interrupt = None
            self.interrupt_state = None
            self.message_queue.put(("info", "✅ 正在恢复执行..."))
    

    
    def _process_stream_output(self, s: Dict[str, Any], last_message_cnt: int) -> tuple:
        """处理流输出并发送到消息队列"""
        try:
            if isinstance(s, dict) and "messages" in s:
                if len(s["messages"]) > last_message_cnt:
                    last_message_cnt = len(s["messages"])
                    message = s["messages"][-1]
                    
                    # 将消息发送到队列
                    if hasattr(message, 'content'):
                        role = "assistant" if hasattr(message, 'name') and message.name != "user" else "user"
                        self.message_queue.put(("message", {"role": role, "content": message.content}))
                    else:
                        self.message_queue.put(("message", {"role": "assistant", "content": f"{message.name}: {str(message)}"}))
                        
                return s, last_message_cnt
            else:
                self.message_queue.put(("info", f"输出: {s}"))
                return s, last_message_cnt
                
        except Exception as e:
            self.message_queue.put(("error", f"处理输出时出错: {str(e)}"))
            return s, last_message_cnt
    
    def get_messages_from_queue(self):
        """从消息队列获取所有待处理消息"""
        messages = []
        while not self.message_queue.empty():
            try:
                msg_type, content = self.message_queue.get_nowait()
                messages.append((msg_type, content))
            except queue.Empty:
                break
        return messages
    
    def is_running(self) -> bool:
        """检查工作流程是否正在运行"""
        return self.workflow_running and (self.workflow_task is not None and self.workflow_task.is_alive())
    
    def has_interrupt(self):
        """检查是否有待处理的中断"""
        return hasattr(self, 'current_interrupt') and self.current_interrupt is not None
    
    def stop_workflow(self):
        """停止工作流程"""
        self.workflow_running = False
        if self.workflow_task and self.workflow_task.is_alive():
            # Thread objects don't have cancel method, we can only set a flag
            # and wait for the thread to check it
            pass
    
    def reset(self):
        """重置工作流程状态"""
        self.workflow_running = False
        self.state = State()
        self.config = {}
        if self.workflow_task and self.workflow_task.is_alive():
            # Thread objects don't have cancel method
            pass
        self.workflow_task = None
        
        # 清空消息队列
        while not self.message_queue.empty():
            try:
                self.message_queue.get_nowait()
            except:
                break
                
        # 清除中断状态
        if hasattr(self, 'current_interrupt'):
            self.current_interrupt = None
        if hasattr(self, 'interrupt_state'):
            self.interrupt_state = None