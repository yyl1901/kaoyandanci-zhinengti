"""
RAG 检索增强生成优化模块
用户提问时先从向量知识库检索对应单词释义、真题考法，再送入LLM生成答案
"""
import json
from backend.core.knowledge.vector_store import get_vector_store, VectorStore
from backend.core.llm.llm_client import LLMClient, SYSTEM_PROMPT_BASE


class RAGRetriever:
    """
    RAG 检索增强生成器

    流程：
    1. 用户提问 → 从 Chroma 向量库检索相关单词/考点
    2. 将检索结果作为上下文注入 LLM 提示词
    3. LLM 基于检索结果生成答案，减少幻觉
    """

    RAG_SYSTEM_PROMPT = """{base}

## 参考知识库上下文
以下是从单词知识库中检索到的相关信息，请基于这些信息回答问题。
如果知识库信息不足以回答问题，请如实告知，不要编造内容。

{context}

## 回答要求
1. 优先使用知识库中的释义、例句、考点
2. 如果涉及词根词缀，基于知识库中的拆解信息讲解
3. 标注信息来源（如"根据考研真题库..."）
4. 回答结构化，便于阅读"""

    def __init__(self, vector_store: VectorStore | None = None):
        self.vs = vector_store or get_vector_store()
        self.llm = LLMClient()

    async def retrieve(self, query: str, exam_type: str | None = None, top_k: int = 5) -> list[dict]:
        """
        检索相关单词/知识点
        :param query: 用户查询
        :param exam_type: 限定考纲
        :param top_k: 返回数量
        """
        collections = None
        if exam_type:
            collections = [v for k, v in VectorStore.COLLECTIONS.items() if exam_type in k]
            if not collections:
                collections = None

        return self.vs.search_all(query, n_results=top_k)

    async def generate_with_rag(
        self,
        query: str,
        exam_type: str | None = None,
        context: str | None = None,
    ) -> str:
        """
        RAG 增强生成：检索 + LLM 生成
        """
        # 1. 检索相关单词
        retrieved = await self.retrieve(query, exam_type)

        # 2. 构建上下文
        context_parts = []
        if context:
            context_parts.append(f"## 用户学习上下文\n{context}")

        if retrieved:
            context_parts.append("## 知识库检索结果")
            for i, item in enumerate(retrieved[:5], 1):
                metadata = item.get("metadata", {})
                doc = item.get("document", "")
                context_parts.append(
                    f"**{i}. {metadata.get('word', '')}**"
                    f"（考纲：{metadata.get('exam_type', '')}，"
                    f"相似度：{1 - item.get('distance', 0):.2f}）\n{doc[:500]}"
                )
        else:
            context_parts.append("（知识库中未找到直接相关的内容，请基于LLM知识回答）")

        rag_context = "\n\n".join(context_parts)

        # 3. 调用 LLM 生成
        system_prompt = self.RAG_SYSTEM_PROMPT.format(
            base=SYSTEM_PROMPT_BASE,
            context=rag_context,
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": query},
        ]
        return await self.llm.chat(messages, temperature=0.3)

    async def get_word_detail_with_rag(self, word: str, exam_type: str | None = None) -> dict:
        """
        通过 RAG 获取单词详解
        检索知识库 + LLM 增强生成
        """
        query = f"请详细讲解单词: {word}，包括释义、词根词缀、真题例句、近反义词、易错点"
        result_text = await self.generate_with_rag(query, exam_type)

        # 尝试解析为结构化JSON
        try:
            return self.llm._parse_json(result_text)
        except (json.JSONDecodeError, ValueError):
            return {"word": word, "content": result_text, "format": "text"}
