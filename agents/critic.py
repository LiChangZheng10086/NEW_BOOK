"""
评论家 Agent - 负责审阅章节内容并提出修改建议
"""
import json
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from core.models import NovelSettings, ChapterContent, CriticFeedback
from config.prompts import CRITIC_SYSTEM, CRITIC_HUMAN
from config.settings import Settings
from core.logger import get_logger

logger = get_logger("CriticAgent")


class CriticAgent:
    def __init__(self, settings: Settings):
        self.llm = ChatOpenAI(
            model=settings.model,
            api_key=settings.deepseek_api_key,
            base_url=settings.deepseek_base_url,
            max_tokens=4096,
        )
        logger.info("CriticAgent 初始化完成，模型：%s", settings.model)

    def run(self, novel_settings: NovelSettings, chapter: ChapterContent, previous_chapter_content: str = "") -> CriticFeedback:
        """审阅章节内容"""
        logger.info(">>> [评论家Agent] 开始审阅第 %d 章：%s", chapter.chapter_number, chapter.title)
        settings_summary = f"""
标题：{novel_settings.title}
类型：{novel_settings.genre}
写作风格：{novel_settings.writing_style}
主要角色：{', '.join([c.name for c in novel_settings.characters])}
""".strip()

        previous_summary = (
            previous_chapter_content[-800:] if previous_chapter_content
            else "（本章为第一章，无上一章内容）"
        )

        human_content = CRITIC_HUMAN.format(
            novel_settings_summary=settings_summary,
            previous_chapter_summary=previous_summary,
            chapter_number=chapter.chapter_number,
            chapter_content=chapter.content,
        )

        messages = [
            SystemMessage(content=CRITIC_SYSTEM),
            HumanMessage(content=human_content),
        ]

        logger.info("正在调用 LLM 审阅第 %d 章...", chapter.chapter_number)
        response = self.llm.invoke(messages)
        logger.debug("LLM 原始返回：\n%s", response.content[:500])
        result = self._parse_response(response.content, chapter.chapter_number)
        logger.info("<<< [评论家Agent] 第 %d 章审阅完成，是否通过：%s，问题数：%d",
                    chapter.chapter_number, result.approved,
                    len(result.logic_issues) + len(result.style_issues) +
                    len(result.character_issues) + len(result.continuity_issues))
        if result.suggestions:
            logger.info("修改建议：%s", " | ".join(result.suggestions[:3]))
        return result

    def _parse_response(self, content: str, chapter_number: int) -> CriticFeedback:
        try:
            start = content.find("{")
            end = content.rfind("}") + 1
            if start != -1 and end > start:
                data = json.loads(content[start:end])
                return CriticFeedback.model_validate(data)
        except Exception as e:
            logger.warning("第 %d 章审阅 JSON 解析失败，使用兜底：%s", chapter_number, e)
        return CriticFeedback(
            chapter_number=chapter_number,
            suggestions=[content[:1000]],
            approved=False,
        )
