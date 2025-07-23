from graph.types import State, update_dict_value
from utils.vivado_operation import *

from langgraph.types import Command
from langchain_core.messages import AIMessage

import logging

logger = logging.getLogger(__name__)

def logic_test_node(state: State) -> Command:
    """ 该节点专门用于逻辑测试：原本处于tester内部的逻辑测试操作移至此处 """
    logger.info("Starting logic test...")

    project_name = state.get('project_name', state.get('module_name', 'unknown'))
    module_name = state.get('module_name', 'unknown')
    workspace_dir = Path(__file__).parent.parent / "workspace"
    testbench_file_path = workspace_dir.joinpath(project_name, f"{project_name}.srcs", "sim_1", "new", f"tb_{module_name}")

    # 先判定项目是否已经建立，则认为当前操作非法（未建立项目则不存在可以实例化的源码）
    if not judge_project_exit(project_name, workspace_dir):
        return Command(
            update={
                "additional_info_needed": f"Project '{project_name}' does not exist, meaning there is not the source code file.\nPlease check if the previous steps are completed!",
            }
        )

    # 执行逻辑验证
    logic_is_valid, logic_validation_message = validate_verilog_logic_vivado(project_name, workspace_dir, str(testbench_file_path))

    if logic_is_valid:
        logger.info(f"Testbench logic : {logic_validation_message}")

        return Command(
            update={
                "messages": [AIMessage(content=logic_validation_message, name="logic_test")],
                "additional_info_needed": "",
                "logic_result": True,
                "logic_message": logic_validation_message,
                "task_finished": update_dict_value(state, "task_finished", "logic_test", True),
            }
        )
    else:
        logger.warning(f"Testbench logic validation failed: {logic_validation_message}")
        return Command(
            update={
                "messages": [AIMessage(content=logic_validation_message, name="logic_test")],               # 设计函数从测试结果中提取出错误信息
                "additional_info_needed": "Unable to pass the testbench logic verification!",
                "logic_result": False,
                "logic_message": logic_validation_message,
                "task_finished": update_dict_value(state, "task_finished", "logic_test", False),
            }
        )