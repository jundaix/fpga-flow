# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

import os
from dataclasses import dataclass, fields
from typing import Any, Optional

from langchain_core.runnables import RunnableConfig

# 自动生成构造函数 (__init__)、__repr__ 等常用方法
@dataclass(kw_only=True)        # kw_only=True强制所有参数必须以“关键字”方式传入，避免位置参数带来的歧义与出错风险
class Configuration:
    """ 声明可配置字段及其默认值 """

    max_plan_iterations: int = 1  # 最大规划迭代次数
    max_step_num: int = 3  # 单次规划最多步骤数
    mcp_settings: dict = None  # 用于存放动态加载工具或其他设置的字典

    @classmethod
    def from_runnable_config(
        cls, config: Optional[RunnableConfig] = None
    ) -> "Configuration":
        """ 通过RunnableConfig实例创建配置实例 """
        configurable = (
            config["configurable"] if config and "configurable" in config else {}       # 从传入的RunnableConfig中读取“configurable”字段信息
        )
        values: dict[str, Any] = {
            f.name: os.environ.get(f.name.upper(), configurable.get(f.name))    # 尝试读环境变量；若不存在，就从configurable字典里按同名小写键取值
            for f in fields(cls)
            if f.init                           # 返回所有字段定义，筛掉那些不参与初始化的字段（dataclass 上会标记某些辅助字段为 init=False）
        }
        return cls(**{k: v for k, v in values.items() if v})   # 排除值为空，None，0的环境变量值，并通过cls封装输出。**filtered会把字典里的键值对拆开，作为关键字参数传给构造函数
