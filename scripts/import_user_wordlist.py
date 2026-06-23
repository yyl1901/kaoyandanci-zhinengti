"""
用户词库导入脚本
支持 JSON / CSV / 纯文本 三种格式的考研词库文件导入

=== 用法 ===
1. 将你的词库文件放到 data/ 目录下
2. 运行: python scripts/import_user_wordlist.py
3. 可选参数:
   --file <路径>    指定单个文件导入
   --exam <类型>    指定考纲类型 (kaoyan/cet6/cet4)，默认 kaoyan
   --skip-chroma    跳过 Chroma 向量化
   --skip-db        跳过数据库导入
   --dry-run        仅预览，不实际导入
   --clear-first    导入前清空已有数据

=== 支持的格式 ===

JSON 格式1（完整格式，与项目 data/*.json 一致）:
  [{"word": "abandon", "phonetic_uk": "...", "definition": "...", ...}, ...]

JSON 格式2（简化格式，仅 word + definition）:
  [{"word": "abandon", "definition": "放弃；抛弃"}, ...]

CSV 格式:
  word,definition
  abandon,放弃；抛弃
  abstract,抽象的

纯文本格式（每行一个单词，自动查字典补全释义）:
  abandon
  abstract
  abuse
"""
import sys
import os
import io
import json
import csv
import re
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from backend.config import DATA_DIR


# ==================== 格式检测 & 解析 ====================

def detect_and_parse(filepath: Path) -> list[dict]:
    """检测文件格式并解析为单词字典列表"""
    suffix = filepath.suffix.lower()

    if suffix == ".json":
        return _parse_json(filepath)
    elif suffix in (".csv", ".tsv"):
        return _parse_csv(filepath)
    elif suffix == ".txt":
        return _parse_txt(filepath)
    else:
        raise ValueError(f"不支持的文件格式: {suffix}，请使用 .json / .csv / .txt")


def _parse_json(filepath: Path) -> list[dict]:
    """解析 JSON 词库文件"""
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError("JSON 文件应为数组格式: [{...}, {...}]")

    # 检查第一个词的格式
    if data and isinstance(data[0], dict):
        sample = data[0]
        if "word" in sample and "definition" in sample:
            print(f"  📄 JSON 格式检测: {'完整格式' if 'etymology' in sample else '简化格式（仅word+definition）'}")
            return data

    raise ValueError("JSON 数据格式不正确，每个词至少需要 word 和 definition 字段")


def _parse_csv(filepath: Path) -> list[dict]:
    """解析 CSV 词库文件"""
    words = []
    delimiter = "\t" if filepath.suffix == ".tsv" else ","

    with open(filepath, "r", encoding="utf-8") as f:
        # 尝试检测是否有 header
        first_line = f.readline().strip()
        f.seek(0)

        has_header = first_line.lower().startswith("word") or "word" in first_line.lower()

        reader = csv.DictReader(f) if has_header else csv.reader(f)

        if has_header:
            for row in reader:
                word = row.get("word", "").strip()
                definition = row.get("definition", "") or row.get("meaning", "") or row.get("释义", "")
                if word:
                    words.append({"word": word, "definition": definition.strip()})
        else:
            for row in reader:
                if len(row) >= 2:
                    words.append({"word": row[0].strip(), "definition": row[1].strip()})
                elif len(row) == 1 and row[0].strip():
                    words.append({"word": row[0].strip(), "definition": ""})

    print(f"  📄 CSV 格式: {len(words)} 行数据")
    return words


def _parse_txt(filepath: Path) -> list[dict]:
    """解析纯文本词库（每行一个单词）"""
    words = []
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            word = line.strip()
            # 跳过空行和注释行
            if word and not word.startswith("#") and not word.startswith("//"):
                # 移除行内注释
                word = re.split(r'[#//]', word)[0].strip()
                if word:
                    words.append({"word": word, "definition": ""})

    print(f"  📄 纯文本格式: {len(words)} 行单词")
    return words


# ==================== 数据标准化 ====================

