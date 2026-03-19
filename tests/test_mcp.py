from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from docx import Document
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from openpyxl import load_workbook
from pptx import Presentation


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
    assert not result.isError, _tool_error_text(result)
    return result.structuredContent


def _tool_error_text(result) -> str:
    parts: list[str] = []
    for content in result.content:
        text = getattr(content, "text", None)
        if text is not None:
            parts.append(text)
    return "\n".join(parts)


def test_mcp_lists_tools_and_runs_docx_flow(sample_docx, config_path) -> None:
    def scenario(session: ClientSession):
        async def run():
            tools = await session.list_tools()
            tool_map = {tool.name: tool for tool in tools.tools}
            assert {
                "index_documents",
                "refresh_document",
                "list_documents",
                "search_documents",
                "locate_item",
                "read_item",
                "replace_text",
                "append_text",
                "write_cell",
            } <= set(tool_map)
            assert tool_map["search_documents"].inputSchema
            assert tool_map["search_documents"].outputSchema

            index_result = await _call_tool(
                session,
                "index_documents",
                {"paths": [str(sample_docx)]},
            )
            assert index_result["files_indexed"] == 1

            documents_result = await _call_tool(session, "list_documents")
            document = documents_result["documents"][0]
            assert document["path"] == str(sample_docx)

            search_result = await _call_tool(
                session,
                "search_documents",
                {"query": "Supplier shall", "file_type": "docx"},
            )
            hit = search_result["hits"][0]
            assert hit["item_id"] == "para:3"

            locate_result = await _call_tool(
                session,
                "locate_item",
                {"document_id": document["document_id"], "locator": hit["locator"]},
            )
            assert locate_result["item"]["item_id"] == "para:3"

            read_result = await _call_tool(
                session,
                "read_item",
                {"document_id": document["document_id"], "item_id": "para:3"},
            )
            assert read_result["text"] == "Supplier shall deliver by Friday."

            replace_result = await _call_tool(
                session,
                "replace_text",
                {
                    "document_id": document["document_id"],
                    "item_id": "para:1",
                    "new_text": "MCP replaced text.",
                },
            )
            append_result = await _call_tool(
                session,
                "append_text",
                {
                    "document_id": replace_result["item"]["document_id"],
                    "item_id": "para:2",
                    "text_to_add": "MCP appended text.",
                },
            )

            refresh_result = await _call_tool(
                session,
                "refresh_document",
                {"document_id": document["document_id"]},
            )
            assert refresh_result["files_indexed"] == 1

            return append_result

        return run()

    append_result = _run_mcp(config_path, scenario)

    original_document = Document(str(sample_docx))
    final_document = Document(append_result["output_path"])
    assert original_document.paragraphs[1].text == "Alpha paragraph for search."
    assert final_document.paragraphs[1].text == "MCP replaced text."
    assert final_document.paragraphs[1].runs[0].bold is True
    assert final_document.paragraphs[2].text == "MCP appended text."


def test_mcp_pptx_and_xlsx_round_trips(sample_pptx, sample_xlsx, config_path) -> None:
    def scenario(session: ClientSession):
        async def run():
            await _call_tool(session, "index_documents", {"paths": [str(sample_pptx), str(sample_xlsx)]})

            documents_result = await _call_tool(session, "list_documents")
            docs_by_type = {document["file_type"]: document for document in documents_result["documents"]}

            pptx_search = await _call_tool(
                session,
                "search_documents",
                {"query": "Supplier shall", "file_type": "pptx"},
            )
            pptx_hit = pptx_search["hits"][0]
            pptx_read = await _call_tool(
                session,
                "read_item",
                {"document_id": docs_by_type["pptx"]["document_id"], "item_id": pptx_hit["item_id"]},
            )
            assert "Supplier shall present the rollout plan." in pptx_read["text"]

            editable_search = await _call_tool(
                session,
                "search_documents",
                {"query": "Editable speaker notes", "file_type": "pptx"},
            )
            editable_item_id = editable_search["hits"][0]["item_id"]
            pptx_replace = await _call_tool(
                session,
                "replace_text",
                {
                    "document_id": docs_by_type["pptx"]["document_id"],
                    "item_id": editable_item_id,
                    "new_text": "MCP updated speaker notes.",
                },
            )
            pptx_append = await _call_tool(
                session,
                "append_text",
                {
                    "document_id": pptx_replace["item"]["document_id"],
                    "item_id": editable_item_id,
                    "text_to_add": "\nMCP appended action.",
                },
            )

            xlsx_search = await _call_tool(
                session,
                "search_documents",
                {"query": "Supplier shall", "file_type": "xlsx"},
            )
            xlsx_hit = xlsx_search["hits"][0]
            xlsx_locate = await _call_tool(
                session,
                "locate_item",
                {"document_id": docs_by_type["xlsx"]["document_id"], "locator": xlsx_hit["locator"]},
            )
            assert xlsx_locate["item"]["item_id"] == "sheet:Notes 2026!A1"

            xlsx_write = await _call_tool(
                session,
                "write_cell",
                {
                    "document_id": docs_by_type["xlsx"]["document_id"],
                    "sheet": "Budget2026",
                    "cell": "B2",
                    "value": "125001",
                },
            )
            xlsx_append = await _call_tool(
                session,
                "append_text",
                {
                    "document_id": xlsx_write["item"]["document_id"],
                    "item_id": "sheet:Notes 2026!B5",
                    "text_to_add": "MCP added note.",
                },
            )

            return {"pptx_output": pptx_append["output_path"], "xlsx_output": xlsx_append["output_path"]}

        return run()

    outputs = _run_mcp(config_path, scenario)

    presentation = Presentation(outputs["pptx_output"])
    editable_shape = next(shape for shape in presentation.slides[1].shapes if shape.has_text_frame)
    assert editable_shape.text_frame.text == "MCP updated speaker notes.\nMCP appended action."

    workbook = load_workbook(outputs["xlsx_output"])
    assert workbook["Budget2026"]["B2"].value == 125001
    assert workbook["Notes 2026"]["B5"].value == "MCP added note."


def test_mcp_returns_structured_errors(sample_docx, sample_xlsx, config_path) -> None:
    def scenario(session: ClientSession):
        async def run():
            await _call_tool(session, "index_documents", {"paths": [str(sample_docx), str(sample_xlsx)]})
            documents_result = await _call_tool(session, "list_documents")
            docs_by_path = {document["path"]: document for document in documents_result["documents"]}

            invalid_locator = await session.call_tool(
                "locate_item",
                {"document_id": docs_by_path[str(sample_docx)]["document_id"], "locator": "slide:1:shape:2"},
            )
            assert invalid_locator.isError
            assert "DOCX locate_item expects" in _tool_error_text(invalid_locator)

            workbook = load_workbook(sample_xlsx)
            del workbook["Budget2026"]
            workbook.save(sample_xlsx)

            stale_result = await session.call_tool(
                "write_cell",
                {
                    "document_id": docs_by_path[str(sample_xlsx)]["document_id"],
                    "sheet": "Budget2026",
                    "cell": "B2",
                    "value": "125001",
                },
            )
            assert stale_result.isError
            assert "stale locator" in _tool_error_text(stale_result)

        return run()

    _run_mcp(config_path, scenario)
