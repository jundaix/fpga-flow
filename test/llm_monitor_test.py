from llm_monitor import test_connect_2_langfuse, initial_langfuse_config, bypass_proxy_for_localhost

if __name__ == "__main__":
    bypass_proxy_for_localhost()
    initial_langfuse_config()
    print(f"连接测试结果: {test_connect_2_langfuse()}")
    