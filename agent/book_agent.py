"""
书籍代理核心逻辑
"""
import anthropic
from config import Config


class BookAgent:
    def __init__(self, config: Config):
        self.config = config
        self.client = anthropic.Anthropic(api_key=config.anthropic_api_key)
        self.tools = []
        self.messages = []

    def run(self):
        print("Book Agent 启动...")
        while True:
            user_input = input("\n你: ").strip()
            if user_input.lower() in ("exit", "quit", "q"):
                break
            response = self.chat(user_input)
            print(f"\nAgent: {response}")

    def chat(self, user_message: str) -> str:
        self.messages.append({"role": "user", "content": user_message})
        response = self.client.messages.create(
            model=self.config.model,
            max_tokens=4096,
            system="你是一个专业的书籍创作助手，帮助用户规划、撰写和完善书籍内容。",
            messages=self.messages,
            tools=self.tools if self.tools else anthropic.NOT_GIVEN,
        )
        assistant_message = response.content[0].text
        self.messages.append({"role": "assistant", "content": assistant_message})
        return assistant_message
