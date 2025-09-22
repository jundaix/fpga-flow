"""
    调用代码编写者，生成 Verilog-eval 数据的的代码，评估当前代码生成的性能
    操作流程：读取数据集内容 - 运行流程编写代码 - 保存代码
"""

import os
import logging
from datetime import datetime
from enum import Enum
from pathlib import Path

from concurrent.futures import ThreadPoolExecutor, as_completed
import traceback
import uuid

from graph.sub_code import build_graph_code_without_memory, build_graph_code_with_memory
from graph.sub_code import build_graph_for_verilogeval_without_memory
from llm_monitor import initial_langfuse_config, test_connect_2_langfuse, langfuse_callback_handler
from llm_monitor import LangfuseServerSelection


# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

workspace = Path(__file__).parent / "workspace"

class TaskType(Enum):
    spec_2_rtl = "dataset_spec-to-rtl"
    code_complete = "dataset_code-complete-iccad2023"

class Coder_Verilogeval:
    def __init__(self, task: TaskType, build_graph_func) -> None:
        self.data_file_path = Path("D:/大语言模型论文/VerilogEval/Verilogeval_test_data")             # 定义测试数据集文件位置
        self.test_task = task
        self.graph = build_graph_func()                                             # 定义任务流的图
        self.langfuse_handler = self.init_monitor()                                             # 初始化 langfuse 监视器
    
    def init_monitor(self):
        ''' 初始化 langfuse 配置，并根据连接测试结果创建 langfuse 回调处理器 '''
        initial_langfuse_config(LangfuseServerSelection.Local)
        if test_connect_2_langfuse():
            langfuse_handler = langfuse_callback_handler()
        else:
            langfuse_handler = None
        
        return langfuse_handler 

    def get_data_files(self):
        ''' 获取保存数据集的文件列表 '''
        data_files_list = []
        data_files = self.data_file_path / self.test_task.value
        for file in data_files.iterdir():
            if file.is_file() and str(file).endswith("prompt.txt"):
                data_files_list.append(str(file))

        return data_files_list
    
    def get_module_name(self, file_path: str):
        ''' 从文件路径中获取对应的问题名称 '''
        file_name = os.path.basename(file_path)
        module_name = file_name.removesuffix("_prompt.txt")
        return module_name
    
    def initial_state(self, file_path: str):
        ''' 读取任务文本，建立初始化内容 '''
        content = ""
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        # print(f"当前任务内容为：{content}")
        module_name = self.get_module_name(file_path)
        system_require = "Assume that sigals are positive clock/clk triggered unless otherwise stated.\n"

        state = {
            "module_requirements": system_require + content,
            "module_name": module_name,
            # 主动补齐默认字段
            "module_code": "",
            "syntax_error_source": "",
            "module_code_syntax_error": [],
            "module_code_logic_error": "",
            "else_error": "",
            "is_syntax_error": False,
            "is_logic_error": False,
            "is_else_error": False,
            "trying_times": 0,
            "MAX_TRY_TIMES": 5,
            }

        return state
    
    def initial_config(self, thread_id: str = "default"):
        config = {
            "configurable": {"thread_id": thread_id},
            "recursion_limit": 100,
        }
        if self.langfuse_handler:
            config["callbacks"] = [self.langfuse_handler]
        
        return config

    def run_one_file(self, data_file: str):
        """单个任务的封装，便于在线程中调用"""
        module_name = self.get_module_name(data_file)
        # 为每个并发任务分配独立 thread_id，避免监控/日志串线
        thread_id = f"{module_name}-{uuid.uuid4().hex[:8]}"
        state = self.initial_state(data_file)
        config = self.initial_config(thread_id=thread_id)

        print(f"当前执行的任务为：{module_name}")

        # 创建输出文件夹
        code_dir = workspace / module_name
        code_dir.mkdir(parents=True, exist_ok=True)

        # 运行任务流（同步调用，交给线程并发）
        try:
            self.graph.invoke(state, config)
            return module_name, "success", None
        except Exception as e:
            # 避免线程异常吞没
            tb = traceback.format_exc()
            with open(f"{module_name}_error.txt", "w", encoding="utf-8") as f:
                f.write(f"{e}\n{tb}")
            return module_name, "error", f"{e}\n{tb}"

    def running_dataset_concurrency(self, max_workers: int = 16):
        """
        并发运行 Verilog-eval 数据集。
        max_workers：并发线程数（建议根据 API 限流、机器性能与 Icarus/Vivado 并发承载设定）
        """
        data_list = self.get_data_files()
        results = []

        # 顺次地并行：读完整个列表，然后限流并发执行
        with ThreadPoolExecutor(max_workers=max_workers) as ex:
            future_map = {ex.submit(self.run_one_file, f): f for f in data_list}
            for fut in as_completed(future_map):
                module_name, status, detail = fut.result()
                if status == "success":
                    logger.info(f"[{module_name}] 完成")
                else:
                    logger.error(f"[{module_name}] 失败：{detail}")
                results.append((module_name, status, detail))

        # 汇总简单打印；如需写入统计文件可在此处处理
        ok = sum(1 for _, s, _ in results if s == "success")
        err = len(results) - ok
        print(f"并发完成：成功 {ok} 项，失败 {err} 项")

    def running_dataset_orderly(self):
        """ 顺序运行数据集，不并发 """
        data_list = self.get_data_files()
        for data_file in data_list:
            module_name, status, detail = self.run_one_file(data_file)
            if status == "success":
                logger.info(f"[{module_name}] 完成")
            else:
                logger.error(f"[{module_name}] 失败：{detail}")


if __name__ == "__main__":
    coder = Coder_Verilogeval(TaskType.spec_2_rtl, build_graph_for_verilogeval_without_memory)
    # coder.running_dataset_concurrency()
    coder.running_dataset_orderly()
    # with open("graph.png", "wb") as f:
    #     f.write(coder.graph.get_graph().draw_mermaid_png())
