"""
FPGA Interactive Workflow
交互式FPGA开发工作流程

这个模块提供了一个交互式的FPGA开发环境，用户可以通过命令行界面
与FPGA开发智能体团队进行交互，完成从需求分析到代码生成的完整流程。
"""

import os
import sys
import logging
from typing import Dict, Any, Optional
from datetime import datetime

from graph.builder import build_graph_with_memory
from graph.types import State
from llm_monitor import initial_langfuse_config, test_connect_2_langfuse, langfuse_callback_handler
from llm_monitor import LangfuseServerSelection

from langfuse.langchain import CallbackHandler

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class FPGAWorkflow:
    """
    FPGA交互式工作流程类

    提供完整的FPGA开发流程，包括：
    1. 需求分析和规划
    2. 代码生成
    3. 测试台生成
    4. 仿真验证
    5. 调试优化
    """
    
    def __init__(self):
        """
        初始化FPGA工作流程: 创建工作流程图，对工作图进行编译
        
        Args:
            use_memory: 是否使用持久化内存
        """
        self.graph = self._build_graph()
        # try:
        #     with open("hello.png","wb") as f:
        #         f.write(self.graph.get_graph().draw_mermaid_png())
        # except:
        #     print("hello")
    
    def _build_graph(self):
        """构建工作流程图"""
        return build_graph_with_memory()
    


    def run_interactive(self):
        """
        运行交互式工作流程
        """
        # 初始化 langfuse 配置，并根据连接测试结果创建 langfuse 回调处理器
        initial_langfuse_config(LangfuseServerSelection.Local)
        if test_connect_2_langfuse():
            langfuse_handler = langfuse_callback_handler()
        else:
            langfuse_handler = None

        # 向用户展示工作流的内容
        print("\n" + "="*60)
        print("🚀 欢迎使用FPGA智能开发工作流程!")
        print("="*60)
        print("这个工具将帮助您完成从需求分析到代码生成的完整FPGA开发流程。")
        print("您可以随时输入 'quit' 或 'exit' 退出程序。\n")
        
        while True:
            # 获取用户需求
            user_input = self._get_user_input()
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("\n👋 感谢使用FPGA开发工作流程，再见!")
                break
            
            if not user_input.strip():
                print("❌ 请输入有效的需求描述。")
                continue
            break
            
        # 创建初始状态：state中的初始信息为用户输入，并默认需要人工审核每一步操作，定义项目所需的所有任务都未完成
        state = {
            # Runtime Variables
            "messages": [{"role": "user", "content": user_input}],
            "auto_accepted_plan": False,
            "task_finished": {
            "time_analysis":    False,
            "module_code_writing": False,
            "testbench_writing":   False,
            "logic_test":          False
            },
            "next_step": ""
        }
        
        # 运行工作流程
        print("\n🔄 开始处理您的需求...")
        self._run_workflow(state, langfuse_handler)       # 将拥护初始输入构成的状态输入
                                
    
    def _get_user_input(self) -> str:
        """获取用户输入"""
        print("\n📝 请描述您的FPGA设计需求:")
        print("   例如: '设计一个8位计数器，带使能和复位功能'")
        print("   或者: '实现一个FIFO缓冲器，深度为16，数据位宽8位，采用同步复位（所有保存的数据置零），包含读、写使能接口以及空满状态输出'")
        print("-" * 50)
        
        user_input = input("💡 您的需求: ").strip()
        return user_input
    
    def _run_workflow(self, initial_state: State, langfuse_callback: CallbackHandler = None) -> State:
        """
        运行工作流程
        
        Args:
            initial_state: 初始状态
        
        Returns:
            最终状态
        """
        try:
            # 使用stream方法支持interrupt，并根据 langfuse 的连接情况添加回调处理器
            if langfuse_callback:
                config = {
                    "configurable": {"thread_id": "default"},       # 设置线程ID，标识不同线程
                    "recursion_limit": 100,                         # 递归限制，避免浪费资源
                    "callbacks": [langfuse_callback]                # 添加 langfuse 回调器
                }
            else:
                config = {
                    "configurable": {"thread_id": "default"},       # 设置线程ID，标识不同线程
                    "recursion_limit": 100,                         # 递归限制，避免浪费资源
                }
            
            return self._run_stream_with_interrupts(initial_state, config)
            
        except Exception as e:
            # 处理异常情况
            logger.error(f"工作流程执行失败: {e}")
            print(f"\n❌ 工作流程执行失败: {e}")
            # 返回错误状态
            initial_state["error_message"] = str(e)
            initial_state["is_complete"] = False
            return initial_state
    
    def _run_stream_with_interrupts(self, state: State, config: Dict[str, Any]) -> State:
        """
        运行带中断处理的流程
        
        Args:
            state: 当前状态
            config: 配置
        
        Returns:
            最终状态
        """
        from langgraph.types import Command
        
        last_message_cnt = 0
        final_state = state
        current_state = state
        
        while True:
            stream_finished = True
            
            # 开始流式执行
            for s in self.graph.stream(current_state, config=config, stream_mode="values"):
                
                # 检查是否有中断
                if "__interrupt__" in s:
                    # 从包含中断的回复中提取中断内容
                    interrupts = s["__interrupt__"]
                    print(f"\n⏸️  检测到中断: {len(interrupts)} 个")
                    
                    for interrupt_info in interrupts:
                        # Interrupt对象有resumable和value属性，不是字典。hasattr用于安全地检查属性是否存在
                        if hasattr(interrupt_info, 'resumable') and interrupt_info.resumable:
                            # 获取中断的值（用户需要回应的内容）
                            interrupt_value = interrupt_info.value if hasattr(interrupt_info, 'value') else str(interrupt_info)
                            print(f"\n💬 {interrupt_value}")
                            
                            # 获取用户输入
                            user_response = input("\n👤 您的回应:")
                            
                            # 创建恢复命令(用于返回到发生中断的位置)
                            resume_command = Command(resume=user_response)
                            
                            print(f"\n✅ 正在恢复执行...")
                            
                            try:
                                # 使用Command恢复执行，但不递归调用(即在处理好当前的中断后，跳出当前处理各个中断的循环，以新的由恢复的Command继续执行工作流)
                                current_state = resume_command
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
                    
                    # 如果处理了某个中断(即stream_finished为False)，跳出for循环，从while循环重新开始
                    if not stream_finished:
                        break
                
                # 正常处理流输出，识别并打印新的信息输出(或是动态处理其它指令)，将新的s作为final_state
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
    
    def _process_stream_output(self, s: Dict[str, Any], last_message_cnt: int) -> tuple:
        """
        处理流输出
        
        Args:
            s: 流输出
            last_message_cnt: 上次消息数量
        
        Returns:
            (更新后的状态, 新的消息数量)
        """
        try:
            if isinstance(s, dict) and "messages" in s:             # 检查流输出 s 是否为包含 messages 的字典
                if len(s["messages"]) > last_message_cnt:           # 确认是否有新消息产生
                    last_message_cnt = len(s["messages"])
                    message = s["messages"][-1]                     # 提取最新消息
                    if isinstance(message, tuple):                  # 动态处理不同消息格式
                        print(message)
                    else:
                        message.pretty_print()
                return s, last_message_cnt
            else:
                # 处理其它的模型输出数据结构
                print(f"Output: {s}")
                return s, last_message_cnt
                
        except Exception as e:
            logger.error(f"Error processing stream output: {e}")
            print(f"Error processing output: {str(e)}")
            return s, last_message_cnt

if __name__ == "__main__":
    workflow = FPGAWorkflow()
    workflow.run_interactive()