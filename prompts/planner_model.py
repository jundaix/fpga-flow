# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

from enum import Enum
from typing import List, Optional
# BaseModel 是所有数据模型的基类，Field 用来给字段添加元数据
from pydantic import BaseModel, Field

# 枚举步骤类型，包含研究型和处理型
class StepType(str, Enum):
    RESEARCH = "research"
    PROCESSING = "processing"


class Step(BaseModel):
    need_web_search: bool = Field(
        ..., description="Must be explicitly set for each step"                         # 指明此步骤是否需要网络搜索
    )
    title: str                                                                          # 步骤标题
    description: str = Field(..., description="Specify exactly what data to collect")   # 描述要收集哪些数据
    step_type: StepType = Field(..., description="Indicates the nature of the step")    # 步骤类型（research或processing）
    execution_res: Optional[str] = Field(
        default=None, description="The Step execution result"                           # 存放步骤执行后的结果
    )


class Plan(BaseModel):
    locale: str = Field(
        ..., description="e.g. 'en-US' or 'zh-CN', based on the user's language"        # 语言/地区标识
    )
    has_enough_context: bool                                                            # 表明当前信息是否足够
    thought: str                                                                        # 模型“思考”文本，用于记录此计划背后的思路
    title: str                                                                          # 计划标题
    steps: List[Step] = Field(
        default_factory=list,
        description="Research & Processing steps to get more context",
    )

    class Config:                                                                       # 向生成的 JSON Schema 中注入示例，向模型提供参考
        json_schema_extra = {
            "examples": [
                {
                    "has_enough_context": False,
                    "thought": (
                        "To understand the current market trends in AI, we need to gather comprehensive information."
                    ),
                    "title": "AI Market Research Plan",
                    "steps": [
                        {
                            "need_web_search": True,
                            "title": "Current AI Market Analysis",
                            "description": (
                                "Collect data on market size, growth rates, major players, and investment trends in AI sector."
                            ),
                            "step_type": "research",
                        }
                    ],
                }
            ]
        }
