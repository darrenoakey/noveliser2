import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any, Generator

import pytest

sys.path.insert(0, str(Path(__file__).parent))

from retrieval_memory import _cosine, split_sentences  # noqa: E402


EMBEDDING_SERVICE_SOURCE = r"""
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

def vector(text):
    lowered = text.lower()
    groups = (
        ("truck", "vehicle", "pickup", "jeff"),
        ("telescope", "balcony"),
        ("kitchen", "toast"),
        ("lighthouse", "clara"),
    )
    return [float(sum(lowered.count(word) for word in group)) for group in groups]

class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        return

    def send_json(self, body):
        encoded = json.dumps(body).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def do_POST(self):
        length = int(self.headers["Content-Length"])
        request = json.loads(self.rfile.read(length))
        texts = request["params"]["texts"]
        self.send_json({"job_id": "integration-embedding"})
        self.server.result = {
            "embeddings": [vector(text) for text in texts],
            "dimension": 4,
            "count": len(texts),
            "model_repository": "local-lexical-embedding",
        }

    def do_GET(self):
        self.send_json({"status": "completed", "result": self.server.result})

server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
server.result = {}
print(server.server_port, flush=True)
server.serve_forever()
"""


@pytest.fixture
def embedding_service() -> Generator[str, None, None]:
    process = subprocess.Popen(
        [sys.executable, "-c", EMBEDDING_SERVICE_SOURCE],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    assert process.stdout is not None
    port = int(process.stdout.readline().strip())
    try:
        yield f"http://127.0.0.1:{port}"
    finally:
        process.terminate()
        _, errors = process.communicate(timeout=5)
        assert process.returncode in {0, -15}
        assert not errors


def run_memory_integration(tmp_path: Path, service_url: str) -> dict[str, Any]:
    home = tmp_path / "home"
    config_directory = home / ".daz-agent-sdk"
    config_directory.mkdir(parents=True)
    (config_directory / "config.yaml").write_text(
        f"providers:\n  arbiter:\n    base_url: {service_url}\n",
        encoding="utf-8",
    )
    source_directory = Path(__file__).resolve().parent
    memory_path = tmp_path / "memory.json"
    child_source = r"""
import json
import sys
from pathlib import Path

sys.path.insert(0, sys.argv[1])
from retrieval_memory import RetrievalMemory

memory = RetrievalMemory()
first_count = memory.ensure_section(
    "ch1.s1",
    "Jeff drove a battered red pickup truck. The kitchen smelled of burnt toast every morning. "
    "Clara kept a telescope on the lighthouse balcony.",
)
second_count = memory.ensure_section("ch1.s1", "Different text with the same section identifier.")
vehicle_hit = memory.retrieve("What vehicle does Jeff own?", k=1)
memory.save(Path(sys.argv[2]))
loaded = RetrievalMemory.load(Path(sys.argv[2]))
loaded_hit = loaded.retrieve("Jeff's truck", k=1)
excluded = loaded.retrieve("Jeff truck", k=5, exclude_section="ch1.s1")
print(json.dumps({
    "first_count": first_count,
    "second_count": second_count,
    "vehicle_hit": vehicle_hit,
    "loaded_length": len(loaded),
    "section_present": "ch1.s1" in loaded,
    "loaded_hit": loaded_hit,
    "excluded": excluded,
}))
"""
    process_environment = os.environ.copy()
    process_environment["HOME"] = str(home)
    completed = subprocess.run(
        [sys.executable, "-c", child_source, str(source_directory), str(memory_path)],
        cwd=tmp_path,
        env=process_environment,
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(completed.stdout)


def test_split_sentences_filters_and_caps() -> None:
    text = "Jeff opened the blue door slowly. He nodded. The dog was a golden retriever named Max."
    sentences = split_sentences(text)
    assert any("blue door" in sentence for sentence in sentences)
    assert any("golden retriever" in sentence for sentence in sentences)
    assert all(len(sentence) <= 400 for sentence in sentences)
    assert not any(sentence.strip() == "He nodded." for sentence in sentences)


def test_cosine_identity_and_orthogonal() -> None:
    assert _cosine([1.0, 0.0], [1.0, 0.0]) == pytest.approx(1.0)
    assert _cosine([1.0, 0.0], [0.0, 1.0]) == pytest.approx(0.0)


def test_memory_uses_http_config_and_persists(
    tmp_path: Path, embedding_service: str
) -> None:
    result = run_memory_integration(tmp_path, embedding_service)
    assert result["first_count"] == 3
    assert result["second_count"] == 0
    assert "pickup truck" in result["vehicle_hit"][0].lower()
    assert result["loaded_length"] == 3
    assert result["section_present"] is True
    assert "pickup truck" in result["loaded_hit"][0].lower()
    assert result["excluded"] == []
