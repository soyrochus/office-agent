from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from docx import Document
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from openpyxl import load_workbook


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


def test_semantic_mcp_tools_are_discoverable_and_schema_backed(
    sample_docx,
    sample_pptx,
    sample_xlsx,
    config_path,
) -> None:
    def scenario(session: ClientSession):
        async def run():
            tools = await session.list_tools()
            tool_map = {tool.name: tool for tool in tools.tools}
            expected_tools = {
                "get_document_structure",
                "get_presentation_structure",
                "get_slide_bundle",
                "get_slide_notes",
                "get_workbook_structure",
                "get_sheet_snapshot",
                "get_document_blocks",
                "get_paragraphs",
                "get_tables",
                "get_block_bundle",
                "append_row",
                "write_table",
                "append_paragraph",
                "replace_block",
            }

            assert expected_tools <= set(tool_map)
            assert all(tool_map[name].inputSchema is not None for name in expected_tools)
            assert all(tool_map[name].outputSchema is not None for name in expected_tools)

            await _call_tool(
                session,
                "index_documents",
                {"paths": [str(sample_docx), str(sample_pptx), str(sample_xlsx)]},
            )
            documents = await _call_tool(session, "list_documents")
            docs_by_type = {document["file_type"]: document for document in documents["documents"]}

            docx_structure = await _call_tool(
                session,
                "get_document_structure",
                {"document_id": docs_by_type["docx"]["document_id"]},
            )
            pptx_bundle = await _call_tool(
                session,
                "get_slide_bundle",
                {"document_id": docs_by_type["pptx"]["document_id"], "slide_number": 1},
            )
            slide_notes = await _call_tool(
                session,
                "get_slide_notes",
                {"document_id": docs_by_type["pptx"]["document_id"], "slide_number": 2},
            )
            xlsx_snapshot = await _call_tool(
                session,
                "get_sheet_snapshot",
                {
                    "document_id": docs_by_type["xlsx"]["document_id"],
                    "sheet_name": "Notes 2026",
                    "start_cell": "A1",
                    "row_count": 2,
                    "column_count": 2,
                },
            )
            block_bundle = await _call_tool(
                session,
                "get_block_bundle",
                {"document_id": docs_by_type["docx"]["document_id"], "block_index": 4},
            )

            append_paragraph = await _call_tool(
                session,
                "append_paragraph",
                {
                    "document_id": docs_by_type["docx"]["document_id"],
                    "text": "Semantic MCP paragraph.",
                    "style_name": "Heading 2",
                },
            )
            replace_block = await _call_tool(
                session,
                "replace_block",
                {
                    "document_id": docs_by_type["docx"]["document_id"],
                    "block_index": 1,
                    "text": "Semantic MCP replacement.",
                },
            )
            append_row = await _call_tool(
                session,
                "append_row",
                {
                    "document_id": docs_by_type["xlsx"]["document_id"],
                    "sheet_name": "Notes 2026",
                    "values": ["Semantic note", "Finance"],
                },
            )
            write_table = await _call_tool(
                session,
                "write_table",
                {
                    "document_id": docs_by_type["xlsx"]["document_id"],
                    "sheet_name": "Notes 2026",
                    "rows": [["Alpha", "Owner"], ["Beta", "Approver"]],
                },
            )

            return {
                "docx_structure": docx_structure,
                "pptx_bundle": pptx_bundle,
                "slide_notes": slide_notes,
                "xlsx_snapshot": xlsx_snapshot,
                "block_bundle": block_bundle,
                "append_paragraph": append_paragraph,
                "replace_block": replace_block,
                "append_row": append_row,
                "write_table": write_table,
            }

        return run()

    result = _run_mcp(config_path, scenario)

    assert [unit["unit_type"] for unit in result["docx_structure"]["units"]] == [
        "paragraph",
        "paragraph",
        "paragraph",
        "paragraph",
        "table",
    ]
    assert result["pptx_bundle"]["notes_text"] == "Speaker notes: confirm launch owner."
    assert result["slide_notes"]["notes_text"] == "Speaker notes: review action list."
    assert [cell["coordinate"] for cell in result["xlsx_snapshot"]["cells"]] == ["A1", "B1", "A2", "B2"]
    assert result["block_bundle"]["table"]["rows"] == [["Table text to ignore"]]
    assert result["append_paragraph"]["target"]["identifier"] == "block:5"
    assert result["replace_block"]["target"]["identifier"] == "block:1"
    assert result["append_row"]["target"]["identifier"] == "Notes 2026!row:3"
    assert result["write_table"]["target"]["identifier"] == "Notes 2026!rows:3-4"

    appended_document = Document(result["append_paragraph"]["output_path"])
    replaced_document = Document(result["replace_block"]["output_path"])
    append_workbook = load_workbook(result["append_row"]["output_path"])
    table_workbook = load_workbook(result["write_table"]["output_path"])
    assert appended_document.paragraphs[-1].text == "Semantic MCP paragraph."
    assert replaced_document.paragraphs[1].text == "Semantic MCP replacement."
    assert append_workbook["Notes 2026"]["A3"].value == "Semantic note"
    assert table_workbook["Notes 2026"]["A3"].value == "Alpha"


def test_semantic_mcp_reports_format_specific_errors(sample_docx, config_path) -> None:
    def scenario(session: ClientSession):
        async def run():
            await _call_tool(session, "index_documents", {"paths": [str(sample_docx)]})
            documents = await _call_tool(session, "list_documents")
            document = documents["documents"][0]

            unsupported = await session.call_tool(
                "append_row",
                {"document_id": document["document_id"], "sheet_name": "Sheet1", "values": ["blocked"]},
            )
            assert unsupported.isError
            assert "requires a .xlsx document" in _tool_error_text(unsupported)

            table_replace = await session.call_tool(
                "replace_block",
                {"document_id": document["document_id"], "block_index": 4, "text": "blocked"},
            )
            assert table_replace.isError
            assert "table block replacement" in _tool_error_text(table_replace)

        return run()

    _run_mcp(config_path, scenario)
