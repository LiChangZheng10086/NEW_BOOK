"""
作家大纲 Agent - 负责生成每章详细大纲
"""
import json
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from core.models import NovelSettings, ChapterOutline
from config.prompts import OUTLINE_WRITER_SYSTEM, OUTLINE_WRITER_HUMAN
from config.settings import Settings
from core.logger import get_logger

logger = get_logger("OutlineWriterAgent")


class OutlineWriterAgent:
    def __init__(self, settings: Settings):
        self.llm = ChatOpenAI(
            model=settings.model,
            api_key=settings.deepseek_api_key,
            base_url=settings.deepseek_base_url,
            max_tokens=4096,
        )
        logger.info("OutlineWriterAgent 初始化完成，模型：%s", settings.model)

    def run(self, novel_settings: NovelSettings, chapter_number: int, previous_ending: str = "") -> ChapterOutline:
        """为指定章节生成大纲"""
        logger.info(">>> [大纲Agent] 开始生成第 %d 章大纲", chapter_number)
        human_content = OUTLINE_WRITER_HUMAN.format(
            chapter_number=chapter_number,
            novel_settings=novel_settings.model_dump_json(indent=2),
            previous_ending=previous_ending or "（本章为第一章，无上一章）",
        )

        messages = [
            SystemMessage(content=OUTLINE_WRITER_SYSTEM),
            HumanMessage(content=human_content),
        ]

        logger.info("正在调用 LLM 生成第 %d 章大纲...", chapter_number)
        response = self.llm.invoke(messages)
        logger.debug("LLM 原始返回：\n%s", response.content[:500])
        result = self._parse_response(response.content, chapter_number)
        logger.info("<<< [大纲Agent] 第 %d 章大纲生成完成：%s，关键事件数：%d",
                    chapter_number, result.title, len(result.key_events))
        return result

    def run_all(self, novel_settings: NovelSettings, previous_endings: dict[int, str] = None) -> list[ChapterOutline]:
        """批量生成所有章节大纲"""
        logger.info(">>> [大纲Agent] 开始批量生成全部 %d 章大纲", novel_settings.target_chapters)
        outlines = []
        previous_endings = previous_endings or {}
        for i in range(1, novel_settings.target_chapters + 1):
            outline = self.run(novel_settings, i, previous_endings.get(i - 1, ""))
            outlines.append(outline)
        logger.info("<<< [大纲Agent] 全部大纲生成完成，共 %d 章", len(outlines))
        return outlines

    def _parse_response(self, content: str, chapter_number: int) -> ChapterOutline:
        try:
            start = content.find("{")
            end = content.rfind("}") + 1
            if start != -1 and end > start:
                data = json.loads(content[start:end])
                return ChapterOutline.model_validate(data)
        except Exception as e:
            logger.warning("第 %d 章大纲 JSON 解析失败，使用兜底：%s", chapter_number, e)
        return ChapterOutline(
            chapter_number=chapter_number,
            title=f"第{chapter_number}章",
            summary=content[:500],
            key_events=[],
            characters_involved=[],
        )
