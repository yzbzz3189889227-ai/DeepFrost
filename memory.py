from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from typing import List

class SimpleWindowMemory(BaseChatMessageHistory):
    """滑动窗口记忆，同时兼容 save_context 调用"""
    def __init__(self, k: int = 5):
        self.k = k
        self._messages: List[BaseMessage] = []

    @property
    def messages(self) -> List[BaseMessage]:
        return self._messages

    @messages.setter
    def messages(self, value):
        self._messages = value[-self.k * 2:]

    def add_messages(self, messages: List[BaseMessage]) -> None:
        self._messages.extend(messages)
        if len(self._messages) > self.k * 2:
            self._messages = self._messages[-self.k * 2:]

    def clear(self) -> None:
        self._messages = []

    def save_context(self, input_data: dict, output_data: dict) -> None:
        """兼容 save_context，将字典转为 Human/AI 消息对"""
        human_msg = HumanMessage(content=str(input_data.get("input", "")))
        ai_msg = AIMessage(content=str(output_data.get("output", "")))
        self.add_messages([human_msg, ai_msg])

def create_agent_memory(k: int = 5) -> SimpleWindowMemory:
    return SimpleWindowMemory(k=k)