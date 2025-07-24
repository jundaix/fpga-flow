import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from langfuse import get_client
from langfuse.langchain import CallbackHandler

from config import load_yaml_config

from pathlib import Path
import logging
import enum


logger = logging.getLogger(__name__)

class LangfuseServerSelection(enum.Enum):
    Local = "LANGFUSE_LOCAL"
    Remote = "LANGFUSE"

def initial_langfuse_config(server_selection = LangfuseServerSelection.Local) -> None:
    """ 用于从 config 文件中读取 langfuse 的配置信息，初始化 langfuse 的环境配置 """
    config_path = Path(__file__).parent.parent / "conf.yaml"
    conf = load_yaml_config(config_path)

    if server_selection == LangfuseServerSelection.Remote:
        langfuse_conf = conf.get("LANGFUSE", {})
    else:
        langfuse_conf = conf.get("LANGFUSE_LOCAL", {})

    if not langfuse_conf:
        logger.warning("Configuration reading exception! Langfuse configuration information is empty!")
        return

    # 将读取到的配置加载到程序的环境变量中
    os.environ["LANGFUSE_PUBLIC_KEY"] = langfuse_conf["public_key"]
    os.environ["LANGFUSE_SECRET_KEY"] = langfuse_conf["secret_key"]
    os.environ["LANGFUSE_HOST"] = langfuse_conf["host"]
    return


def test_connect_2_langfuse() -> bool:
    """ 测试连接到 langfuse """
    try:
        client = get_client()
        if client.auth_check():
           logger.info("Langfuse connection SUCCESS!")
           return True
        else:
            logger.warning("Langfuse connection FAILED! Agent monitoring MISSING!")
            return False
    except Exception as e:
        logger.error(f"FAILS to connect Langfuse: {e}")
        return False


def langfuse_callback_handler() -> CallbackHandler:
    return CallbackHandler()


if __name__ == "__main__":
    initial_langfuse_config()
