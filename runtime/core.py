from __future__ import annotations

"""共享的 agent 执行核心。

这个模块负责把“消息列表 -> 模型调用 -> 结果回填”这条最基础的执行链
抽象成一个可复用对象，避免每个 agent 策略都自己维护一套消息循环。
"""

from typing import Any, Optional

try:
    import numpy as np
except ImportError:  # pragma: no cover - optional dependency
    np = None

try:
    import torch
except ImportError:  # pragma: no cover - optional dependency
    torch = None


def token_entropy(logits):
    """计算单步 token 分布的熵值。

    仅在 analysis 模式下使用，用于记录模型在生成过程中的不确定性。
    """
    if torch is None:
        raise RuntimeError("torch is required for analysis mode entropy calculation")

    log_probs = torch.nn.functional.log_softmax(logits, dim=-1)
    probs = torch.exp(log_probs)
    entropy = -(probs * log_probs).sum(dim=-1)
    entropy = torch.where(torch.isnan(entropy), torch.zeros_like(entropy), entropy)
    return entropy


class AgentCore:
    """独立实验环境里最小可复用的对话执行器。

    它只关心三件事：
    1. 保存消息历史；
    2. 调用底层模型对象；
    3. 把模型输出追加回消息列表。
    """

    def __init__(self, system: str = "", agentic_model: Optional[Any] = None):
        """初始化执行器。

        Args:
            system: 可选的系统提示词；如果存在，会作为第一条 system message 放入消息历史。
            agentic_model: 已经构造好的模型对象，通常由 runtime/factory.py 创建。
        """
        self.system = system
        self.messages = []
        self.agentic_model = agentic_model

        if self.system:
            self.messages.append({"role": "system", "content": system})

    def __call__(self, message: str, json_format: bool = False) -> str:
        """向执行器追加一条用户消息并立即执行。

        如果当前最后一条消息刚好就是相同的 user message，则直接复用现有消息历史执行，
        避免重复插入一条完全相同的输入。
        """
        if self.messages and self.messages[-1]["role"] == "user" and self.messages[-1]["content"] == message:
            result = self.execute(json_format=json_format)
            self.messages.append({"role": "assistant", "content": result})
            return result

        self.messages.append({"role": "user", "content": message})
        result = self.execute(json_format=json_format)
        self.messages.append({"role": "assistant", "content": result})
        return result

    def execute(self, json_format: bool = False) -> str:
        """按照当前模型类型执行一次推理。

        当前支持三种路径：
        - `api`：走 OpenAI 兼容接口；
        - `analysis`：走 transformers 本地模型并记录熵值；
        - 其它值：按 vLLM 风格本地生成处理。
        """
        if self.agentic_model is None:
            raise ValueError("agentic_model is required before AgentCore can execute")

        if self.agentic_model.model_type == "api":
            # API 模式下直接把现有消息历史转成 chat completion 请求。
            request = {
                "model": self.agentic_model.model_name,
                "messages": self.messages,
                "temperature": self.agentic_model.temperature,
            }
            if json_format:
                request["response_format"] = {"type": "json_object"}
            response = self.agentic_model.client.chat.completions.create(**request)
            return response.choices[0].message.content

        if self.agentic_model.model_type == "analysis":
            # analysis 模式主要用于本地分析型实验：
            # 一边生成答案，一边记录每一步生成时的 token 熵。
            if torch is None or np is None:
                raise RuntimeError("analysis mode requires both torch and numpy")

            inputs = self.agentic_model.tokenizer.apply_chat_template(
                self.messages,
                tokenize=False,
                add_generation_prompt=True,
            )
            model_inputs = self.agentic_model.tokenizer(inputs, return_tensors="pt").to(self.agentic_model.model.device)
            outputs = self.agentic_model.model.generate(
                **model_inputs,
                max_new_tokens=self.agentic_model.max_tokens,
                do_sample=False,
                return_dict_in_generate=True,
                output_scores=True,
            )
            response = self.agentic_model.tokenizer.decode(
                outputs.sequences[0][model_inputs["input_ids"].shape[-1] :],
                skip_special_tokens=True,
            ).strip()

            entropies = []
            for step_logits in outputs.scores:
                entropy = token_entropy(step_logits)
                entropies.append(entropy.item())

            entropies_np = np.array(entropies)
            self.last_entropies = entropies
            self.last_entropy_stats = {
                "mean": float(entropies_np.mean()) if len(entropies_np) > 0 else 0.0,
                "length": len(entropies_np),
            }
            return response

        # 其余情况默认视为本地生成接口，例如 vLLM 风格模型。
        response = self.agentic_model.client.chat(
            self.messages,
            sampling_params=self.agentic_model.sampling,
        )
        return response[0].outputs[0].text.strip()
