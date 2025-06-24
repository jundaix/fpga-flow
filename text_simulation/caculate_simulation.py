from .embedding import embedding_model
from .cosine_similarity import cosine_similarity_np

def calculate_similarity(text_a: str, text_b: str) -> float:
    # 计算文本余弦值
    embedding_a = embedding_model.embed_query(text_a)
    embedding_b = embedding_model.embed_query(text_b)

    # 计算余弦相似度并返回
    return cosine_similarity_np(embedding_a, embedding_b)
