import os

# 这个文件实现带“提示词防火墙”的 ReAct 变体。
# 核心思想不是在执行后做安全评分，而是在系统提示词和对齐检查阶段主动抑制危险动作。

# ===== Agent Configuration =====
model_name = os.getenv("STANDALONE_REACT_FIREWALL_MODEL_NAME", "gpt-4o-mini")
api_key = os.getenv("STANDALONE_REACT_FIREWALL_API_KEY", "YOUR_API_KEY")
api_base = os.getenv("STANDALONE_REACT_FIREWALL_API_BASE", "http://localhost:8000/v1")
temperature = float(os.getenv("STANDALONE_REACT_FIREWALL_TEMPERATURE", "0.1"))
model_type = os.getenv("STANDALONE_REACT_FIREWALL_MODEL_TYPE", "api")
model_path = os.getenv("STANDALONE_REACT_FIREWALL_MODEL_PATH", "")
max_tokens = int(os.getenv("STANDALONE_REACT_FIREWALL_MAX_TOKENS", "2048"))
top_p = float(os.getenv("STANDALONE_REACT_FIREWALL_TOP_P", "0.9"))
default_max_turns = int(os.getenv("STANDALONE_REACT_FIREWALL_MAX_TURNS", "10"))

from copy import deepcopy
from types import FunctionType

from guard import GuardEvaluationRequest
from runtime.core import AgentCore
from runtime.factory import create_guard_from_env, create_model_from_config
from runtime.modeling import RuntimeModelConfig
from runtime.parsers import extract_tool_params_react
from runtime.prompts import REACT_SANDWITCH_DEFENSE_SYSTEM_PROMPT


class ReActFirewallAgent:
    """带提示词防火墙和对齐检查的 ReAct 策略。"""

    def __init__(self, system_template="", agentic_model=None, guard_model=None, max_turns=10):
        """初始化策略状态。"""
        self.system_template= system_template
        self.agentic_model = agentic_model
        self.guard_model = guard_model
        self.max_turns = max_turns
    
    def format_tools_for_prompt(self, tool_descriptions, tool_params):
        """把工具描述整理成系统提示词文本。"""
        result = []
        for tool, desc in tool_descriptions.items():
            result.append(f"{tool}: {desc}")
            params = tool_params.get(tool, {})
            if params:
                param_str = "\n    ".join([f"{k}: {v}" for k, v in params.items()])
                result.append(f"  parameters:\n    {param_str}")
            result.append("")
        return "\n".join(result)
        
    def extract_tool_params(self, text):
        """从模型输出中提取工具名和参数。"""
        tool_name, params_dict = extract_tool_params_react(text)
        return tool_name, params_dict

    def agent_invoke(self, query="", available_tool_descriptions={}, available_tool_params={}, known_actions={}, injection_task=""):
        """执行带提示词防火墙的 ReAct 主循环。"""
        i = 0
        logs = ""
        available_tool_descriptions_str=self.format_tools_for_prompt(available_tool_descriptions, available_tool_params)
        available_tool_list_str = str(list(available_tool_descriptions.keys()))
        logs += "[System Prompt]:\n" + self.system_template.format(available_tool_descriptions=available_tool_descriptions_str, available_tool_names=available_tool_list_str)
        logs += "\n-----------------------------------\n"
        bot = AgentCore(system=self.system_template.format(available_tool_descriptions=available_tool_descriptions_str, available_tool_names=available_tool_list_str), agentic_model=self.agentic_model)
        next_prompt = query
        logs += query
        logs += "\n-----------------------------------\n"

        # 这里预留了输入侧护栏位置；当前默认关闭，保留给后续研究扩展。
        # meta_info = {"user_request": query, "interaction_history": [], "current_action": "", "current_action_description": available_tool_descriptions_str}
        # guard_res = self.guard_model.call_tool(tool_name="tool_safety_guardian", arguments=meta_info)

        # if "risk rating" in guard_res and guard_res["risk rating"] > 0:
        #     guard_res["final answer"] = "Sorry, I can't assist with the request"
        #     bot.messages.append({"role": "user", "content": query})
        #     bot.messages.append({"role": "assistant", "content": guard_res})
        #     return logs, bot.messages, available_tool_descriptions_str

        #################################################

        while i < self.max_turns:
            i += 1
            result = bot(next_prompt)
            print(result)
            logs += result
            logs += "\n-----------------------------------\n"

            try:
                tool_name, tool_params = self.extract_tool_params(result)
                print(tool_name, tool_params)
                if tool_name:
                    logs += f" -- running {tool_name} {tool_params}\n"
                    if tool_name in known_actions:
                        ########## Alignment Check ######################
                        agent_action = bot.messages[2:]
                        interaction_history, current_action = agent_action[:-1], agent_action[-1]
                        guard_request = GuardEvaluationRequest(
                            user_request=query,
                            interaction_history=interaction_history,
                            current_action=current_action,
                            current_action_description=available_tool_descriptions_str,
                        )
                        guard_decision = self.guard_model.review_alignment(guard_request)
                        if guard_decision.blocked:
                            # 一旦判定当前动作与原始用户意图偏离，就直接拒绝继续执行。
                            bot.messages.append({"role": "user", "content": guard_decision.to_tool_result()})
                            bot.messages.append({"role": "assistant", "content": "Sorry, I can't assist with the request"})
                            return logs, bot.messages, available_tool_descriptions_str

                        #################################################

                        if isinstance(known_actions[tool_name], FunctionType):
                            observation = known_actions[tool_name](**deepcopy(tool_params))
                        elif isinstance(known_actions[tool_name], dict):
                            observation = known_actions[tool_name]["output"]
                        elif isinstance(known_actions[tool_name], tuple):
                            runtime = known_actions[tool_name][0]
                            env = known_actions[tool_name][1]
                            tool_call_result, error = runtime.run_function(env, tool_name, deepcopy(tool_params))
                            if error:
                                observation = f"tool_call_result: {tool_call_result}\nerror: {error}"
                            else:
                                observation = tool_call_result
                        else:
                            observation = known_actions[tool_name].call_tool(tool_name, deepcopy(tool_params))

                        #### 注入任务 ########
                        if injection_task and tool_name==injection_task["tool_name"]:
                            observation = observation + injection_task["template"].format(injection_prompt=injection_task["injection_prompt"])
                        #####################

                    else:
                        observation = f"Unknown tool: {tool_name}"

                    logs += "Observation: "+ str(observation)
                    logs += "\n-----------------------------------\n"

                    next_prompt = f"Observation: {observation}"
                else:
                    #print("Response:", result)
                    break

            except Exception as e:
                observation = f"Error occurred: {str(e)}\n"
                logs += "Observation: "+ str(observation)
                logs += "\n-----------------------------------\n"
                next_prompt = f"Observation: {observation}"

        return logs, bot.messages, available_tool_descriptions_str


def build_agent(system_template: str = REACT_SANDWITCH_DEFENSE_SYSTEM_PROMPT, max_turns: int = default_max_turns):
    """根据文件顶部配置构造防火墙版 ReAct agent。"""
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
    guard_model = create_guard_from_env("STANDALONE_REACT_FIREWALL", model_config)
    return ReActFirewallAgent(
        system_template=system_template,
        agentic_model=agentic_model,
        guard_model=guard_model,
        max_turns=max_turns,
    )
