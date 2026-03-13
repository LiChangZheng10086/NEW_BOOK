"""
Gradio 前端界面
"""
import gradio as gr
from config.settings import Settings
from core.database import NovelDatabase
from agents.planner import PlannerAgent
from agents.outline_writer import OutlineWriterAgent
from agents.chapter_writer import ChapterWriterAgent
from agents.critic import CriticAgent

settings = Settings()
db = NovelDatabase(settings.chroma_db_dir)
planner = PlannerAgent(settings)
outline_writer = OutlineWriterAgent(settings)
chapter_writer = ChapterWriterAgent(settings)
critic = CriticAgent(settings)


def _initial_state():
    return {
        "novel_settings": None,
        "current_outline": None,
        "current_chapter_content": None,
        "current_chapter_num": 1,
        "critic_feedback": None,
    }


def step1_plan(title, genre, outline, characters, world_setting, foreshadowings, writing_style, target_chapters, state):
    if not settings.deepseek_api_key:
        return state, "", "❌ 请先在 .env 中配置 DEEPSEEK_API_KEY 后重启应用"
    user_input = {
        "title": title, "genre": genre, "outline": outline,
        "characters": characters, "world_setting": world_setting,
        "foreshadowings": foreshadowings, "writing_style": writing_style,
        "target_chapters": int(target_chapters),
    }
    try:
        novel_settings = planner.run(user_input)
    except Exception as e:
        return state, "", f"❌ 生成设定失败：{e}"
    new_state = {**state, "novel_settings": novel_settings}
    return new_state, novel_settings.model_dump_json(indent=2), ""


def step1_confirm(edited_json, state):
    from core.models import NovelSettings
    if not state.get("novel_settings"):
        return state, "❌ 请先点击「生成完善设定」"
    try:
        novel_settings = NovelSettings.model_validate_json(edited_json)
        db.save_novel_settings(novel_settings)
        new_state = {**state, "novel_settings": novel_settings}
        return new_state, "✅ 设定已确认并存入数据库"
    except Exception as e:
        return state, f"❌ 解析失败：{e}"


def step2_gen_outline(chapter_num, state):
    if not state.get("novel_settings"):
        return state, "请先完成第一步设定"
    chapter_num = int(chapter_num)
    new_state = {**state, "current_chapter_num": chapter_num}
    previous_ending = db.get_chapter_content(state["novel_settings"].title, chapter_num - 1) or ""
    outline = outline_writer.run(state["novel_settings"], chapter_num, previous_ending)
    new_state = {**new_state, "current_outline": outline}
    return new_state, outline.model_dump_json(indent=2)


def step2_confirm_outline(edited_json, state):
    from core.models import ChapterOutline
    if not state.get("novel_settings"):
        return state, "❌ 请先完成第一步设定"
    try:
        outline = ChapterOutline.model_validate_json(edited_json)
        db.save_chapter_outline(outline, state["novel_settings"].title)
        new_state = {**state, "current_outline": outline}
        return new_state, "✅ 大纲已确认并存入数据库"
    except Exception as e:
        return state, f"❌ 解析失败：{e}"


def step3_write_chapter(state):
    if not state.get("novel_settings") or not state.get("current_outline"):
        return state, "请先完成前两步"
    chapter_num = state["current_chapter_num"]
    previous_ending = db.get_chapter_content(state["novel_settings"].title, chapter_num - 1) or ""
    chapter = chapter_writer.run(state["novel_settings"], state["current_outline"], previous_ending)
    new_state = {**state, "current_chapter_content": chapter}
    return new_state, chapter.content


def step3_review(state):
    if not state.get("current_chapter_content"):
        return state, "", "请先生成章节内容"
    chapter_num = state["current_chapter_num"]
    previous_content = db.get_chapter_content(state["novel_settings"].title, chapter_num - 1) or ""
    feedback = critic.run(state["novel_settings"], state["current_chapter_content"], previous_content)
    feedback_text = "\n".join([
        f"逻辑问题：{feedback.logic_issues}",
        f"风格问题：{feedback.style_issues}",
        f"角色问题：{feedback.character_issues}",
        f"连贯性问题：{feedback.continuity_issues}",
        f"修改建议：{feedback.suggestions}",
        f"是否通过：{'✅' if feedback.approved else '❌'}",
    ])
    new_state = {**state, "critic_feedback": feedback}
    return new_state, state["current_chapter_content"].content, feedback_text


