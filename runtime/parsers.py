from __future__ import annotations

"""工具调用解析器。

不同 agent 策略输出的工具调用格式不完全一样，这里提供统一的解析函数，
把模型文本输出转成 `(tool_name, params_dict)` 这种更容易执行的结构。
"""

import json
import re

from runtime.intent_schema import IntentDeclaration, get_fallback_config


def extract_intent(text: str) -> IntentDeclaration:
    """从模型输出中提取 <intent> 块并解析为 IntentDeclaration。

    格式示例：
        <intent>
        action_type: read
        target_object: file
        ...
        </intent>

    解析失败时根据 fallback 配置决定行为，返回保守的 fallback 意图。
    """
    match = re.search(r"<intent>(.*?)</intent>", text, re.S)
    if not match:
        fb = get_fallback_config()
        if fb.get("on_missing_intent", "warn") != "allow":
            return IntentDeclaration.make_fallback(raw_text=text)
        return IntentDeclaration()

    raw = match.group(1).strip()
    data: dict = {}
    for line in raw.splitlines():
        line = line.strip()
        if not line or ":" not in line:
            continue
        key, _, val = line.partition(":")
        key = key.strip()
        val = val.strip()
        data[key] = val

    try:
        intent = IntentDeclaration.from_dict(data)
        intent.raw_text = raw
        errors = intent.validate()
        if errors:
            fb = get_fallback_config()
            if fb.get("on_invalid_format", "warn") != "allow":
                fallback = IntentDeclaration.make_fallback(raw_text=raw)
                return fallback
        return intent
    except Exception:
        return IntentDeclaration.make_fallback(raw_text=raw)


def extract_tool_params_react(text: str):
    """从 ReAct 风格文本中提取工具名和 JSON 参数。"""
    text = str(text)
    text = re.sub(r"```json", "", text)
    pattern = r"Action:\s*(\w+)[\s\S]*?Action Input:\s*(\{.*\})"
    match = re.search(pattern, text, re.S)
    if not match:
        return "", {}

    tool_name = match.group(1).strip()
    raw_params = match.group(2).strip()
    try:
        raw_params_clean = raw_params.strip().rstrip(".").strip("`")
        params_dict = json.loads(raw_params_clean)
        if isinstance(params_dict, dict):
            return tool_name, params_dict
    except json.JSONDecodeError:
        pass

    params_dict = {}
    pairs = re.findall(r'(\w+)\s*=\s*["\']?([^,"\']+)["\']?', raw_params)
    for key, value in pairs:
        params_dict[key] = value.strip()
    return tool_name, params_dict


def extract_tool_params_planexecute(tool_call):
    """从 Plan-Execute 风格的字典或 JSON 字符串中提取工具调用信息。"""
    if isinstance(tool_call, str):
        try:
            tool_call = json.loads(tool_call)
        except json.JSONDecodeError:
            return "", {}

    if not isinstance(tool_call, dict):
        return "", {}

    if "function_name" not in tool_call and "args" not in tool_call:
        return "", {}
    if "function_name" not in tool_call:
        return "", tool_call.get("args", {})
    if "args" not in tool_call:
        return tool_call.get("function_name", ""), {}
    return tool_call.get("function_name", ""), tool_call.get("args", {})


tool_extractor = {
    # 这里维护"策略名 -> 解析函数"的映射，方便上层按策略动态选择解析器。
    "react": extract_tool_params_react,
    "react_firewall": extract_tool_params_react,
    "plan_and_execute": extract_tool_params_planexecute,
    "sec_react": extract_tool_params_react,
    "intentguard": extract_tool_params_react,
}
