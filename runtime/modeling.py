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

from guard import GuardConfig, GuardDecision, GuardEvaluationRequest, GuardSubsystem


class StandaloneGuardian(GuardSubsystem):
    """Backward-compatible runtime wrapper around the dedicated Guard subsystem."""

    def __init__(self, config: RuntimeModelConfig):
        super().__init__(GuardConfig.from_model_config(config))