def normalize_word_entry(raw: dict, exam_type: str = "kaoyan") -> dict:
    """
    将各种格式的原始词条标准化为项目 Word 模型字段
    """
    word = raw.get("word", "").strip()
    if not word:
        return None

    # 处理 definition 字段
    definition = raw.get("definition", "")
    if isinstance(definition, list):
        # 已经是结构化列表
        definition = json.dumps(definition, ensure_ascii=False)
    elif isinstance(definition, dict):
        definition = json.dumps([definition], ensure_ascii=False)
    elif isinstance(definition, str) and definition.strip():
        # 如果是纯文本释义，尝试解析
        if definition.startswith("[") and definition.endswith("]"):
            pass  # 已经是 JSON 字符串
        else:
            # 简单中文释义 → 包装为 JSON
            definition = json.dumps(
                [{"pos": "", "meaning": definition.strip()}],
                ensure_ascii=False,
            )
    else:
        definition = "[]"

    # 构建标准化词条
    entry = {
        "word": word,
        "phonetic_uk": raw.get("phonetic_uk", ""),
        "phonetic_us": raw.get("phonetic_us", ""),
        "definition": definition,
        "exam_type": raw.get("exam_type", exam_type),
        "category": raw.get("category", "core"),
        "frequency": raw.get("frequency", 3),
        "etymology": raw.get("etymology", ""),
        "example_sentences": raw.get("example_sentences", "[]"),
        "synonyms": raw.get("synonyms", "[]"),
        "antonyms": raw.get("antonyms", "[]"),
    }

    # 确保 JSON 字段是字符串
    for field in ["etymology", "example_sentences", "synonyms", "antonyms"]:
        if isinstance(entry[field], (dict, list)):
            entry[field] = json.dumps(entry[field], ensure_ascii=False)

    return entry


# ==================== 导入逻辑 ====================

def import_to_database(words: list[dict], clear_first: bool = False):
    """导入到 SQLite/MySQL"""
    try:
        from backend.models.database import init_db, engine_sync
        from sqlalchemy.orm import Session
        from backend.models.database import Word

        init_db()

        with Session(engine_sync) as session:
            if clear_first:
                print("  🗑️  清空已有数据...")
                session.query(Word).delete()
                session.commit()

            new_count = 0
            update_count = 0
            for entry in words:
                existing = session.query(Word).filter(
                    Word.word == entry["word"],
                    Word.exam_type == entry["exam_type"]
                ).first()
                if existing:
                    # 更新已有数据
                    for k, v in entry.items():
                        if hasattr(existing, k) and k not in ("word", "exam_type"):
                            setattr(existing, k, v)
                    update_count += 1
                else:
                    word_obj = Word(**entry)
                    session.add(word_obj)
                    new_count += 1

            session.commit()
            print(f"✅ 数据库导入完成 (新增 {new_count} 词, 更新 {update_count} 词, 共 {len(words)} 词)")
            return True
    except Exception as e:
        print(f"⚠️ 数据库导入失败: {e}")
        return False


def import_to_chromadb(words: list[dict], clear_first: bool = False):
    """导入到 ChromaDB 向量库"""
    try:
        from backend.core.knowledge.vector_store import VectorStore

        vs = VectorStore()
        if clear_first:
            vs.reset_all()

        # 按考纲 + 类型分类
        categories = {"cet4": [], "cet6": [], "kaoyan_core": [], "kaoyan_rare": []}

        for w in words:
            exam = w.get("exam_type", "kaoyan")
            category = w.get("category", "core")
            if exam == "kaoyan" and category == "rare":
                categories["kaoyan_rare"].append(w)
            elif exam == "kaoyan":
                categories["kaoyan_core"].append(w)
            elif exam == "cet6":
                categories["cet6"].append(w)
            else:
                categories["cet4"].append(w)

        collection_map = {
            "cet4": "word_kb_cet4",
            "cet6": "word_kb_cet6",
            "kaoyan_core": "word_kb_kaoyan_core",
            "kaoyan_rare": "word_kb_kaoyan_rare",
        }

        total = 0
        for cat_key, word_list in categories.items():
            if word_list:
                col_name = collection_map[cat_key]
                n = vs.add_words(col_name, word_list)
                total += n
                print(f"  ✅ {col_name}: {n} 词已向量化")

        print(f"✅ Chroma 向量库导入完成 (共 {total} 词)")
        return True
    except Exception as e:
        print(f"⚠️ Chroma 导入失败: {e}")
        return False


def find_wordlist_files(data_dir: Path) -> list[Path]:
    """查找 data/ 目录下的词库文件（排除内置文件和 all_words.json）"""
    builtin = {"cet4.json", "cet6.json", "kaoyan.json", "all_words.json"}
    candidates = []
    for f in sorted(data_dir.glob("*")):
        if f.suffix.lower() in (".json", ".csv", ".tsv", ".txt") and f.name not in builtin:
            candidates.append(f)
    return candidates


# ==================== 主入口 ====================

