from text_simulation.caculate_simulation import calculate_similarity

def judge_same_code(code_a: str, code_b: str) -> bool:
    # 计算两代码相似度
    similarity = calculate_similarity(code_a, code_b)

    # 根据相似度大小返回判定结果
    if similarity > 0.85:
        return True
    else:
        return False
