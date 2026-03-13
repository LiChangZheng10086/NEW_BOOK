"""
作家详细章节 Agent - 负责撰写章节正文
"""
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from core.models import NovelSettings, ChapterOutline, ChapterContent, CriticFeedback
from config.prompts import CHAPTER_WRITER_SYSTEM, CHAPTER_WRITER_HUMAN, CHAPTER_WRITER_REVISION_HUMAN
from config.settings import Settings
from core.logger import get_logger

logger = get_logger("ChapterWriterAgent")


class ChapterWriterAgent:
    def __init__(self, settings: Settings):
        self.llm = ChatOpenAI(
            model=settings.model,
            api_key=settings.deepseek_api_key,
            base_url=settings.deepseek_base_url,
            max_tokens=8192,
        )
        logger.info("ChapterWriterAgent 初始化完成，模型：%s", settings.model)

    def run(self, novel_settings: NovelSettings, outline: ChapterOutline, previous_ending: str = "") -> ChapterContent:
        """根据大纲撰写章节正文"""
        logger.info(">>> [章节Agent] 开始撰写第 %d 章：%s", outline.chapter_number, outline.title)
        characters_summary = "\n".join(
            [f"- {c.name}（{c.role}）：{c.personality}" for c in novel_settings.characters]
        )
        foreshadowing_summary = "\n".join(
            [f"- {f.description}（第{f.appear_chapter}章出现，第{f.resolve_chapter}章收尾）"
             for f in novel_settings.foreshadowings
             if f.appear_chapter <= outline.chapter_number <= f.resolve_chapter]
        )

        human_content = CHAPTER_WRITER_HUMAN.format(
            chapter_number=outline.chapter_number,
            genre=novel_settings.genre,
            writing_style=novel_settings.writing_style,
            world_setting_summary=novel_settings.world_setting[:500],
            characters_summary=characters_summary or "暂无角色信息",
            foreshadowing_summary=foreshadowing_summary or "本章无特定伏笔",
            chapter_outline=outline.model_dump_json(indent=2),
            previous_ending=previous_ending[-500:] if previous_ending else "（本章为第一章）",
        )

        messages = [
            SystemMessage(content=CHAPTER_WRITER_SYSTEM),
            HumanMessage(content=human_content),
        ]

        logger.info("正在调用 LLM 撰写第 %d 章正文...", outline.chapter_number)
        response = self.llm.invoke(messages)
        content = response.content
        logger.info("<<< [章节Agent] 第 %d 章撰写完成，字数：%d", outline.chapter_number, len(content))
        logger.debug("章节内容预览（前200字）：\n%s", content[:200])

        return ChapterContent(
            chapter_number=outline.chapter_number,
            title=outline.title,
            content=content,
            word_count=len(content),
            status="draft",
        )

    def revise(self, chapter: ChapterContent, feedback: CriticFeedback) -> ChapterContent:
        """根据评论家反馈修改章节"""
        logger.info(">>> [章节Agent] 开始修改第 %d 章（根据评论家反馈）", chapter.chapter_number)
        suggestions = "\n".join([f"- {s}" for s in feedback.suggestions])
        issues = "\n".join(
            feedback.logic_issues + feedback.style_issues +
            feedback.character_issues + feedback.continuity_issues
        )
        logger.debug("修改建议：\n%s", suggestions)

        human_content = CHAPTER_WRITER_REVISION_HUMAN.format(
            chapter_number=chapter.chapter_number,
            original_content=chapter.content,
            critic_feedback=f"问题：\n{issues}\n\n修改建议：\n{suggestions}",
        )

        messages = [
            SystemMessage(content=CHAPTER_WRITER_SYSTEM),
            HumanMessage(content=human_content),
        ]

        logger.info("正在调用 LLM 修改第 %d 章...", chapter.chapter_number)
        response = self.llm.invoke(messages)
        content = response.content
        logger.info("<<< [章节Agent] 第 %d 章修改完成，字数：%d", chapter.chapter_number, len(content))

        return ChapterContent(
            chapter_number=chapter.chapter_number,
            title=chapter.title,
            content=content,
            word_count=len(content),
            status="revised",
        )
