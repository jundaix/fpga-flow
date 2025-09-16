"""
分析 LLM 输出的 JSON 格式代码块，提取其中的 JSON 内容。
"""

import json
from typing import List, Union, Tuple

JsonType = Union[dict, list]

def _strip_code_fence(block: str) -> str:
    """
    去掉 ``` 代码块围栏及前缀的语言标记（如 'json', 'JSON', 'js' 等）。
    仅对完整的围栏块使用；不会修改块内部内容。
    """
    s = block.strip()
    if s.startswith("```") and s.endswith("```"):
        inner = s[3:-3]  # 去掉首尾 ```
        inner = inner.lstrip()  # 去掉左侧空白
        # 若首行是语言标记（如 'json'），去掉该行
        first_newline = inner.find("\n")
        if first_newline == -1:
            lang = inner.strip()
            if lang.lower() in {"json", "js", "javascript"}:
                return ""  # 只有语言标记，没有内容
            return inner
        lang = inner[:first_newline].strip()
        rest = inner[first_newline + 1 :]
        if lang.lower() in {"json", "js", "javascript"}:
            return rest
        # 不是语言标记，则整个内容保留
        return inner
    return block

def _find_fenced_code_blocks(text: str) -> List[str]:
    """
    找到所有三反引号 ``` 包裹的代码块，原样返回（含 ```）。
    """
    blocks = []
    i = 0
    n = len(text)
    while i < n:
        start = text.find("```", i)
        if start == -1:
            break
        end = text.find("```", start + 3)
        if end == -1:
            # 没有闭合，放弃这段
            break
        blocks.append(text[start : end + 3])
        i = end + 3
    return blocks

def _scan_balanced_json(text: str) -> List[str]:
    """
    逐字符扫描，提取所有顶层完整的 {...} 或 [...] 片段。
    能正确跳过字符串中的引号、转义与花括号/方括号。
    返回原始子串列表（不做任何清洗）。
    """
    snippets = []
    n = len(text)
    i = 0

    in_string = False
    string_quote = ''
    escape = False
    stack = []  # 存放期望的闭合符号，如 '}' 或 ']'
    start_idx = None

    while i < n:
        ch = text[i]

        if in_string:
            if escape:
                escape = False  # 当前字符被转义，直接跳过
            elif ch == "\\":
                escape = True
            elif ch == string_quote:
                in_string = False
        else:
            if ch in ('"', "'"):
                # 注意：JSON 标准只允许双引号，这里仅用于正确跳过字符串段，避免误匹配大括号
                in_string = True
                string_quote = ch
            elif ch == '{':
                if not stack:
                    start_idx = i
                stack.append('}')
            elif ch == '[':
                if not stack:
                    start_idx = i
                stack.append(']')
            elif ch == '}' or ch == ']':
                if stack and ch == stack[-1]:
                    stack.pop()
                    if not stack and start_idx is not None:
                        # 捕获一个完整 JSON 片段
                        snippets.append(text[start_idx : i + 1])
                        start_idx = None
                else:
                    # 不匹配，忽略（容错）
                    pass

        i += 1

    return snippets

def _escape_control_chars_in_strings(raw: str) -> str:
    """
    仅在 **字符串字面量内部** 将裸的换行/回车/制表替换为 JSON 合法的转义序列，
    不改变字符串外部（结构性）换行。
    """
    out_chars = []
    in_string = False
    quote = ''
    escape = False

    for ch in raw:
        if in_string:
            if escape:
                # 上一个是反斜杠，当前字符原样保留
                out_chars.append(ch)
                escape = False
            else:
                if ch == '\\':
                    out_chars.append(ch)
                    escape = True
                elif ch == quote:
                    # 字符串结束
                    out_chars.append(ch)
                    in_string = False
                    quote = ''
                elif ch == '\n':
                    out_chars.append('\\n')
                elif ch == '\r':
                    out_chars.append('\\r')
                elif ch == '\t':
                    out_chars.append('\\t')
                else:
                    out_chars.append(ch)
        else:
            # 不在字符串里，遇到引号进入字符串
            if ch == '"' or ch == "'":
                in_string = True
                quote = ch
                out_chars.append(ch)
            else:
                out_chars.append(ch)

    return ''.join(out_chars)

def extract_json_snippets(text: str) -> List[str]:
    """
    综合提取 JSON 片段：
    1) 优先提取所有 ``` fenced code blocks ```，并剥离围栏与语言标记；
    2) 对整段文本做一次平衡扫描，捕获 {…} 与 […] 顶层片段。
    去重后返回候选 JSON 字符串列表（仍需 json.loads）。
    """
    candidates: List[str] = []

    # 1) 代码围栏内的内容
    for block in _find_fenced_code_blocks(text):
        inner = _strip_code_fence(block)
        if inner.strip():
            candidates.append(inner.strip())

    # 2) 全文扫描捕获顶层 JSON
    for snip in _scan_balanced_json(text):
        candidates.append(snip.strip())

    # 去重，保持顺序
    seen = set()
    unique = []
    for c in candidates:
        if c not in seen:
            seen.add(c)
            unique.append(c)
    return unique

def parse_llm_json_all(text: str) -> List[JsonType]:
    """
    提取并解析所有 JSON 片段，成功解析的以 Python 对象（dict/list）返回。
    对无法解析者静默跳过（你也可以改成抛异常或记录日志）。
    """
    results: List[JsonType] = []
    for snip in extract_json_snippets(text):
        # 轻微清洗：有些模型会在 fenced block 里再包一层 ```，此处再保险去一次
        cleaned = _strip_code_fence(snip).strip()
        if not cleaned:
            continue
        try:
            obj = json.loads(cleaned)
            results.append(obj)
        except json.JSONDecodeError as e1:
            # 第一次失败：尝试“修复”字符串内的裸控制字符
            repaired = _escape_control_chars_in_strings(cleaned)
            try:
                obj = json.loads(repaired)
                results.append(obj)
                continue
            except json.JSONDecodeError as e2:
                print(f"解析 JSON 失败：{e1}；修复后仍失败：{e2}，原始文本：{cleaned}")
                continue
    return results

def parse_llm_json_first(text: str) -> Tuple[bool, JsonType]:
    """
    仅返回解析到的第一个 JSON。若未找到或均解析失败则返回 (False, None)。
    """
    all_objs = parse_llm_json_all(text)
    if not all_objs:
        return False, None
    return True, all_objs[0]
