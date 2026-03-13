"""
LangGraph 工作流定义 - 多 Agent 协作编排
"""
from typing import TypedDict, Optional, Annotated
from langgraph.graph import StateGraph, END
from core.models import NovelSettings, ChapterOutline, ChapterContent, CriticFeedback
from core.database import NovelDatabase
from agents.planner import PlannerAgent
from agents.outline_writer import OutlineWriterAgent
from agents.chapter_writer import ChapterWriterAgent
from agents.critic import CriticAgent
from config.settings import Settings


class NovelState(TypedDict):
    # 输入
    user_input: dict
    # 设定阶段
    novel_settings: Optional[NovelSettings]
    settings_confirmed: bool
    # 大纲阶段
    chapter_outlines: list[ChapterOutline]
    current_chapter: int
    outlines_confirmed: bool
    # 写作阶段
    chapter_contents: list[ChapterContent]
    current_content: Optional[ChapterContent]
    # 评审阶段
    critic_feedback: Optional[CriticFeedback]
    critic_iterations: int
    # 流程控制
    error: Optional[str]


class NovelWorkflow:
    def __init__(self, settings: Settings, db: NovelDatabase):
        self.settings = settings
        self.db = db
        self.planner = PlannerAgent(settings)
        self.outline_writer = OutlineWriterAgent(settings)
        self.chapter_writer = ChapterWriterAgent(settings)
        self.critic = CriticAgent(settings)
        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        graph = StateGraph(NovelState)

        graph.add_node("plan", self._plan_node)
        graph.add_node("write_outline", self._write_outline_node)
        graph.add_node("write_chapter", self._write_chapter_node)
        graph.add_node("review_chapter", self._review_chapter_node)
        graph.add_node("save_chapter", self._save_chapter_node)

        graph.set_entry_point("plan")
        graph.add_edge("plan", "write_outline")
        graph.add_edge("write_outline", "write_chapter")
        graph.add_edge("write_chapter", "review_chapter")
        graph.add_conditional_edges(
            "review_chapter",
            self._should_revise,
            {"revise": "write_chapter", "save": "save_chapter"},
        )
        graph.add_conditional_edges(
            "save_chapter",
            self._has_more_chapters,
            {"next": "write_outline", "done": END},
        )

        return graph.compile()

    def _plan_node(self, state: NovelState) -> NovelState:
        settings = self.planner.run(state["user_input"])
        return {**state, "novel_settings": settings}

    def _write_outline_node(self, state: NovelState) -> NovelState:
        chapter_num = state.get("current_chapter", 1)
        previous_ending = ""
        if chapter_num > 1 and state.get("chapter_contents"):
            last = state["chapter_contents"][-1]
            previous_ending = last.content[-500:]

        outline = self.outline_writer.run(state["novel_settings"], chapter_num, previous_ending)
        outlines = state.get("chapter_outlines", [])
        outlines.append(outline)
        return {**state, "chapter_outlines": outlines, "critic_iterations": 0}

    def _write_chapter_node(self, state: NovelState) -> NovelState:
        chapter_num = state.get("current_chapter", 1)
        outline = state["chapter_outlines"][-1]
        previous_ending = ""
        if state.get("chapter_contents"):
            previous_ending = state["chapter_contents"][-1].content[-500:]

        # 若是修改，传入评论家反馈
        feedback = state.get("critic_feedback")
        if feedback and state.get("current_content"):
            content = self.chapter_writer.revise(state["current_content"], feedback)
        else:
            content = self.chapter_writer.run(state["novel_settings"], outline, previous_ending)

        return {**state, "current_content": content, "critic_feedback": None}

    def _review_chapter_node(self, state: NovelState) -> NovelState:
        previous_content = ""
        if state.get("chapter_contents"):
            previous_content = state["chapter_contents"][-1].content

        feedback = self.critic.run(
            state["novel_settings"],
            state["current_content"],
            previous_content,
        )
        iterations = state.get("critic_iterations", 0) + 1
        return {**state, "critic_feedback": feedback, "critic_iterations": iterations}

    def _save_chapter_node(self, state: NovelState) -> NovelState:
        chapter = state["current_content"]
        chapter.status = "confirmed"
        self.db.save_chapter_content(chapter, state["novel_settings"].title)

        contents = state.get("chapter_contents", [])
        contents.append(chapter)
        next_chapter = state.get("current_chapter", 1) + 1
        return {**state, "chapter_contents": contents, "current_chapter": next_chapter, "current_content": None}

    def _should_revise(self, state: NovelState) -> str:
        feedback = state.get("critic_feedback")
        iterations = state.get("critic_iterations", 0)
        max_iter = self.settings.max_critic_iterations
        if feedback and not feedback.approved and iterations < max_iter:
            return "revise"
        return "save"

    def _has_more_chapters(self, state: NovelState) -> str:
        current = state.get("current_chapter", 1)
        total = state["novel_settings"].target_chapters
        return "next" if current <= total else "done"

    def run(self, user_input: dict) -> NovelState:
        initial_state = NovelState(
            user_input=user_input,
            novel_settings=None,
            settings_confirmed=False,
            chapter_outlines=[],
            current_chapter=1,
            outlines_confirmed=False,
            chapter_contents=[],
            current_content=None,
            critic_feedback=None,
            critic_iterations=0,
            error=None,
        )
        return self.graph.invoke(initial_state)
