from __future__ import annotations

import asyncio
import shutil
import subprocess
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def _write_config(workspace: Path) -> Path:
    docs_dir = workspace / "docs"
    output_dir = workspace / "edited"
    config_path = workspace / "office-agent.toml"
    config_path.write_text(
        f"""
[offagent]
index_path = "{(workspace / 'state' / 'index.sqlite3').as_posix()}"
document_roots = ["{docs_dir.as_posix()}"]
allowed_roots = ["{docs_dir.as_posix()}"]
output_directory = "{output_dir.as_posix()}"
output_roots = ["{output_dir.as_posix()}", "{docs_dir.as_posix()}"]
embedding_model = "hash://parity"
embedding_dimensions = 48
""".strip()
    )
    return config_path


def _run_cli(config_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "offagent",
            *args,
            "--config",
            str(config_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )


def _server_params(config_path: Path) -> StdioServerParameters:
    return StdioServerParameters(
        command=sys.executable,
        args=["-m", "offagent", "mcp", "--config", str(config_path)],
    )


def _run_mcp(config_path: Path, callback):
    async def runner():
        async with stdio_client(_server_params(config_path)) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                return await callback(session)

    return asyncio.run(runner())


async def _call_tool(session: ClientSession, name: str, arguments: dict | None = None):
    result = await session.call_tool(name, arguments=arguments)
    assert not result.isError
    return result.structuredContent


def test_cli_and_mcp_parity_for_docx_cycle(tmp_path) -> None:
    cli_workspace = tmp_path / "cli"
    mcp_workspace = tmp_path / "mcp"
    (cli_workspace / "docs").mkdir(parents=True)
    (mcp_workspace / "docs").mkdir(parents=True)
    cli_docx = cli_workspace / "docs" / "golden.docx"
    mcp_docx = mcp_workspace / "docs" / "golden.docx"
    shutil.copy2(FIXTURES_DIR / "golden.docx", cli_docx)
    shutil.copy2(FIXTURES_DIR / "golden.docx", mcp_docx)
    cli_config = _write_config(cli_workspace)
    mcp_config = _write_config(mcp_workspace)

    cli_index = _run_cli(cli_config, "index", str(cli_docx))
    cli_search = _run_cli(cli_config, "search", "Supplier shall", "--type", "docx")
    cli_locate = _run_cli(cli_config, "locate", "--doc", str(cli_docx), "--paragraph", "3")
    cli_read = _run_cli(cli_config, "read", "--doc", str(cli_docx), "--item", "para:3")
    cli_replace = _run_cli(
        cli_config,
        "replace",
        "--doc",
        str(cli_docx),
        "--item",
        "para:1",
        "--text",
        "CLI parity text.",
    )

    assert cli_index.returncode == 0, cli_index.stderr
    assert "files_indexed=1" in cli_index.stdout
    assert cli_search.returncode == 0, cli_search.stderr
    assert "para:3" in cli_search.stdout
    assert cli_locate.returncode == 0, cli_locate.stderr
    assert "para:3" in cli_locate.stdout
    assert cli_read.returncode == 0, cli_read.stderr
    assert cli_read.stdout.strip() == "Supplier shall deliver by Friday."
    assert cli_replace.returncode == 0, cli_replace.stderr
    assert ".edited." in cli_replace.stdout

    def scenario(session: ClientSession):
        async def run():
            await _call_tool(session, "index_documents", {"paths": [str(mcp_docx)]})
            documents_result = await _call_tool(session, "list_documents")
            document = documents_result["documents"][0]
            search_result = await _call_tool(
                session,
                "search_documents",
                {"query": "Supplier shall", "file_type": "docx"},
            )
            locate_result = await _call_tool(
                session,
                "locate_item",
                {"document_id": document["document_id"], "locator": search_result["hits"][0]["locator"]},
            )
            read_result = await _call_tool(
                session,
                "read_item",
                {"document_id": document["document_id"], "item_id": "para:3"},
            )
            replace_result = await _call_tool(
                session,
                "replace_text",
                {
                    "document_id": document["document_id"],
                    "item_id": "para:1",
                    "new_text": "MCP parity text.",
                },
            )
            return {
                "search_item_id": search_result["hits"][0]["item_id"],
                "locate_item_id": locate_result["item"]["item_id"],
                "read_text": read_result["text"],
                "output_path": replace_result["output_path"],
            }

        return run()

    mcp_result = _run_mcp(mcp_config, scenario)

    assert mcp_result["search_item_id"] == "para:3"
    assert mcp_result["locate_item_id"] == "para:3"
    assert mcp_result["read_text"] == "Supplier shall deliver by Friday."
    assert ".edited." in mcp_result["output_path"]
