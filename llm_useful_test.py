from llms.llm import get_llm_by_type

# LLMType = Literal["basic", "advanced", "reasoning", "vision"]

def llm_useful_test():
    llm_model = get_llm_by_type("advanced")
    try:
        response = llm_model.invoke("请介绍一下你自己")
        print(response.content)
    except Exception as e:
        print(f"调用LLM模型失败: {e}")


if __name__ == "__main__":
    llm_useful_test()