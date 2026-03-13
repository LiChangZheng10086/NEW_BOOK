"""
向量数据库操作封装 (Chroma)
"""
import json
from typing import List, Optional
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.documents import Document
from core.models import NovelSettings, ChapterOutline, ChapterContent


class NovelDatabase:
    def __init__(self, persist_dir: str = "./chroma_db"):
        # 使用本地中文向量模型，无需额外 API Key
        self.embeddings = HuggingFaceEmbeddings(
            model_name="BAAI/bge-small-zh-v1.5",
            model_kwargs={"device": "cpu"},
        )
        self.persist_dir = persist_dir

        self.settings_store = Chroma(
            collection_name="novel_settings",
            embedding_function=self.embeddings,
            persist_directory=persist_dir,
        )
        self.outlines_store = Chroma(
            collection_name="chapter_outlines",
            embedding_function=self.embeddings,
            persist_directory=persist_dir,
        )
        self.chapters_store = Chroma(
            collection_name="chapter_contents",
            embedding_function=self.embeddings,
            persist_directory=persist_dir,
        )

    def save_novel_settings(self, settings: NovelSettings) -> None:
        doc = Document(
            page_content=settings.model_dump_json(),
            metadata={"title": settings.title, "type": "settings"},
        )
        self.settings_store.add_documents([doc])

    def save_chapter_outline(self, outline: ChapterOutline, novel_title: str) -> None:
        doc = Document(
            page_content=outline.model_dump_json(),
            metadata={"novel_title": novel_title, "chapter": outline.chapter_number, "type": "outline"},
        )
        self.outlines_store.add_documents([doc])

    def save_chapter_content(self, chapter: ChapterContent, novel_title: str) -> None:
        doc = Document(
            page_content=chapter.content,
            metadata={"novel_title": novel_title, "chapter": chapter.chapter_number, "title": chapter.title, "type": "chapter"},
        )
        self.chapters_store.add_documents([doc])

    def get_novel_settings(self, title: str) -> Optional[NovelSettings]:
        results = self.settings_store.similarity_search(title, k=1, filter={"type": "settings"})
        if results:
            return NovelSettings.model_validate_json(results[0].page_content)
        return None

    def get_chapter_outline(self, novel_title: str, chapter_number: int) -> Optional[ChapterOutline]:
        results = self.outlines_store.similarity_search(
            f"chapter {chapter_number}",
            k=1,
            filter={"novel_title": novel_title, "chapter": chapter_number},
        )
        if results:
            return ChapterOutline.model_validate_json(results[0].page_content)
        return None

    def get_chapter_content(self, novel_title: str, chapter_number: int) -> Optional[str]:
        results = self.chapters_store.similarity_search(
            f"chapter {chapter_number}",
            k=1,
            filter={"novel_title": novel_title, "chapter": chapter_number},
        )
        if results:
            return results[0].page_content
        return None

    def get_all_outlines(self, novel_title: str) -> List[ChapterOutline]:
        results = self.outlines_store.similarity_search(
            novel_title, k=100, filter={"novel_title": novel_title, "type": "outline"}
        )
        outlines = [ChapterOutline.model_validate_json(r.page_content) for r in results]
        return sorted(outlines, key=lambda x: x.chapter_number)
