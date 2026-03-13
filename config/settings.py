"""
配置管理
"""
import os
from dataclasses import dataclass, field
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Settings:
    deepseek_api_key: str = field(default_factory=lambda: os.getenv("DEEPSEEK_API_KEY", ""))
    tavily_api_key: str = field(default_factory=lambda: os.getenv("TAVILY_API_KEY", ""))
    model: str = "deepseek-reasoner"
    deepseek_base_url: str = "https://api.deepseek.com"
    chroma_db_dir: str = "./chroma_db"
    max_critic_iterations: int = 2  # 评论家最多迭代次数
