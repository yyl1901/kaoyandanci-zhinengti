"""
向量知识库 —— Chroma 向量存储
按考纲分类：四级词库、六级词库、考研核心词/熟词僻义词库
"""
import json
from pathlib import Path
from chromadb import PersistentClient
from chromadb.config import Settings
from backend.config import CHROMA_CONFIG


class VectorStore:
    """
    Chroma 向量知识库管理

    集合设计：
    - word_kb_cet4：四级词库
    - word_kb_cet6：六级词库
    - word_kb_kaoyan_core：考研核心词
    - word_kb_kaoyan_rare：考研熟词僻义
    """

    COLLECTIONS = {
        "cet4": "word_kb_cet4",
        "cet6": "word_kb_cet6",
        "kaoyan_core": "word_kb_kaoyan_core",
        "kaoyan_rare": "word_kb_kaoyan_rare",
    }

    def __init__(self, persist_dir: str | None = None):
        persist_dir = persist_dir or CHROMA_CONFIG["persist_directory"]
        Path(persist_dir).mkdir(parents=True, exist_ok=True)
        self._client = PersistentClient(
            path=persist_dir,
            settings=Settings(anonymized_telemetry=False),
        )

    def get_or_create_collection(self, name: str):
        """获取或创建集合"""
        return self._client.get_or_create_collection(
            name=name,
            metadata={"hnsw:space": "cosine"},
        )

    def list_collections(self) -> list[str]:
        """列出所有集合"""
        return [c.name for c in self._client.list_collections()]

    def delete_collection(self, name: str) -> None:
        """删除集合"""
        try:
            self._client.delete_collection(name)
        except Exception:
            pass

    def reset_all(self) -> None:
        """重置所有知识库集合"""
        for col_name in self.COLLECTIONS.values():
            self.delete_collection(col_name)

    def add_words(
        self,
        collection_name: str,
        words: list[dict],
        embeddings: list[list[float]] | None = None,
    ) -> int:
        """
        批量添加单词到向量库
        :param collection_name: 集合名称
        :param words: 单词数据列表 [{id, word, definition, ...}]
        :param embeddings: 可选，预计算的向量；不提供则用 Chroma 内置 embedding
        :return: 添加的单词数
        """
        if not words:
            return 0

        col = self.get_or_create_collection(collection_name)

        ids = [f"word_{w.get('id', w.get('word', f'unknown_{i}'))}" for i, w in enumerate(words)]
        documents = [
            self._word_to_document(w) for w in words
        ]
        metadatas = [
            {
                "word_id": w.get("id", "N/A"),
                "word": w.get("word", ""),
                "exam_type": w.get("exam_type", ""),
                "category": w.get("category", "core"),
            }
            for w in words
        ]

        col.add(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
            embeddings=embeddings,
        )
        return len(words)

    def search(
        self,
        query: str,
        collection_names: list[str] | None = None,
        n_results: int = 5,
    ) -> dict:
        """
        向量检索：从指定集合中检索最相关的单词
        :param query: 查询文本
        :param collection_names: 集合名列表，默认搜索全部
        :param n_results: 返回结果数
        :return: {collection_name: [{id, word, definition, distance}, ...]}
        """
        if collection_names is None:
            collection_names = list(self.COLLECTIONS.values())

        results = {}
        for col_name in collection_names:
            try:
                col = self._client.get_collection(col_name)
                query_result = col.query(
                    query_texts=[query],
                    n_results=n_results,
                )
                items = []
                if query_result["ids"] and query_result["documents"]:
                    for i in range(len(query_result["ids"][0])):
                        items.append({
                            "id": query_result["ids"][0][i],
                            "document": query_result["documents"][0][i],
                            "metadata": query_result["metadatas"][0][i] if query_result["metadatas"] else {},
                            "distance": query_result["distances"][0][i] if query_result["distances"] else 0,
                        })
                results[col_name] = items
            except Exception:
                results[col_name] = []

        return results

    def search_all(
        self,
        query: str,
        n_results: int = 5,
    ) -> list[dict]:
        """跨所有集合检索，返回排序后的结果列表"""
        all_results = []
        raw = self.search(query, n_results=n_results)
        for col_name, items in raw.items():
            for item in items:
                item["collection"] = col_name
                all_results.append(item)
        # 按相似度排序（distance 越小越相似）
        all_results.sort(key=lambda x: x.get("distance", 999))
        return all_results[:n_results]

    @staticmethod
    def _word_to_document(word: dict) -> str:
        """将单词数据转为可向量化的文本"""
        parts = [f"单词: {word.get('word', '')}"]
        if word.get("phonetic_uk"):
            parts.append(f"英音: {word['phonetic_uk']}")
        if word.get("definition"):
            def_val = word["definition"]
            if isinstance(def_val, (dict, list)):
                def_val = json.dumps(def_val, ensure_ascii=False)
            parts.append(f"释义: {def_val}")
        if word.get("etymology"):
            parts.append(f"词根: {word['etymology']}")
        if word.get("example_sentences"):
            parts.append(f"例句: {word['example_sentences']}")
        return "\n".join(parts)


# 全局向量库实例
_global_vs: VectorStore | None = None


def get_vector_store() -> VectorStore:
    global _global_vs
    if _global_vs is None:
        _global_vs = VectorStore()
    return _global_vs
