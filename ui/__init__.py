"""FPGA工作流程UI模块

这个包包含了FPGA智能开发工作流程的Streamlit用户界面实现。
采用松耦合的架构设计，将业务逻辑、UI状态管理和UI组件分离。

模块结构：
- workflow_manager: 工作流程管理器，负责FPGA开发流程的执行
- ui_state_manager: UI状态管理器，负责Streamlit会话状态管理
- ui_components: UI组件管理器，负责UI界面的渲染
- fpga_workflow_app_refactored: 重构后的主应用文件
- fpga_workflow_app: 原始的单体应用文件（保留作为参考）
"""

__version__ = "2.0.0"
__author__ = "FPGA Development Team"

from .workflow_manager import StreamlitFPGAWorkflow
from .ui_state_manager import UIStateManager
from .ui_components import UIComponents

__all__ = [
    "StreamlitFPGAWorkflow",
    "UIStateManager", 
    "UIComponents"
]