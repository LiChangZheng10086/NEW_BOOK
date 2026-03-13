"""
新书代理 (New Book Agent) - 主入口
"""
from agent.book_agent import BookAgent
from config import Config


def main():
    config = Config()
    agent = BookAgent(config)
    agent.run()


if __name__ == "__main__":
    main()
