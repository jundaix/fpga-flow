"""
    用于设置环境变量，使运行本地 langfuse 时绕过代理
"""
import os

def bypass_proxy_for_localhost():
    # 强制不使用代理
    for k in ("HTTP_PROXY","HTTPS_PROXY","http_proxy","https_proxy"):
        os.environ.pop(k, None)

    # 指定不走代理的直连名单
    no_proxy = "localhost,127.0.0.1,::1,host.docker.internal"
    # 追加已有的 NO_PROXY
    os.environ["NO_PROXY"] = (no_proxy if "NO_PROXY" not in os.environ
                              else os.environ["NO_PROXY"] + "," + no_proxy)
    os.environ["no_proxy"] = os.environ["NO_PROXY"]  # 兼容小写

