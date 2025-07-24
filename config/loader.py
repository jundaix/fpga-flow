# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

import os
import yaml
from typing import Dict, Any


def replace_env_vars(value: str) -> str:
    """ 替换字符串值中的环境变量 """
    # 如果传入的值不是字符串，原样返回
    if not isinstance(value, str):
        return value
    # 如果字符串以$开头，就把$后面的部分当作环境变量名，通过os.getenv读取其值，
    if value.startswith("$"):
        env_var = value[1:]
        return os.getenv(env_var, value)    # 从当前进程的环境变量中读取名为env_var的项。如果该环境变量存在，就返回它对应的字符串值；如果不存在，则返回第二个参数 value 作为默认值
    # 其它情况下返回原值
    return value


def process_dict(config: Dict[str, Any]) -> Dict[str, Any]:
    """ 循环处理字典，保存其中的环境变量，将配置信息以字典的形式保存在python程序中 """
    result = {}
    for key, value in config.items():
        # 如果某个值又是一个子字典，就递归调用 process_dict
        if isinstance(value, dict):
            result[key] = process_dict(value)
        # 如果值是字符串，则调用replace_env_vars处理
        elif isinstance(value, str):
            result[key] = replace_env_vars(value)
        # 如果值是其余类型（数字、列表等），则原样保留
        else:
            result[key] = value
    return result

# 将运行过程中将刚加载并处理过的某个文件内容缓存起来，避免多次打开和解析同一文件。保存结构：{文件名: {配置名称: 配置值}}
_config_cache: Dict[str, Dict[str, Any]] = {}


def load_yaml_config(file_path: str) -> Dict[str, Any]:
    """ 加载yaml配置文件，处理其中的配置信息以适用于后续处理 """
    # 如果文件不存在，返回{}
    if not os.path.exists(file_path):
        print(f"文件不存在：{file_path}")
        return {}

    # 检查缓存中是否已存在配置
    if file_path in _config_cache:
        return _config_cache[file_path]

    # 如果缓存中不存在，则加载并处理配置
    with open(file_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)                  # 读取并解析整个YAML文件为Python对象，一般为字典
    processed_config = process_dict(config)

    # 将处理后的配置存入缓存
    _config_cache[file_path] = processed_config
    return processed_config
