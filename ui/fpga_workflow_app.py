import streamlit as st
import datetime
import sys
import os
import threading
import queue
import time
from typing import Dict, Any, Optional

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from graph.types import State
from graph.builder import build_graph_with_memory
from langchain_core.messages import HumanMessage, AIMessage

# 设置页面配置
st.set_page_config(
    page_title="FPGA智能开发工作流程",
    page_icon="🚀",
    layout="wide"
)

class StreamlitFPGAWorkflow:
    """
    Streamlit版本的FPGA工作流程
    将原有的终端交互转换为Web UI交互
    """
    
    def __init__(self):
        self.graph = self._build_graph()
        self.state = State()
        self.config = {}
        self.workflow_running = False

    def _build_graph(self):
        """构建工作流程图"""
        return build_graph_with_memory()
    
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

        self.config = {
                "configurable": {"thread_id": "default"},
                "recursion_limit": 100,
            }
        if "workflow_state" not in st.session_state:
            st.session_state.workflow_state = None
        
        if "waiting_for_response" not in st.session_state:
            st.session_state.waiting_for_response = False
        
        if "current_interrupt" not in st.session_state:
            st.session_state.current_interrupt = None
    
    def add_message(self, role: str, content: str):
        """添加消息到聊天记录"""
        st.session_state.messages.append({
            "role": role,
            "content": content,
            "timestamp": datetime.datetime.now()
        })
    
    def run_workflow_async(self, user_input: str):
        """异步运行工作流程"""
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
        final_state = state
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
                            self.message_queue.put((f"💬 {interrupt_value}"))
                            
                            # 获取用户输入
                            user_response = input("\n👤 您的回应:")
                            
                            # 创建恢复命令
                            resume_command = Command(resume=user_response)
                            
                            print(f"\n✅ 正在恢复执行...")
                            
                            try:
                                # 使用Command恢复执行，但不递归调用
                                self.state = resume_command
                                stream_finished = False
                                break  # 跳出当前for循环，重新开始while循环
                                
                            except Exception as resume_error:
                                logger.error(f"恢复执行失败: {resume_error}")
                                print(f"\n❌ 恢复执行失败: {resume_error}")
                                # 如果恢复失败，尝试手动更新状态
                                from langchain_core.messages import HumanMessage
                                final_state["messages"].append(
                                    HumanMessage(content=user_response, name="user")
                                )
                                return final_state
                        else:
                             print(f"\n⚠️  不可恢复的中断: {interrupt_info}")

                
                    if not stream_finished:
                        break
                
                # 正常处理流输出
                result = self._process_stream_output(s, last_message_cnt)
                if isinstance(result, tuple):
                    final_state, last_message_cnt = result
                else:
                    final_state = result
            
            # 如果流正常结束（没有中断），退出while循环
            if stream_finished:
                break
        
        logger.info("Workflow completed successfully")
        return final_state
    
    def _process_stream_output_ui(self, s: Dict[str, Any], last_message_cnt: int) -> tuple:
        """处理流输出并发送到UI"""
        try:
            if isinstance(s, dict) and "messages" in s:
                if len(s["messages"]) > last_message_cnt:
                    last_message_cnt = len(s["messages"])
                    message = s["messages"][-1]
                    
                    # 将消息发送到UI
                    if hasattr(message, 'content'):
                        role = "assistant" if hasattr(message, 'name') and message.name != "user" else "user"
                        self.message_queue.put(("message", {"role": role, "content": message.content}))
                    else:
                        self.message_queue.put(("message", {"role": "assistant", "content": f"{message.name}: str(message)"}))
                        
                return s, last_message_cnt
            else:
                self.message_queue.put(("info", f"输出: {s}"))
                return s, last_message_cnt
                
        except Exception as e:
            self.message_queue.put(("error", f"处理输出时出错: {str(e)}"))
            return s, last_message_cnt
    
    def check_messages(self):
        """检查并处理消息队列"""
        messages_updated = False
        
        while not self.message_queue.empty():
            try:
                msg_type, content = self.message_queue.get_nowait()
                
                if msg_type == "message":
                    self.add_message(content["role"], content["content"])
                    messages_updated = True
                elif msg_type in ["info", "error", "success", "warning"]:
                    self.add_message("assistant", content)
                    messages_updated = True
                    
            except queue.Empty:
                break
        
        return messages_updated
    

