"""Downloading and filtering the Kaikki dump, and choosing the CLI's input file."""

import gzip
import io
import json
import shutil
import sys

import pytest

from wiktionary_to_kindle import cli, downloader

LINES = [
    {"word": "amo", "lang_code": "la"},
    {"word": "love", "lang_code": "en", "translations": [{"lang_code": "la"}]},
    {"word": "puella", "lang_code": "la"},
]


@pytest.fixture
def gz_dump(tmp_path):
    path = tmp_path / "raw.jsonl.gz"
    with gzip.open(path, "wt", encoding="utf-8") as f:
        f.writelines(json.dumps(line) + "\n" for line in LINES)
    return path


def read_words(path):
    return [json.loads(line)["word"] for line in path.read_text("utf-8").splitlines()]


def test_python_filter_keeps_top_level_language(tmp_path, gz_dump, monkeypatch):
    monkeypatch.setattr(downloader.shutil, "which", lambda tool: None)
    out = tmp_path / "kaikki-la.jsonl"
    downloader.filter_dump(gz_dump, "la", out)
    assert read_words(out) == ["amo", "puella"]
    assert not downloader.partial_path(out).exists()


@pytest.mark.skipif(
    not (shutil.which("rg") and shutil.which("gzip")), reason="needs ripgrep and gzip"
)
def test_cli_filter_runs_without_a_shell(tmp_path, gz_dump):
    out = tmp_path / "kaikki-la.jsonl"
    downloader.filter_dump(gz_dump, "la", out)
    # The ripgrep prefilter also keeps the nested match; sort_jsonl drops it later
    assert {"amo", "puella"} <= set(read_words(out))


CAT = [sys.executable, "-c", "import sys; sys.stdout.write(sys.stdin.read())"]


def test_pipeline_writes_second_commands_output(tmp_path):
    echo = [sys.executable, "-c", "print('a b')"]
    out = tmp_path / "out"
    downloader.pipe_commands(echo, CAT, out)
    assert out.read_text().strip() == "a b"


def test_failed_pipeline_raises(tmp_path):
    fail = [sys.executable, "-c", "import sys; sys.exit(3)"]
    with pytest.raises(downloader.subprocess.CalledProcessError):
        downloader.pipe_commands(fail, CAT, tmp_path / "out")


def test_interrupted_filter_leaves_no_output(tmp_path, monkeypatch):
    monkeypatch.setattr(downloader.shutil, "which", lambda tool: None)
    truncated = tmp_path / "raw.jsonl.gz"
    truncated.write_bytes(gzip.compress(b'{"lang_code": "la"}\n' * 1000)[:-30])
    out = tmp_path / "kaikki-la.jsonl"
    with pytest.raises(EOFError):
        downloader.filter_dump(truncated, "la", out)
    assert not out.exists()


class BrokenResponse(io.BytesIO):
    """A download that fails after its first chunk."""

    def info(self):
        return {"Content-Length": "100"}

    def read(self, size=-1):
        if self.tell():
            raise ConnectionResetError
        return super().read(10)

    def __exit__(self, *exc):
        return False


def test_interrupted_download_leaves_no_dump(tmp_path, monkeypatch):
    monkeypatch.setattr(
        downloader.urllib.request, "urlopen", lambda req: BrokenResponse(b"x" * 100)
    )
    dump = tmp_path / "raw.jsonl.gz"
    with pytest.raises(ConnectionResetError):
        downloader.download("https://example.invalid/dump.gz", dump)
    assert not dump.exists()


@pytest.fixture
def run_cli(tmp_path, monkeypatch):
    """Run the CLI up to the build, recording which input file it chose."""
    chosen = []

    class FakeKindleDict:
        def __init__(self, input_file, lang, kindlegen):
            chosen.append(input_file)

        def sort_jsonl(self, force=False):
            pass

        def build_dictionary(self, **kwargs):
            pass

    def no_download(*args, **kwargs):
        raise AssertionError("downloaded although --input was given")

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(cli, "KindleDict", FakeKindleDict)
    monkeypatch.setattr(cli, "download_kaikki_dump", no_download)
    monkeypatch.setattr(cli, "find_kindlegen", lambda: "kindling")

    def run(*argv):
        monkeypatch.setattr(sys, "argv", ["wiktionary-to-kindle", *argv])
        cli.main()
        return chosen[-1]

    return run


def test_input_is_used_without_no_download(tmp_path, run_cli):
    dump = tmp_path / "my-dump.jsonl"
    dump.write_text("", encoding="utf-8")
    assert run_cli("--lang", "la", "--input", str(dump)) == str(dump)


def test_missing_input_is_an_error(run_cli):
    with pytest.raises(SystemExit):
        run_cli("--lang", "la", "--input", "missing.jsonl")
