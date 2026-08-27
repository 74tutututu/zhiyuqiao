"""
Data Migration Script: File System -> Vector Database

Migrates all knowledge base data from file system (CSV, JSONL) to Chroma vector DB.
Run this script once to initialize the vector database before using vector_retriever.py
"""

import hashlib
import json
import logging
import sys
from pathlib import Path
from typing import Dict, List, Any
import time

import pandas as pd
import chromadb
from sentence_transformers import SentenceTransformer

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Paths
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
DATABASE_DIR = PROJECT_ROOT / "database"
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.config import EMBEDDING_MODEL, VECTOR_DB_DIR

# Constants
BATCH_SIZE = 256  # Batch size for embedding generation
CHUNK_SIZE = 400  # Characters per chunk for long documents
CHUNK_OVERLAP = 50  # Character overlap between chunks


class VectorDBMigrator:
    """Handles migration of knowledge base data to vector database."""

    def __init__(self, reset: bool = False):
        """Initialize migrator.

        Args:
            reset: If True, reset vector database before migrating
        """
        self.db_dir = VECTOR_DB_DIR
        self.db_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Initializing Chroma client at {self.db_dir}")
        self.client = chromadb.PersistentClient(
            path=str(self.db_dir),
            settings=chromadb.Settings(anonymized_telemetry=False)
        )

        if reset:
            logger.warning("Resetting vector database...")
            self.client.reset()

        logger.info(f"Loading embedding model: {EMBEDDING_MODEL}")
        self.embedding_model = SentenceTransformer(EMBEDDING_MODEL)

        self.stats = {
            "hsk": 0,
            "mucgec": 0,
            "teacher": 0,
            "strategies": 0,
            "references": 0,
            "softwares": 0
        }
        self._prepared_domains = set()

    def _chunk_text(self, text: str, chunk_size: int = CHUNK_SIZE) -> List[str]:
        """Split text into overlapping chunks."""
        if not text or len(text) <= chunk_size:
            return [text]

        chunks = []
        overlap = CHUNK_OVERLAP
        start = 0

        while start < len(text):
            end = min(start + chunk_size, len(text))
            chunks.append(text[start:end])

            # Move start for next chunk with overlap
            start = end - overlap if end < len(text) else len(text)

        return chunks

    def _add_documents(self, collection, documents, metadatas, ids):
        """使用与查询端一致的多语种模型生成向量并分批写入。"""
        for i in range(0, len(documents), BATCH_SIZE):
            batch_docs = documents[i:i+BATCH_SIZE]
            batch_meta = metadatas[i:i+BATCH_SIZE]
            batch_ids = ids[i:i+BATCH_SIZE]
            embeddings = self.embedding_model.encode(
                batch_docs,
                batch_size=64,
                show_progress_bar=False,
                normalize_embeddings=True,
            ).tolist()
            collection.add(
                documents=batch_docs,
                metadatas=batch_meta,
                ids=batch_ids,
                embeddings=embeddings,
            )

    def _detect_text_encoding(self, file_path: Path) -> str:
        """为历史语料选择更合适的编码，优先得到可读中文。"""
        candidates = ["utf-8", "gb18030", "gbk"]
        best_encoding = "utf-8"
        best_score = -1

        for encoding in candidates:
            try:
                with open(file_path, "r", encoding=encoding, errors="ignore") as f:
                    sample = "".join([f.readline() for _ in range(30)])
                if not sample:
                    continue
                chinese_count = len([ch for ch in sample if "\u4e00" <= ch <= "\u9fff"])
                score = chinese_count / max(len(sample), 1)
                if score > best_score:
                    best_score = score
                    best_encoding = encoding
            except Exception:
                continue

        return best_encoding

    def migrate_hsk(self):
        """Migrate HSK vocabulary, characters, and grammar data."""
        logger.info("="*50)
        logger.info("MIGRATING HSK DATA...")
        logger.info("="*50)

        hsk_dir = DATABASE_DIR / "HSK3.0" / "hsk30-master"

        # Delete existing collection if it exists
        try:
            self.client.delete_collection(name="hsk")
            logger.info("Deleted existing HSK collection")
        except:
            pass

        collection = self.client.get_or_create_collection(
            name="hsk",
            metadata={"hnsw:space": "cosine"}
        )

        # Migrate vocabulary (hsk30.csv)
        vocab_file = hsk_dir / "hsk30.csv"
        if vocab_file.exists():
            logger.info(f"Loading {vocab_file.name}...")
            df = pd.read_csv(vocab_file, encoding='utf-8')

            documents = []
            metadatas = []
            ids = []

            for idx, row in df.iterrows():
                # Create searchable text
                word = str(row.get('Simplified', '')).strip()
                traditional = str(row.get('Traditional', '')).strip()
                pinyin = str(row.get('Pinyin', '')).strip()
                level = str(row.get('Level', '')).strip()
                pos = str(row.get('POS', '')).strip()

                if not word:
                    continue

                # Format: word(pinyin)[POS]HSK_Level
                text = f"{word}({pinyin})[{pos}]HSK{level}级"
                doc_id = f"hsk_vocab_{idx}"

                documents.append(text)
                metadatas.append({
                    "type": "vocabulary",
                    "word": word,
                    "traditional": traditional,
                    "pinyin": pinyin,
                    "level": str(level),
                    "pos": pos,
                    "source": "hsk30.csv"
                })
                ids.append(doc_id)

                if len(documents) % 100 == 0:
                    logger.info(f"  Processed {len(documents)} vocab items...")

            logger.info(f"Adding {len(documents)} vocabulary items to Chroma...")
            self._add_documents(collection, documents, metadatas, ids)

            self.stats["hsk"] += len(documents)
            logger.info(f"✓ Added {len(documents)} HSK vocabulary items")

        # Migrate characters (hsk30-chars.csv)
        chars_file = hsk_dir / "hsk30-chars.csv"
        if chars_file.exists():
            logger.info(f"Loading {chars_file.name}...")
            df = pd.read_csv(chars_file, encoding='utf-8')

            documents = []
            metadatas = []
            ids = []

            for idx, row in df.iterrows():
                char = str(row.get('Hanzi', '')).strip()
                traditional = str(row.get('Traditional', '')).strip()
                level = str(row.get('Level', '')).strip()
                frequency = str(row.get('Freq', '')).strip()
                examples = str(row.get('Examples', '')).strip()

                if not char:
                    continue

                text = (
                    f"汉字：{char} 繁体：{traditional} HSK{level}级 "
                    f"常用例词：{examples}"
                )
                doc_id = f"hsk_char_{idx}"

                documents.append(text)
                metadatas.append({
                    "type": "character",
                    "character": char,
                    "traditional": traditional,
                    "level": str(level),
                    "frequency": frequency,
                    "examples": examples,
                    "source": "hsk30-chars.csv"
                })
                ids.append(doc_id)

            logger.info(f"Adding {len(documents)} character items to Chroma...")
            self._add_documents(collection, documents, metadatas, ids)

            self.stats["hsk"] += len(documents)
            logger.info(f"✓ Added {len(documents)} HSK character items")

        # Migrate grammar (hsk30-grammar.csv)
        grammar_file = hsk_dir / "hsk30-grammar.csv"
        if grammar_file.exists():
            logger.info(f"Loading {grammar_file.name}...")
            df = pd.read_csv(grammar_file, encoding='utf-8')

            documents = []
            metadatas = []
            ids = []

            for idx, row in df.iterrows():
                point = str(row.get('Content', '')).strip()
                level = str(row.get('Level', '')).strip()
                category = str(row.get('Category', '')).strip()
                details = str(row.get('Details', '')).strip()

                if not point:
                    continue

                text = f"语法点：{point} 分类：{category}/{details} HSK{level}级"
                doc_id = f"hsk_grammar_{idx}"

                documents.append(text)
                metadatas.append({
                    "type": "grammar",
                    "point": point,
                    "category": category,
                    "details": details,
                    "level": str(level),
                    "source": "hsk30-grammar.csv"
                })
                ids.append(doc_id)

            logger.info(f"Adding {len(documents)} grammar items to Chroma...")
            self._add_documents(collection, documents, metadatas, ids)

            self.stats["hsk"] += len(documents)
            logger.info(f"✓ Added {len(documents)} HSK grammar items")

    def migrate_jsonl_domain(self, domain: str, file_path: Path, chunk: bool = True):
        """Migrate a JSONL domain."""
        logger.info(f"\nMigrating {domain} from {file_path.name}...")

        # 一个知识域可能由多个文件组成。只在首个文件写入前删除旧集合，
        # 后续文件必须追加，否则最终只会保留最后一个源文件。
        if domain not in self._prepared_domains:
            try:
                self.client.delete_collection(name=domain)
                logger.info(f"Deleted existing {domain} collection")
            except Exception:
                pass
            self._prepared_domains.add(domain)

        collection = self.client.get_or_create_collection(
            name=domain,
            metadata={"hnsw:space": "cosine"}
        )

        documents = []
        metadatas = []
        ids = []
        doc_counter = 0
        source_key = hashlib.sha1(
            str(file_path.relative_to(DATABASE_DIR)).encode("utf-8")
        ).hexdigest()[:12]

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line_idx, line in enumerate(f):
                    line = line.strip()
                    if not line:
                        continue

                    try:
                        data = json.loads(line)

                        # Extract main text content
                        if isinstance(data, dict):
                            text = data.get('content') or data.get('text') or str(data)
                        else:
                            text = str(data)

                        if not text or len(text) < 5:
                            continue

                        # Chunk long documents
                        if chunk and len(text) > CHUNK_SIZE:
                            chunks = self._chunk_text(text, CHUNK_SIZE)
                            for chunk_idx, chunk_text in enumerate(chunks):
                                documents.append(chunk_text)
                                metadatas.append({
                                    "domain": domain,
                                    "chunk_index": str(chunk_idx),
                                    "source": file_path.name,
                                    "original_line": str(line_idx)
                                })
                                ids.append(f"{domain}_{source_key}_{line_idx}_{chunk_idx}")
                                doc_counter += 1
                        else:
                            documents.append(text)
                            metadatas.append({
                                "domain": domain,
                                "chunk_index": "0",
                                "source": file_path.name,
                                "original_line": str(line_idx)
                            })
                            ids.append(f"{domain}_{source_key}_{line_idx}")
                            doc_counter += 1

                        if doc_counter % 100 == 0:
                            logger.info(f"  Processed {doc_counter} items...")

                    except json.JSONDecodeError as e:
                        logger.warning(f"  Skipping invalid JSON at line {line_idx}: {e}")
                        continue

        except Exception as e:
            logger.error(f"Error reading {file_path}: {e}")
            return

        # Add to Chroma in batches
        if documents:
            logger.info(f"Adding {len(documents)} items to Chroma...")
            self._add_documents(collection, documents, metadatas, ids)

            self.stats[domain] += len(documents)
            logger.info(f"✓ Added {len(documents)} {domain} items")

    def migrate_mucgec(self):
        """Migrate MUCGEC correction data."""
        logger.info("="*50)
        logger.info("MIGRATING MUCGEC DATA...")
        logger.info("="*50)

        mucgec_dir = DATABASE_DIR / "MUCGEC"

        # Migrate guidelines
        guidelines_file = mucgec_dir / "guidelines" / "guidelines.jsonl"
        if guidelines_file.exists():
            self.migrate_jsonl_domain("mucgec", guidelines_file, chunk=True)

        # Migrate dev examples (original sentence + corrections)
        dev_file = mucgec_dir / "MuCGEC" / "MuCGEC_dev.txt"
        if dev_file.exists():
            self.migrate_mucgec_examples(dev_file)

    def migrate_mucgec_examples(self, file_path: Path):
        """Migrate MuCGEC dev examples into the same mucgec collection."""
        logger.info(f"Migrating MuCGEC examples from {file_path.name}...")

        collection = self.client.get_or_create_collection(
            name="mucgec",
            metadata={"hnsw:space": "cosine"}
        )

        documents = []
        metadatas = []
        ids = []

        try:
            detected_encoding = self._detect_text_encoding(file_path)
            logger.info(f"Detected encoding for {file_path.name}: {detected_encoding}")
            with open(file_path, 'r', encoding=detected_encoding, errors='ignore') as f:
                for line_idx, line in enumerate(f):
                    line = line.strip()
                    if not line:
                        continue

                    parts = line.split('\t')
                    if len(parts) < 2:
                        continue

                    example_id = parts[0].strip()
                    original = parts[1].strip()
                    corrections = [part.strip() for part in parts[2:] if part.strip()]

                    if not original:
                        continue

                    correction_text = "\n".join([f"改法{i + 1}: {corr}" for i, corr in enumerate(corrections[:4])])
                    text = (
                        f"原句：{original}\n"
                        f"改法数：{len(corrections)}\n"
                        f"{correction_text}"
                    )

                    documents.append(text)
                    metadatas.append({
                        "domain": "mucgec",
                        "type": "example",
                        "source": "MuCGEC_dev.txt",
                        "line_no": str(line_idx),
                        "example_id": example_id,
                        "original": original,
                        "corrections_count": str(len(corrections)),
                    })
                    ids.append(f"mucgec_example_{example_id}_{line_idx}")

            if documents:
                logger.info(f"Adding {len(documents)} MuCGEC examples to Chroma...")
                self._add_documents(collection, documents, metadatas, ids)

                self.stats["mucgec"] += len(documents)
                logger.info(f"✓ Added {len(documents)} MuCGEC examples")
        except Exception as e:
            logger.error(f"Error migrating MuCGEC examples: {e}", exc_info=True)

    def migrate_teacher(self):
        """Migrate teacher development standards."""
        logger.info("="*50)
        logger.info("MIGRATING TEACHER DEVELOPMENT DATA...")
        logger.info("="*50)

        teacher_dir = DATABASE_DIR / "teacher_development_standards"

        for jsonl_file in teacher_dir.glob("*.jsonl"):
            self.migrate_jsonl_domain("teacher", jsonl_file, chunk=True)

    def migrate_strategies(self):
        """Migrate teaching strategies."""
        logger.info("="*50)
        logger.info("MIGRATING TEACHING STRATEGIES DATA...")
        logger.info("="*50)

        strategies_dir = DATABASE_DIR / "strategies for learning Chinese"
        strategies_file = strategies_dir / "chinese_teaching_strategies.jsonl"

        if strategies_file.exists():
            self.migrate_jsonl_domain("strategies", strategies_file, chunk=True)

    def migrate_references(self):
        """Migrate reference documents."""
        logger.info("="*50)
        logger.info("MIGRATING REFERENCES DATA...")
        logger.info("="*50)

        references_dir = DATABASE_DIR / "references"

        for jsonl_file in references_dir.rglob("*.jsonl"):
            self.migrate_jsonl_domain("references", jsonl_file, chunk=True)

    def migrate_softwares(self):
        """Migrate software documentation."""
        logger.info("="*50)
        logger.info("MIGRATING SOFTWARES DATA...")
        logger.info("="*50)

        softwares_dir = DATABASE_DIR / "softwares"

        for jsonl_file in softwares_dir.glob("*.jsonl"):
            self.migrate_jsonl_domain("softwares", jsonl_file, chunk=True)

    def verify_migration(self):
        """Verify migration statistics."""
        logger.info("\n" + "="*50)
        logger.info("MIGRATION VERIFICATION")
        logger.info("="*50)

        for domain, count in self.stats.items():
            collection = self.client.get_or_create_collection(name=domain)
            actual_count = collection.count()
            status = "✓" if actual_count > 0 else "✗"
            logger.info(f"{status} {domain.upper():15} {actual_count:6} items")

        total = sum(self.stats.values())
        logger.info("-" * 50)
        logger.info(f"TOTAL: {total} items migrated")
        logger.info("="*50)

    def run_full_migration(self):
        """Run complete migration."""
        start_time = time.time()

        self.migrate_hsk()
        self.migrate_mucgec()
        self.migrate_teacher()
        self.migrate_strategies()
        self.migrate_references()
        self.migrate_softwares()

        elapsed = time.time() - start_time
        logger.info(f"\n✓ Migration completed in {elapsed:.1f} seconds")

        self.verify_migration()


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Migrate knowledge base to vector database")
    parser.add_argument("--reset", action="store_true", help="Reset vector database before migration")
    parser.add_argument("--verify-only", action="store_true", help="Only verify existing data")
    args = parser.parse_args()

    try:
        migrator = VectorDBMigrator(reset=args.reset)

        if args.verify_only:
            migrator.verify_migration()
        else:
            migrator.run_full_migration()

        logger.info("\n✓ Success! Vector database is ready to use.")
        return 0

    except Exception as e:
        logger.error(f"\n✗ Migration failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
