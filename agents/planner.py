"""
编剧 Agent - 负责完善小说整体设定
"""
import json
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_tavily import TavilySearch
from core.models import NovelSettings, Character, Foreshadowing, PlotSegment
from config.prompts import PLANNER_SYSTEM, PLANNER_HUMAN
from config.settings import Settings
from core.logger import get_logger

logger = get_logger("PlannerAgent")


class PlannerAgent:
    def __init__(self, settings: Settings):
        self.llm = ChatOpenAI(
            model=settings.model,
            api_key=settings.deepseek_api_key,
            base_url=settings.deepseek_base_url,
            max_tokens=8192,
        )
        self.search_tool = TavilySearch(max_results=3)
        logger.info("PlannerAgent 初始化完成，模型：%s", settings.model)

    def run(self, user_input: dict) -> NovelSettings:
        """根据用户输入完善小说设定"""
        logger.info(">>> [编剧Agent] 开始完善小说设定，标题：%s", user_input.get("title"))
        search_context = ""
        if user_input.get("world_setting"):
            logger.info("正在联网搜索世界设定参考资料...")
            try:
                results = self.search_tool.invoke(
                    f"{user_input['genre']} 小说 世界设定 {user_input['world_setting'][:50]}"
                )
                if isinstance(results, list):
                    search_context = "\n".join([
                        r.get("content", r) if isinstance(r, dict) else str(r)
                        for r in results[:2]
                    ])
                logger.info("联网搜索完成，获取到 %d 条参考资料", len(results) if isinstance(results, list) else 0)
            except Exception as e:
                logger.warning("联网搜索失败（跳过）：%s", e)

        human_content = PLANNER_HUMAN.format(
            title=user_input.get("title", ""),
            genre=user_input.get("genre", ""),
            outline=user_input.get("outline", ""),
            characters=user_input.get("characters", ""),
            world_setting=user_input.get("world_setting", "") + (f"\n\n参考资料：{search_context}" if search_context else ""),
            foreshadowings=user_input.get("foreshadowings", ""),
            writing_style=user_input.get("writing_style", ""),
            target_chapters=user_input.get("target_chapters", 10),
        )

        messages = [
            SystemMessage(content=PLANNER_SYSTEM),
            HumanMessage(content=human_content),
        ]

        logger.info("正在调用 LLM 生成完善设定...")
        response = self.llm.invoke(messages)
        logger.debug("LLM 原始返回：\n%s", response.content[:500])
        result = self._parse_response(response.content, user_input)
        logger.info("<<< [编剧Agent] 设定完善完成，角色数：%d，伏笔数：%d，剧情段数：%d",
                    len(result.characters), len(result.foreshadowings), len(result.plot_segments))
        return result

    def _parse_response(self, content: str, fallback: dict) -> NovelSettings:
        try:
            start = content.find("{")
            end = content.rfind("}") + 1
            if start != -1 and end > start:
                data = json.loads(content[start:end])
                return NovelSettings.model_validate(data)
        except Exception as e:
            logger.warning("JSON 解析失败，使用基础设定兜底：%s", e)
        # 解析失败时返回基础设定
        return NovelSettings(
            title=fallback.get("title", ""),
            genre=fallback.get("genre", ""),
            writing_style=fallback.get("writing_style", ""),
            target_chapters=int(fallback.get("target_chapters", 10)),
            outline=fallback.get("outline", ""),
            world_setting=fallback.get("world_setting", ""),
        )
