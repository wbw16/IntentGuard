import os

# IntentGuard 策略智能体。
# 在 ReAct 循环中每步工具调用前提取结构化意图声明，
# 并将 IntentDeclaration 传递给护栏模块做交叉验证。

# ===== Agent Configuration =====
model_name = os.getenv("STANDALONE_INTENTGUARD_MODEL_NAME", "gpt-4o-mini")
api_key = os.getenv("STANDALONE_INTENTGUARD_API_KEY", "YOUR_API_KEY")
api_base = os.getenv("STANDALONE_INTENTGUARD_API_BASE", "http://localhost:8000/v1")
temperature = float(os.getenv("STANDALONE_INTENTGUARD_TEMPERATURE", "0.1"))
model_type = os.getenv("STANDALONE_INTENTGUARD_MODEL_TYPE", "api")
model_path = os.getenv("STANDALONE_INTENTGUARD_MODEL_PATH", "")
max_tokens = int(os.getenv("STANDALONE_INTENTGUARD_MAX_TOKENS", "2048"))
top_p = float(os.getenv("STANDALONE_INTENTGUARD_TOP_P", "0.9"))
default_max_turns = int(os.getenv("STANDALONE_INTENTGUARD_MAX_TURNS", "10"))

# ===== Guard Model Configuration =====
guard_model_name = os.getenv("STANDALONE_INTENTGUARD_GUARD_MODEL_NAME", "gpt-4o-mini")
guard_mode = os.getenv("STANDALONE_INTENTGUARD_GUARD_MODE", "cross_validate")  # cross_validate | passthrough

from types import FunctionType

from runtime.core import AgentCore
from runtime.factory import create_guard_from_env, create_model_from_config
from runtime.intent_schema import IntentDeclaration
from runtime.modeling import RuntimeModelConfig
from runtime.parsers import extract_intent, extract_tool_params_react
from runtime.prompts import INTENTGUARD_REACT_SYSTEM_PROMPT


class IntentGuard_Agent:
    """带结构化意图声明的 ReAct 策略。

    每步工具调用前：
    1. 从模型输出中提取 <intent> 块，解析为 IntentDeclaration
    2. 将意图传递给护栏模块（当前为占位接口，Phase 2 实现）
    3. 根据护栏决策决定是否执行工具
    """

    def __init__(self, system_template="", agentic_model=None, guard_model=None,
                 max_turns=10, guard_mode="cross_validate"):
        self.system_template = system_template
        self.agentic_model = agentic_model
        self.guard_model = guard_model
        self.max_turns = max_turns
        self.guard_mode = guard_mode

    def format_tools_for_prompt(self, tool_descriptions, tool_params):
        result = []
        for tool, desc in tool_descriptions.items():
            result.append(f"{tool}: {desc}")
            params = tool_params.get(tool, {})
            if params:
                param_str = "\n    ".join([f"{k}: {v}" for k, v in params.items()])
                result.append(f"  parameters:\n    {param_str}")
            result.append("")
        return "\n".join(result)

    def _evaluate_intent(self, intent: IntentDeclaration, tool_name: str,
                         tool_params: dict, query: str, history: list) -> tuple[bool, str]:
        """调用护栏模块评估意图。

        Phase 1 占位实现：仅做基础格式校验。
        Phase 2 将替换为完整的 GuardrailMiddleware.evaluate() 调用。

        Returns:
            (allowed, reason)
        """
        errors = intent.validate()
        if errors:
            return False, f"Intent validation failed: {'; '.join(errors)}"
        return True, "ok"

    def agent_invoke(self, query="", available_tool_descriptions={},
                     available_tool_params={}, known_actions={}, injection_task=""):
        """执行 IntentGuard ReAct 主循环。"""
        i = 0
        logs = ""
        intent_log: list[dict] = []

        available_tool_descriptions_str = self.format_tools_for_prompt(
            available_tool_descriptions, available_tool_params
        )
        available_tool_list_str = str(list(available_tool_descriptions.keys()))

        system_prompt = self.system_template.format(
            available_tool_descriptions=available_tool_descriptions_str,
            available_tool_names=available_tool_list_str,
        )
        logs += "[System Prompt]:\n" + system_prompt
        logs += "\n-----------------------------------\n"

        bot = AgentCore(system=system_prompt, agentic_model=self.agentic_model)
        next_prompt = query
        logs += query + "\n-----------------------------------\n"

        while i < self.max_turns:
            i += 1
            result = bot(next_prompt)
            print(result)
            logs += result + "\n-----------------------------------\n"

            try:
                tool_name, tool_params = extract_tool_params_react(result)
                if not tool_name:
                    break

                # 提取结构化意图
                intent = extract_intent(result)
                intent_log.append({
                    "turn": i,
                    "tool": tool_name,
                    "intent": intent.to_dict(),
                    "intent_valid": intent.is_valid,
                })
                print(f"[IntentGuard] Turn {i} intent: {intent.to_dict()}")

                logs += f" -- running {tool_name} {tool_params}\n"

                if tool_name not in known_actions:
                    observation = f"Unknown tool: {tool_name}"
                    logs += "Observation: " + str(observation) + "\n-----------------------------------\n"
                    next_prompt = f"Observation: {observation}"
                    continue

                # 护栏评估
                allowed, reason = self._evaluate_intent(
                    intent, tool_name, tool_params, query, bot.messages
                )
                if not allowed:
                    observation = (
                        f"IntentGuard blocked this action.\nReason: {reason}\n"
                        "Please reconsider your approach."
                    )
                    logs += f"[IntentGuard BLOCKED] {reason}\n"
                    logs += "Observation: " + observation + "\n-----------------------------------\n"
                    next_prompt = f"Observation: {observation}"
                    continue

                # 执行工具
                action_fn = known_actions[tool_name]
                if isinstance(action_fn, FunctionType):
                    observation = action_fn(**tool_params)
                elif hasattr(action_fn, "__call__"):
                    observation = action_fn(**tool_params)
                else:
                    observation = f"Unknown tool: {tool_name}"

                logs += "Observation: " + str(observation) + "\n-----------------------------------\n"
                next_prompt = f"Observation: {observation}"

            except Exception as e:
                observation = f"Error occurred: {str(e)}\n"
                logs += "Observation: " + str(observation) + "\n-----------------------------------\n"
                next_prompt = f"Observation: {observation}"

        return logs, bot.messages, available_tool_descriptions_str, intent_log


def build_agent(system_template: str = INTENTGUARD_REACT_SYSTEM_PROMPT,
                max_turns: int = default_max_turns):
    """根据文件顶部配置构造 IntentGuard agent。"""
    model_config = RuntimeModelConfig(
        model_name=model_name,
        model_type=model_type,
        model_path=model_path,
        api_base=api_base,
        api_key=api_key,
        temperature=temperature,
        max_tokens=max_tokens,
        top_p=top_p,
    )
    agentic_model = create_model_from_config(config=model_config)
    guard_model = create_guard_from_env("STANDALONE_INTENTGUARD", model_config)
    return IntentGuard_Agent(
        system_template=system_template,
        agentic_model=agentic_model,
        guard_model=guard_model,
        max_turns=max_turns,
        guard_mode=guard_mode,
    )
