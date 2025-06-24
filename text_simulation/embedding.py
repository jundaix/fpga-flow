from langchain_openai import OpenAIEmbeddings
from config.loader import load_yaml_config
from pathlib import Path

def create_embedding_model() -> OpenAIEmbeddings:
    conf = load_yaml_config(
        str((Path(__file__).parent.parent / "conf.yaml").resolve())         # 加载yaml配置文件，整理其中的配置信息（返回字典）
    )

    # 提取嵌入模型相关配置
    embedding_conf = conf.get("EMBEDDING_MODEL")
    if not embedding_conf:
        raise ValueError("Embedding model configuration not found in the YAML file.")
    if not isinstance(embedding_conf, dict):
        raise ValueError("Invalid EMBEDDING_MODEL configuration format.")

    # 根据嵌入模型配置创建嵌入模型
    return OpenAIEmbeddings(**embedding_conf)


embedding_model = create_embedding_model()

__all__ = ["embedding_model"]

if __name__ == "__main__":
    vector = embedding_model.embed_query("Hello, world!")
    print(vector)
    print(len(vector))
    print(type(vector))