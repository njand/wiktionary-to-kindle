"""Ingest: downloading and filtering the Kaikki dump, and the CLI's choice of input file."""

import gzip
import io
import json
import shutil
import sys

import pytest

from wiktionary_to_kindle import cli, ingest

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
    monkeypatch.setattr(ingest.shutil, "which", lambda tool: None)
    out = tmp_path / "kaikki-la.jsonl"
    ingest.filter_dump(gz_dump, "la", out)
    assert read_words(out) == ["amo", "puella"]
    assert not ingest.partial_path(out).exists()


@pytest.mark.skipif(
    not (shutil.which("rg") and shutil.which("gzip")), reason="needs ripgrep and gzip"
)
def test_cli_filter_runs_without_a_shell(tmp_path, gz_dump):
    out = tmp_path / "kaikki-la.jsonl"
    ingest.filter_dump(gz_dump, "la", out)
    # The ripgrep prefilter also keeps the nested match; sort_jsonl drops it later
    assert {"amo", "puella"} <= set(read_words(out))


CAT = [sys.executable, "-c", "import sys; sys.stdout.write(sys.stdin.read())"]


def test_pipeline_writes_second_commands_output(tmp_path):
    echo = [sys.executable, "-c", "print('a b')"]
    out = tmp_path / "out"
    ingest.pipe_commands(echo, CAT, out)
    assert out.read_text().strip() == "a b"


def test_failed_pipeline_raises(tmp_path):
    fail = [sys.executable, "-c", "import sys; sys.exit(3)"]
    with pytest.raises(ingest.subprocess.CalledProcessError):
        ingest.pipe_commands(fail, CAT, tmp_path / "out")


def test_interrupted_filter_leaves_no_output(tmp_path, monkeypatch):
    monkeypatch.setattr(ingest.shutil, "which", lambda tool: None)
    truncated = tmp_path / "raw.jsonl.gz"
    truncated.write_bytes(gzip.compress(b'{"lang_code": "la"}\n' * 1000)[:-30])
    out = tmp_path / "kaikki-la.jsonl"
    with pytest.raises(EOFError):
        ingest.filter_dump(truncated, "la", out)
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
        ingest.urllib.request, "urlopen", lambda req: BrokenResponse(b"x" * 100)
    )
    dump = tmp_path / "raw.jsonl.gz"
    with pytest.raises(ConnectionResetError):
        ingest.download("https://example.invalid/dump.gz", dump)
    assert not dump.exists()


@pytest.fixture
def run_cli(tmp_path, monkeypatch):
    """Run the CLI up to the build, returning the input file, language and kindling it
    chose."""
    chosen = []

    def fake_build(input_file, lang, kindling, **kwargs):
        chosen.append((input_file, lang, kindling))

    def no_download(*args, **kwargs):
        raise AssertionError("downloaded although --input was given")

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(cli, "build_dictionary", fake_build)
    monkeypatch.setattr(cli, "download_kaikki_dump", no_download)
    monkeypatch.setattr(cli, "find_kindling", lambda: "kindling")

    def run(*argv):
        cli.main(list(argv))
        return chosen[-1]

    return run


@pytest.fixture
def dump(tmp_path):
    path = tmp_path / "my-dump.jsonl"
    path.write_text("", encoding="utf-8")
    return path


def test_input_is_used_without_no_download(dump, run_cli):
    assert run_cli("--lang", "la", "--input", str(dump))[0] == str(dump)


def test_lang_defaults_to_latin(dump, run_cli):
    assert run_cli("--input", str(dump))[1].code == "la"


def test_kindling_path_is_made_absolute(tmp_path, dump, run_cli):
    (tmp_path / "kindling-cli").write_text("", encoding="utf-8")
    for flag in ("--kindling", "--kindlegen"):  # --kindlegen is the old name
        kindling = run_cli("--input", str(dump), flag, "kindling-cli")[2]
        assert kindling == str(tmp_path / "kindling-cli")


@pytest.mark.parametrize("kindling", [None, "missing/kindling-cli"])
def test_missing_kindling_is_a_usage_error(dump, run_cli, monkeypatch, kindling):
    monkeypatch.setattr(cli, "find_kindling", lambda: None)
    argv = ["--input", str(dump)] + (["--kindling", kindling] if kindling else [])
    with pytest.raises(SystemExit) as exc:
        run_cli(*argv)
    assert exc.value.code == 2  # argparse's exit code for a usage error


def test_no_download_without_a_dump_is_a_usage_error(run_cli):
    with pytest.raises(SystemExit) as exc:
        run_cli("--no-download")
    assert exc.value.code == 2


def test_missing_input_is_an_error(run_cli):
    with pytest.raises(SystemExit):
        run_cli("--lang", "la", "--input", "missing.jsonl")


def test_dump_date_follows_the_dump_to_its_sorted_file(tmp_path, gz_dump, monkeypatch):
    monkeypatch.setattr(ingest.shutil, "which", lambda tool: None)
    ingest.date_path(gz_dump).write_text("2026-10-25", encoding="utf-8")
    out = tmp_path / "kaikki-la.jsonl"
    ingest.filter_dump(gz_dump, "la", out)
    assert ingest.dump_date(out) == "2026-10-25"

    sorted_file = tmp_path / "kaikki-la(sorted).jsonl"
    sorted_file.write_text("", encoding="utf-8")
    assert ingest.dump_date(sorted_file) == "2026-10-25"


def test_dump_date_without_a_record_is_the_files_date(tmp_path):
    dump = tmp_path / "my-dump.jsonl"
    dump.write_text("", encoding="utf-8")
    assert len(ingest.dump_date(dump)) == len("2026-10-25")
