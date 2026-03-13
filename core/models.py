"""
Pydantic 数据模型定义
"""
from typing import List, Optional
from pydantic import BaseModel, Field


class Character(BaseModel):
    name: str
    role: str  # 主角/反派/配角
    background: str
    personality: str
    appearance: str
    relationship_to_protagonist: str
    arc: Optional[str] = None


class Foreshadowing(BaseModel):
    description: str
    appear_chapter: int
    resolve_chapter: int
    details: Optional[str] = None


class PlotSegment(BaseModel):
    start_chapter: int
    end_chapter: int
    summary: str


class NovelSettings(BaseModel):
    title: str
    genre: str
    writing_style: str
    target_chapters: int
    outline: str
    world_setting: str
    characters: List[Character] = Field(default_factory=list)
    foreshadowings: List[Foreshadowing] = Field(default_factory=list)
    plot_segments: List[PlotSegment] = Field(default_factory=list)


class ChapterOutline(BaseModel):
    chapter_number: int
    title: str
    summary: str
    key_events: List[str]
    characters_involved: List[str]
    foreshadowing_hints: Optional[List[str]] = None


class ChapterContent(BaseModel):
    chapter_number: int
    title: str
    content: str
    word_count: int = 0
    status: str = "draft"  # draft / reviewed / confirmed


class CriticFeedback(BaseModel):
    chapter_number: int
    logic_issues: List[str] = Field(default_factory=list)
    style_issues: List[str] = Field(default_factory=list)
    character_issues: List[str] = Field(default_factory=list)
    continuity_issues: List[str] = Field(default_factory=list)
    suggestions: List[str] = Field(default_factory=list)
    approved: bool = False
