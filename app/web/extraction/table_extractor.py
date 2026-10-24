"""Extraction of structured tabular data from HTML documents."""

from app.web.extraction.html_parser import HTMLNode
from app.web.models.document import ExtractedTable


class TableExtractor:
    """Extracts structured tables preserving row/column relationships from HTML trees."""

    @classmethod
    def extract_tables(cls, root: HTMLNode) -> list[ExtractedTable]:
        """Finds and parses all <table> elements into ExtractedTable models."""
        extracted: list[ExtractedTable] = []
        table_nodes = root.find_all("table")

        for table in table_nodes:
            # 1. Caption
            caption_node = table.find("caption")
            caption_text = caption_node.get_text() if caption_node else None

            # 2. Extract rows
            all_tr = table.find_all("tr")
            if not all_tr:
                continue

            raw_rows: list[list[str]] = []
            for tr in all_tr:
                cells = [
                    child.get_text()
                    for child in tr.children
                    if isinstance(child, HTMLNode) and child.tag in ("th", "td")
                ]
                if any(cell.strip() for cell in cells):
                    raw_rows.append(cells)

            if not raw_rows:
                continue

            # Determine column headers
            columns: list[str] = []
            rows: list[list[str]] = []

            thead = table.find("thead")
            if thead:
                thead_tr = thead.find("tr")
                if thead_tr:
                    columns = [
                        c.get_text()
                        for c in thead_tr.children
                        if isinstance(c, HTMLNode) and c.tag in ("th", "td")
                    ]

            # If no <thead>, check if first row contains only <th>
            if not columns and raw_rows:
                first_tr = all_tr[0]
                first_cells = [
                    c
                    for c in first_tr.children
                    if isinstance(c, HTMLNode) and c.tag in ("th", "td")
                ]
                if all(c.tag == "th" for c in first_cells) and len(raw_rows) > 1:
                    columns = raw_rows[0]
                    rows = raw_rows[1:]
                else:
                    max_cols = max(len(r) for r in raw_rows)
                    columns = [f"Col {i + 1}" for i in range(max_cols)]
                    rows = raw_rows
            else:
                # If columns extracted from thead, filter out matching header row if duplicated
                if raw_rows and raw_rows[0] == columns:
                    rows = raw_rows[1:]
                else:
                    rows = raw_rows

            # Normalize row widths to match columns length
            normalized_rows: list[list[str]] = []
            for r in rows:
                if len(r) < len(columns):
                    r = r + [""] * (len(columns) - len(r))
                elif len(r) > len(columns):
                    # Pad columns if needed
                    columns = columns + [f"Col {i + 1}" for i in range(len(columns), len(r))]
                normalized_rows.append(r)

            extracted.append(
                ExtractedTable(
                    caption=caption_text,
                    columns=columns,
                    rows=normalized_rows,
                )
            )

        return extracted

    @classmethod
    def format_table_as_markdown(cls, table: ExtractedTable) -> str:
        """Converts an ExtractedTable into a clean Markdown table string."""
        if not table.columns and not table.rows:
            return ""

        cols = table.columns or [f"Col {i + 1}" for i in range(len(table.rows[0]))]
        header_line = "| " + " | ".join(cols) + " |"
        separator_line = "| " + " | ".join(["---"] * len(cols)) + " |"
        row_lines = ["| " + " | ".join(row) + " |" for row in table.rows]

        parts: list[str] = []
        if table.caption:
            parts.append(f"**Table: {table.caption}**")
        parts.append(header_line)
        parts.append(separator_line)
        parts.extend(row_lines)
        return "\n".join(parts)
