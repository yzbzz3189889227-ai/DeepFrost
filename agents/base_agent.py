from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, SystemMessage
from typing import List
from config import DEEPSEEK_BASE_URL, DEEPSEEK_API_KEY, DEEPSEEK_MODEL
from memory import create_agent_memory
from utils.logger import logger
import json

class BaseToolCallingAgent:
    """基于 OpenAI Function Calling 的智能体基类（兼容 DeepSeek）"""

    def __init__(self, name: str, role: str, tools: List, max_iterations: int = 12, verbose: bool = True):
        self.name = name
        self.role = role
        self.tools = tools
        self.max_iterations = max_iterations
        self.verbose = verbose

        self.llm = ChatOpenAI(
            model=DEEPSEEK_MODEL,
            openai_api_key=DEEPSEEK_API_KEY,
            openai_api_base=DEEPSEEK_BASE_URL,
            temperature=0.0,
        )
        self.llm_with_tools = self.llm.bind_tools(tools)
        self.memory = create_agent_memory(k=5)
        self.tool_map = {tool.name: tool for tool in tools}

    def run(self, user_input: str) -> str:
        logger.info(f"\n{'='*40}\n{self.name} 开始任务\n{'='*40}")
        logger.info(f"任务内容：{user_input}")

        system_msg = SystemMessage(content=self.role)
        history = self.memory.messages
        human_msg = HumanMessage(content=user_input)

        messages = [system_msg] + history + [human_msg]

        iteration = 0
        final_answer = ""

        while iteration < self.max_iterations:
            iteration += 1
            try:
                response = self.llm_with_tools.invoke(messages)
            except Exception as e:
                logger.error(f"LLM 调用失败：{e}")
                break

            if response.content and not response.tool_calls:
                final_answer = response.content
                self.memory.add_messages([human_msg, AIMessage(content=final_answer)])
                break

            if response.tool_calls:
                messages.append(AIMessage(content=response.content, tool_calls=response.tool_calls))

                for tool_call in response.tool_calls:
                    tool_name = tool_call["name"]
                    tool_args = tool_call["args"]

                    logger.info(f"[思考] 调用工具：{tool_name}")
                    logger.info(f"[行动] 工具参数：{json.dumps(tool_args, ensure_ascii=False)}")

                    tool_func = self.tool_map.get(tool_name)
                    if tool_func:
                        try:
                            observation = tool_func.invoke(tool_args)
                            logger.info(f"[观察] 工具返回：{observation}")
                        except Exception as e:
                            observation = f"工具执行错误：{e}"
                            logger.error(observation)
                    else:
                        observation = f"工具 {tool_name} 不存在"
                        logger.warning(observation)

                    messages.append(ToolMessage(content=str(observation), tool_call_id=tool_call["id"]))
                continue
            break

        if not final_answer:
            final_answer = "抱歉，我无法完成当前任务。"
            logger.warning(f"{self.name} 达到最大迭代次数，强制结束")

        logger.info(f"最终输出：{final_answer}")
        logger.info(f"{'='*40}\n{self.name} 结束任务\n{'='*40}")
        return final_answer
