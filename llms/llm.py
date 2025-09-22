# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

from pathlib import Path
from typing import Any, Dict

from langchain_openai import ChatOpenAI

from config import load_yaml_config
from config.agents import LLMType

# 保存llm实例的cache，其中键为llm类型，值为ChatOpenAI实例
_llm_cache: dict[LLMType, ChatOpenAI] = {}


def _create_llm_use_conf(llm_type: LLMType, conf: Dict[str, Any]) -> ChatOpenAI:
    """ 根据llm类型和配置信息生成llm实例 """
    # 定义一个映射表,把逻辑名称映射到配置字典中的相应区块。例如通过"reasoning"可以获得关于"REASONING_MODEL"的配置信息
    llm_type_map = {
        "reasoning": conf.get("REASONING_MODEL"),
        "basic": conf.get("BASIC_MODEL"),
        "advanced": conf.get("ADVANCED_MODEL"),
        "vision": conf.get("VISION_MODEL"),
    }
    # 获得llm的配置信息并保存
    llm_conf = llm_type_map.get(llm_type)
    # 验证是否存在llm配置以及这个配置的数据结构是否为字典
    if not llm_conf:
        raise ValueError(f"Unknown LLM type: {llm_type}")
    if not isinstance(llm_conf, dict):
        raise ValueError(f"Invalid LLM Conf: {llm_type}")
    # 把配置字典拆解成关键字参数，创建一个 langchain_openai.ChatOpenAI 客户端实例
    return ChatOpenAI(**llm_conf)


def get_llm_by_type(
    llm_type: LLMType,
) -> ChatOpenAI:
    """
    按类型获取 LLM 实例。如果_llm_cache存在已生成的对应的实例，则返回缓存实例。
    """
    if llm_type in _llm_cache:
        return _llm_cache[llm_type]
    # print("path:",str((Path(__file__).parent.parent)))
    conf = load_yaml_config(
        str((Path(__file__).parent.parent / "conf.yaml").resolve())         # 加载yaml配置文件，整理其中的配置信息（返回字典）
    )
    llm = _create_llm_use_conf(llm_type, conf)          # 根据配置信息和llm类型需求创建llm实例
    _llm_cache[llm_type] = llm                          # 保存llm实例
    return llm


# Initialize LLMs for different purposes - now these will be cached
basic_llm = get_llm_by_type("basic")

# In the future, we will use reasoning_llm and vl_llm for different purposes
# reasoning_llm = get_llm_by_type("reasoning")
# vl_llm = get_llm_by_type("vision")


if __name__ == "__main__":
    print(basic_llm.invoke("Hello"))
