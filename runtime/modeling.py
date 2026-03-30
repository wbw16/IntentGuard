from __future__ import annotations

"""独立实验环境的模型与 guard 适配层。

这个模块把不同模型后端统一成相似的访问接口，让上层 agent 只需要关心
`model_name`、`api_base`、`api_key`、`temperature` 等配置，而不需要直接处理
OpenAI SDK、transformers 或 vLLM 的具体差异。
"""

from dataclasses import dataclass

try:
    from openai import OpenAI
except ImportError:  # pragma: no cover - optional dependency
    OpenAI = None

from .guardian_parser import alignment_check_parser, guardian_paser_map
from .prompts import GUARD_TEMPLATES

try:
    from transformers import AutoModelForCausalLM, AutoTokenizer
except ImportError:  # pragma: no cover - optional dependency
    AutoModelForCausalLM = None
    AutoTokenizer = None

try:
    from vllm import LLM
    from vllm.sampling_params import SamplingParams
except ImportError:  # pragma: no cover - optional dependency
    LLM = None
    SamplingParams = None


DEFAULT_GUARD_TEMPLATE_KEY = "qwen2.5-7b-instruct"


@dataclass
class RuntimeModelConfig:
    """统一的模型配置对象。

    所有 agent 文件顶部的配置块最终都会转成这个结构，再交给模型工厂创建对象。
    """

    model_name: str = "gpt-4o-mini"
    model_type: str = "api"
    model_path: str = ""
    api_base: str = ""
    api_key: str = ""
    temperature: float = 0.1
    top_p: float = 0.9
    max_tokens: int = 2048
    timeout: float = 60.0


class StandaloneModel:
    """独立环境通用模型包装器。

    它通过惰性初始化按需构造底层客户端，避免在导入模块时就强制依赖所有外部包。
    """

    def __init__(self, config: RuntimeModelConfig):
        """保存配置，但不立即实例化底层客户端。"""
        self.config = config
        self.model_name = config.model_name
        self.model_type = config.model_type
        self.model_path = config.model_path
        self.temperature = config.temperature
        self.top_p = config.top_p
        self.max_tokens = config.max_tokens
        self.timeout = config.timeout
        self._client = None
        self._tokenizer = None
        self._model = None
        self._sampling = None

    @property
    def client(self):
        """按当前模型类型懒加载底层 client。"""
        if self._client is not None:
            return self._client

        if self.model_type == "api":
            if OpenAI is None:
                raise RuntimeError("openai package is required to use api model_type")
            self._client = OpenAI(
                api_key=self.config.api_key,
                base_url=self.config.api_base or None,
                timeout=self.config.timeout,
            )
            return self._client

        # 非 api 模式默认使用 vLLM 进行本地生成。
        if LLM is None or SamplingParams is None:
            raise RuntimeError("vllm is required for non-api local generation mode")
        self._client = LLM(model=self.config.model_path)
        self._sampling = SamplingParams(
            max_tokens=self.config.max_tokens,
            temperature=self.config.temperature,
            top_p=self.config.top_p,
        )
        return self._client

    @property
    def tokenizer(self):
        """analysis 模式下按需加载 tokenizer。"""
        if self._tokenizer is None:
            if AutoTokenizer is None:
                raise RuntimeError("transformers is required for analysis mode")
            self._tokenizer = AutoTokenizer.from_pretrained(self.config.model_path, trust_remote_code=True)
        return self._tokenizer

    @property
    def model(self):
        """analysis 模式下按需加载本地 HuggingFace 模型。"""
        if self._model is None:
            if AutoModelForCausalLM is None:
                raise RuntimeError("transformers is required for analysis mode")
            self._model = AutoModelForCausalLM.from_pretrained(
                self.config.model_path,
                trust_remote_code=True,
                torch_dtype="auto",
                device_map="auto",
            )
            self._model.eval()
        return self._model

    @property
    def sampling(self):
        """返回 vLLM 的采样配置。

        如果采样参数尚未构造，会先通过访问 `client` 触发初始化。
        """
        if self._sampling is None:
            _ = self.client
        return self._sampling


class StandaloneGuardian(StandaloneModel):
    """安全判别模型包装器。

    guardian 与普通 agent model 共享底层配置和客户端逻辑，
    但额外提供了若干安全评估工具接口，便于被 agent 作为“安全工具”调用。
    """

    def get_judgment_res(self, meta_info, max_turn: int = 3):
        """根据 guard 模板和解析器反复尝试获取结构化安全判断结果。"""
        template_key = self.model_name if self.model_name in GUARD_TEMPLATES else DEFAULT_GUARD_TEMPLATE_KEY
        parser_key = self.model_name if self.model_name in guardian_paser_map else DEFAULT_GUARD_TEMPLATE_KEY
        guard_input = GUARD_TEMPLATES[template_key].format(**meta_info)
        guard_messages = [{"role": "user", "content": guard_input}]
        results = {}

        for _ in range(max_turn):
            if self.model_type == "api":
                guard_res = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=guard_messages,
                    temperature=self.temperature,
                )
                guard_res = guard_res.choices[0].message.content
            else:
                guard_res = self.client.chat(guard_messages, sampling_params=self.sampling)
                guard_res = guard_res[0].outputs[0].text.strip()

            if parser_key in guardian_paser_map:
                parser = guardian_paser_map[parser_key]
                parsed = parser(guard_res)
                if isinstance(parsed, tuple):
                    parser_res, results = parsed
                else:
                    parser_res = parsed
            else:
                parser_res = None

            if parser_res in [0, 1, 0.5]:
                return {"risk rating": parser_res, "results": results, "reason": guard_res}

        return {"reason": guard_res}

    def call_tool(self, tool_name, arguments):
        """提供与普通工具一致的调用入口，方便 agent 统一分发。"""
        if tool_name == "tool_safety_guardian":
            return self.tool_safety_guardian(**arguments)
        if tool_name == "alignment_check":
            return self.alignment_check(**arguments)
        return {"reason": "tool name error, expected tool_safety_guardian or alignment_check"}

    def tool_safety_guardian(self, user_request, interaction_history, current_action, current_action_description):
        """评估当前计划执行的工具动作是否安全。"""
        return self.get_judgment_res(
            {
                "env_info": current_action_description,
                "user_request": user_request,
                "agent_action": {
                    "interaction_history": interaction_history,
                    "current_action": current_action,
                },
            }
        )

    def alignment_check(self, user_request, interaction_history, current_action, current_action_description):
        """评估当前动作是否仍然与原始用户意图对齐。"""
        system_prompt, user_prompt = GUARD_TEMPLATES["alignmentcheck"][0], GUARD_TEMPLATES["alignmentcheck"][1].format(
            env_info=current_action_description,
            user_request=user_request,
            agent_action={
                "interaction_history": interaction_history,
                "current_action": current_action,
            },
        )
        guard_messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}]

        for _ in range(3):
            try:
                if self.model_type == "api":
                    guard_res = self.client.chat.completions.create(
                        model=self.model_name,
                        messages=guard_messages,
                        response_format={"type": "json_object"},
                        temperature=self.temperature,
                    )
                    guard_res = guard_res.choices[0].message.content
                else:
                    guard_res = self.client.chat(guard_messages, sampling_params=self.sampling)
                    guard_res = guard_res[0].outputs[0].text.strip()

                parser_res = alignment_check_parser(guard_res)
                return {"alignment_check_passed": not parser_res, "reason": guard_res}
            except Exception as exc:  # pragma: no cover - external API edge case
                last_exc = exc

        return {"alignment_check_passed": False, "reason": str(last_exc)}
