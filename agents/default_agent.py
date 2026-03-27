import os

# 这个文件实现最轻量的默认 agent。
# 研究时如果只想验证“模型本身 + 基础消息流”的行为，而不想引入复杂工具循环，
# 可以从这个策略开始。

# ===== Agent Configuration =====
model_name = os.getenv("STANDALONE_DEFAULT_MODEL_NAME", "gpt-4o-mini")
api_key = os.getenv("STANDALONE_DEFAULT_API_KEY", "YOUR_API_KEY")
api_base = os.getenv("STANDALONE_DEFAULT_API_BASE", "http://localhost:8000/v1")
temperature = float(os.getenv("STANDALONE_DEFAULT_TEMPERATURE", "0.1"))
model_type = os.getenv("STANDALONE_DEFAULT_MODEL_TYPE", "api")
model_path = os.getenv("STANDALONE_DEFAULT_MODEL_PATH", "")
max_tokens = int(os.getenv("STANDALONE_DEFAULT_MAX_TOKENS", "2048"))
top_p = float(os.getenv("STANDALONE_DEFAULT_TOP_P", "0.9"))
guard_model_name = os.getenv("STANDALONE_DEFAULT_GUARD_MODEL_NAME", model_name)
guard_api_key = os.getenv("STANDALONE_DEFAULT_GUARD_API_KEY", api_key)
guard_api_base = os.getenv("STANDALONE_DEFAULT_GUARD_API_BASE", api_base)
guard_temperature = float(os.getenv("STANDALONE_DEFAULT_GUARD_TEMPERATURE", str(temperature)))
guard_model_type = os.getenv("STANDALONE_DEFAULT_GUARD_MODEL_TYPE", model_type)
guard_model_path = os.getenv("STANDALONE_DEFAULT_GUARD_MODEL_PATH", model_path)
default_max_turns = int(os.getenv("STANDALONE_DEFAULT_MAX_TURNS", "10"))

from copy import deepcopy

from standalone_agent_env.runtime.core import AgentCore
from standalone_agent_env.runtime.factory import create_guard_from_config, create_model_from_config


class Default_Agent:
    """最简单的消息执行封装。

    它不会主动组织复杂的工具推理流程，只负责把已有消息列表交给模型执行。
    """

    def __init__(self, system_template="", agentic_model=None, guard_model=None, max_turns=10):
        """保存运行所需的模型对象和基础配置。"""
        self.system_template= system_template
        self.agentic_model = agentic_model
        self.guard_model = guard_model
        self.max_turns = max_turns
    
    def agent_invoke(self, query="", available_tool_descriptions={}, available_tool_params={}, known_actions={}):
        """执行一次最基础的消息推理。

        这里约定 `query` 必须已经是完整的 message 列表，
        因此这个 agent 更适合做纯模型基线或自定义消息流实验。
        """
        assert isinstance(query, list), "`query` must be a list of messages"

        bot = AgentCore(agentic_model=self.agentic_model)
        # 直接复用外部传入的消息历史，而不是在这里再拼装工具提示词。
        bot.messages = deepcopy(query)

        response = bot.execute()
        bot.messages.append({ 'role': 'assistant', 'content': response })

        return [], bot.messages, ""


def build_agent(system_template: str = "", max_turns: int = default_max_turns):
    """根据文件顶部配置构造默认 agent。"""
    agentic_model = create_model_from_config(
        model_name=model_name,
        model_type=model_type,
        model_path=model_path,
        api_base=api_base,
        api_key=api_key,
        temperature=temperature,
        max_tokens=max_tokens,
        top_p=top_p,
    )
    guard_model = create_guard_from_config(
        model_name=guard_model_name,
        model_type=guard_model_type,
        model_path=guard_model_path,
        api_base=guard_api_base,
        api_key=guard_api_key,
        temperature=guard_temperature,
        max_tokens=max_tokens,
        top_p=top_p,
    )
    return Default_Agent(
        system_template=system_template,
        agentic_model=agentic_model,
        guard_model=guard_model,
        max_turns=max_turns,
    )
