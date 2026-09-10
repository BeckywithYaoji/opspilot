from pathlib import Path

import pytest

from app.rag.indexer import Chunk, RunbookIndex, chunk_markdown
from app.rag.retriever import RunbookRetriever


class DeterministicEncoder:
    dimension = 8

    def encode(self, texts):
        return [[float((sum(map(ord, text)) + i) % 17) for i in range(self.dimension)] for text in texts]


def test_chunk_markdown_preserves_heading_paragraph_metadata(tmp_path):
    path = tmp_path / "ssh.md"
    path.write_text("# SSH Troubleshooting\n\nCheck connectivity.\n\n## Verify\n\nRun ssh -v.\n")
    chunks = chunk_markdown(path)
    assert chunks[0].source == "ssh.md"
    assert chunks[0].title == "SSH Troubleshooting"
    assert chunks[0].section == "SSH Troubleshooting"
    assert "Check connectivity" in chunks[0].content
    assert chunks[1].section == "Verify"


def test_chunk_ids_are_deterministic(tmp_path):
    path = tmp_path / "a.md"
    path.write_text("# Title\n\nParagraph")
    assert chunk_markdown(path)[0].chunk_id == chunk_markdown(path)[0].chunk_id


def test_index_and_search_hits_sources_and_handles_empty_query(tmp_path):
    ssh = tmp_path / "ssh.md"; ssh.write_text("# SSH\n\nCheck port 22 and ssh connectivity.")
    perm = tmp_path / "permission-denied.md"; perm.write_text("# Permissions\n\nCheck file ownership and sudo access.")
    index = RunbookIndex(tmp_path / "qdrant", encoder=DeterministicEncoder())
    index.build([ssh, perm])
    retriever = RunbookRetriever(tmp_path / "qdrant", encoder=DeterministicEncoder())
    assert retriever.search("ssh connectivity", 2)["results"]
    assert retriever.search("ssh connectivity", 2)["results"][0]["source"] in {"ssh.md", "permission-denied.md"}
    assert retriever.search("", 3)["results"] == []


def test_missing_collection_is_safe_error(tmp_path):
    result = RunbookRetriever(tmp_path / "missing", encoder=DeterministicEncoder()).search("ssh", 2)
    assert result["status"] == "error"