def main():
    # 创建工作流程实例
    if "fpga_workflow" not in st.session_state:
        st.session_state.fpga_workflow = StreamlitFPGAWorkflow()
    
    workflow_app = st.session_state.fpga_workflow
    workflow_app.initialize_session_state()
    
    # 页面标题
    st.title("🚀 FPGA智能开发工作流程")
    st.markdown("---")
    
    # 检查消息更新
    messages_updated = workflow_app.check_messages()
    
    if messages_updated:
        st.rerun()
    
    # 聊天记录显示区域
    st.subheader("💬 开发流程记录")
    chat_container = st.container()
    
    with chat_container:
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.write(message["content"])
                st.caption(f"时间: {message['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 分隔线
    st.markdown("---")
    
    # 输入区域
    if st.session_state.waiting_for_response:
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
            workflow_app.resume_workflow_with_response(user_response)
            st.rerun()
    
    else:
        st.subheader("✍️ 发送消息")
        
        # 显示工作流程状态
        if workflow_app.workflow_running:
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
        
        # 处理用户输入
        if send_button and user_input:
            # 添加用户消息
            workflow_app.add_message("user", user_input)
            
            # 启动工作流程
            workflow_app.workflow_running = True
            workflow_app.workflow_thread = threading.Thread(
                target=workflow_app.run_workflow_async,
                args=(user_input,)
            )
            workflow_app.workflow_thread.start()
            
            st.rerun()
    
    # 侧边栏
    with st.sidebar:
        st.header("⚙️ 工作流程控制")
        
        # 清除记录按钮
        if st.button("🗑️ 清除开发记录", type="secondary"):
            st.session_state.messages = [
                {
                    "role": "assistant", 
                    "content": "🚀 欢迎使用FPGA智能开发工作流程！\n\n开发记录已清除。请描述您的新FPGA设计需求。", 
                    "timestamp": datetime.datetime.now()
                }
            ]
            st.session_state.waiting_for_response = False
            st.session_state.current_interrupt = None
            workflow_app.workflow_running = False
            st.rerun()
        
        # 导出记录
        if st.button("📥 导出开发记录"):
            chat_history = ""
            for msg in st.session_state.messages:
                role = "用户" if msg["role"] == "user" else "助手"
                chat_history += f"[{msg['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}] {role}: {msg['content']}\n\n"
            
            st.download_button(
                label="下载开发记录",
                data=chat_history,
                file_name=f"fpga_development_log_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                mime="text/plain"
            )
        
        st.markdown("---")
        
        # 状态信息
        st.markdown("### 📊 状态信息")
        total_messages = len(st.session_state.messages)
        user_messages = len([msg for msg in st.session_state.messages if msg["role"] == "user"])
        assistant_messages = len([msg for msg in st.session_state.messages if msg["role"] == "assistant"])
        
        st.metric("总消息数", total_messages)
        st.metric("用户消息", user_messages)
        st.metric("系统回复", assistant_messages)
        
        if workflow_app.workflow_running:
            st.success("🔄 工作流程运行中")
        elif st.session_state.waiting_for_response:
            st.warning("⏸️ 等待用户回应")
        else:
            st.info("⏹️ 工作流程空闲")
        
        st.markdown("---")
        st.markdown("### 📋 使用说明")
        st.markdown("""
        1. 在输入框中描述您的FPGA设计需求
        2. 点击"开始开发"按钮启动工作流程
        3. 根据系统提示进行交互确认
        4. 查看生成的代码和测试结果
        5. 使用侧边栏管理开发记录
        """)
        
        st.markdown("---")
        st.markdown("### 🔗 相关链接")
        st.markdown("""
        - [FPGA设计指南](https://example.com/fpga-guide)
        - [Verilog语法参考](https://example.com/verilog)
        - [仿真工具文档](https://example.com/simulation)
        """)
    
    # 页脚
    st.markdown("---")
    st.markdown(
        "<div style='text-align: center; color: gray;'>🚀 FPGA智能开发工作流程 v2.0 | 基于Streamlit构建 | 支持完整开发流程</div>",
        unsafe_allow_html=True
    )
    
    # 自动刷新检查（每2秒检查一次消息更新）
    if workflow_app.workflow_running:
        time.sleep(2)
        st.rerun()

if __name__ == "__main__":
    main()