def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="用户词库导入脚本 —— 支持 JSON/CSV/TXT 格式",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python scripts/import_user_wordlist.py                          # 自动扫描 data/ 目录
  python scripts/import_user_wordlist.py --file data/my_words.json # 指定文件
  python scripts/import_user_wordlist.py --exam kaoyan --clear-first
  python scripts/import_user_wordlist.py --dry-run                # 仅预览
        """,
    )
    parser.add_argument("--file", type=str, help="指定词库文件路径")
    parser.add_argument("--exam", type=str, default="kaoyan", choices=["cet4", "cet6", "kaoyan"], help="考纲类型")
    parser.add_argument("--skip-chroma", action="store_true", help="跳过 Chroma 向量化")
    parser.add_argument("--skip-db", action="store_true", help="跳过数据库导入")
    parser.add_argument("--dry-run", action="store_true", help="仅预览，不实际导入")
    parser.add_argument("--clear-first", action="store_true", help="导入前清空已有数据")

    args = parser.parse_args()

    print("=" * 55)
    print("  📚 考研单词备考智能体 —— 用户词库导入")
    print("=" * 55)
    print()

    # 1. 确定要导入的文件
    if args.file:
        filepath = Path(args.file)
        if not filepath.exists():
            print(f"❌ 文件不存在: {filepath}")
            sys.exit(1)
        files = [filepath]
        print(f"📂 指定文件: {filepath.name}")
    else:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        files = find_wordlist_files(DATA_DIR)
        if not files:
            print(f"⚠️ 未在 data/ 目录下找到用户词库文件")
            print(f"   请将词库文件(.json/.csv/.txt)放入 data/ 目录后重新运行")
            print(f"   支持的命名示例: data/kaoyan_full.json, data/my_words.csv, data/words.txt")
            print()
            print(f"   💡 或指定文件: python scripts/import_user_wordlist.py --file <路径>")
            sys.exit(0)
        print(f"📂 扫描到 {len(files)} 个词库文件:")
        for f in files:
            print(f"   - {f.name}")

    # 2. 解析所有文件
    all_raw_words = []
    for f in files:
        print(f"\n📖 正在解析: {f.name}")
        try:
            parsed = detect_and_parse(f)
            all_raw_words.extend(parsed)
            print(f"   → 解析出 {len(parsed)} 个单词")
        except Exception as e:
            print(f"   ❌ 解析失败: {e}")
            continue

    if not all_raw_words:
        print("❌ 未解析到任何有效单词")
        sys.exit(1)

    # 3. 标准化
    print(f"\n🔧 正在标准化 {len(all_raw_words)} 个词条...")
    normalized_words = []
    skipped = 0
    for raw in all_raw_words:
        entry = normalize_word_entry(raw, exam_type=args.exam)
        if entry:
            normalized_words.append(entry)
        else:
            skipped += 1

    if skipped:
        print(f"   ⚠️ {skipped} 个词条因缺少word字段被跳过")
    print(f"   → 有效词条: {len(normalized_words)} 个")

    # 4. 预览 / 导入
    if args.dry_run:
        print(f"\n🔍 [DRY RUN] 预览模式 —— 不会实际导入")
        print(f"   考纲类型: {args.exam}")
        print(f"   词条数量: {len(normalized_words)}")
        print(f"\n   前10个单词预览:")
        for w in normalized_words[:10]:
            def_text = w["definition"]
            try:
                def_obj = json.loads(def_text)
                if isinstance(def_obj, list) and len(def_obj) > 0:
                    def_text = def_obj[0].get("meaning", def_text)
            except (json.JSONDecodeError, TypeError):
                pass
            print(f"   - {w['word']:20s} | {def_text}")
        if len(normalized_words) > 10:
            print(f"   ... 还有 {len(normalized_words) - 10} 个词")
        return

    # 5. 数据库导入
    if not args.skip_db:
        print(f"\n🗄️  正在导入数据库...")
        import_to_database(normalized_words, clear_first=args.clear_first)
    else:
        print(f"\n⏭️  跳过数据库导入")

    # 6. Chroma 导入
    if not args.skip_chroma:
        print(f"\n🧬 正在向量化...")
        import_to_chromadb(normalized_words, clear_first=args.clear_first)
    else:
        print(f"\n⏭️  跳过 Chroma 向量化")

    print()
    print("=" * 55)
    print(f"  ✅ 导入完成！共处理 {len(normalized_words)} 个单词")
    print(f"  💡 启动后端: python -m uvicorn backend.main:app --port 8000")
    print("=" * 55)


if __name__ == "__main__":
    main()