def step3_revise(state):
    if not state.get("critic_feedback"):
        return state, "请先进行审阅"
    revised = chapter_writer.revise(state["current_chapter_content"], state["critic_feedback"])
    new_state = {**state, "current_chapter_content": revised}
    return new_state, revised.content


def step3_confirm_chapter(edited_content, state):
    if not state.get("current_chapter_content"):
        return state, "请先生成或审阅章节后再确认"
    if not state.get("novel_settings"):
        return state, "❌ 设定缺失，请先完成第一步"
    current = state["current_chapter_content"]
    updated = current.model_copy(update={"content": edited_content, "status": "confirmed"})
    db.save_chapter_content(updated, state["novel_settings"].title)
    new_state = {**state, "current_chapter_content": updated}
    return new_state, "✅ 章节已确认并存入数据库"


with gr.Blocks(title="AI 小说创作助手") as app:
    gr.Markdown("# AI 小说创作助手")
    api_key_warning = gr.Markdown(
        "⚠️ 请先在项目根目录配置 `.env` 中的 `DEEPSEEK_API_KEY`，否则无法生成内容。"
        if not settings.deepseek_api_key else ""
    )
    session_state = gr.State(_initial_state)

    with gr.Tab("第一步：编剧设定"):
        with gr.Row():
            with gr.Column():
                title_in = gr.Textbox(label="小说标题")
                genre_in = gr.Textbox(label="小说类型")
                outline_in = gr.Textbox(label="故事大纲", lines=4)
                characters_in = gr.Textbox(label="主要角色", lines=3)
                world_in = gr.Textbox(label="世界设定", lines=3)
                foreshadow_in = gr.Textbox(label="伏笔线索", lines=2)
                style_in = gr.Textbox(label="写作风格")
                chapters_in = gr.Number(label="目标章节数", value=10)
                plan_btn = gr.Button("生成完善设定", variant="primary")
            with gr.Column():
                settings_out = gr.Code(label="完善后的设定（可编辑）", language="json", lines=25)
                confirm_btn = gr.Button("确认并存入数据库", variant="secondary")
                confirm_msg = gr.Textbox(label="状态")

        plan_btn.click(
            step1_plan,
            [title_in, genre_in, outline_in, characters_in, world_in, foreshadow_in, style_in, chapters_in, session_state],
            [session_state, settings_out, confirm_msg],
        )
        confirm_btn.click(
            step1_confirm,
            [settings_out, session_state],
            [session_state, confirm_msg],
        )

    with gr.Tab("第二步：章节大纲"):
        chapter_num_in = gr.Number(label="章节编号", value=1)
        gen_outline_btn = gr.Button("生成章节大纲", variant="primary")
        outline_out = gr.Code(label="章节大纲（可编辑）", language="json", lines=15)
        confirm_outline_btn = gr.Button("确认大纲并存入数据库", variant="secondary")
        outline_confirm_msg = gr.Textbox(label="状态")

        gen_outline_btn.click(
            step2_gen_outline,
            [chapter_num_in, session_state],
            [session_state, outline_out],
        )
        confirm_outline_btn.click(
            step2_confirm_outline,
            [outline_out, session_state],
            [session_state, outline_confirm_msg],
        )

    with gr.Tab("第三步：写作与审阅"):
        write_btn = gr.Button("生成章节正文", variant="primary")
        chapter_out = gr.Textbox(label="章节内容（可编辑）", lines=20)
        with gr.Row():
            review_btn = gr.Button("评论家审阅")
            revise_btn = gr.Button("根据建议修改")
        feedback_out = gr.Textbox(label="审阅意见", lines=8)
        confirm_chapter_btn = gr.Button("确认章节并存入数据库", variant="secondary")
        chapter_confirm_msg = gr.Textbox(label="状态")

        write_btn.click(
            step3_write_chapter,
            [session_state],
            [session_state, chapter_out],
        )
        review_btn.click(
            step3_review,
            [session_state],
            [session_state, chapter_out, feedback_out],
        )
        revise_btn.click(
            step3_revise,
            [session_state],
            [session_state, chapter_out],
        )
        confirm_chapter_btn.click(
            step3_confirm_chapter,
            [chapter_out, session_state],
            [session_state, chapter_confirm_msg],
        )


if __name__ == "__main__":
    app.launch()
