from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from offagent.app.services import AppServices
from offagent.config import load_config


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


def test_mcp_search_objects_supports_mode(golden_config_path, golden_docx) -> None:
    services = AppServices(load_config(golden_config_path))
    services.index_document(golden_docx, with_embeddings=True)

    def scenario(session: ClientSession):
        async def run():
            tools = await session.list_tools()
            search_tool = next(tool for tool in tools.tools if tool.name == "search_objects")
            assert "mode" in search_tool.inputSchema["properties"]

            documents_result = await _call_tool(session, "list_documents")
            document = documents_result["documents"][0]
            semantic = await _call_tool(
                session,
                "search_objects",
                {
                    "query": "supplier shall",
                    "file_type": "docx",
                    "document_id": document["document_id"],
                    "mode": "semantic",
                },
            )
            hybrid = await _call_tool(
                session,
                "search_objects",
                {
                    "query": "supplier shall",
                    "file_type": "docx",
                    "document_id": document["document_id"],
                    "mode": "hybrid",
                },
            )
            return {"semantic": semantic, "hybrid": hybrid}

        return run()

    result = _run_mcp(golden_config_path, scenario)

    assert result["semantic"]["hits"][0]["match_mode"] == "semantic"
    assert "semantic" in result["semantic"]["hits"][0]["scores"]
    assert result["hybrid"]["hits"][0]["match_mode"] == "hybrid"
    assert "final" in result["hybrid"]["hits"][0]["scores"]


def test_mcp_search_documents_alias_preserves_pre_v2_shape(golden_config_path, golden_docx) -> None:
    services = AppServices(load_config(golden_config_path))
    services.index_document(golden_docx, with_embeddings=True)

    def scenario(session: ClientSession):
        async def run():
            alias_result = await _call_tool(
                session,
                "search_documents",
                {
                    "query": "supplier shall",
                    "file_type": "docx",
                    "mode": "semantic",
                },
            )
            return alias_result["hits"][0]

        return run()

    hit = _run_mcp(golden_config_path, scenario)

    assert "match_mode" not in hit
    assert "object_type" not in hit
    assert hit["item_type"] == "paragraph"
