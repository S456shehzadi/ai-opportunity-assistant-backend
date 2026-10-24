"""Main content extraction, boilerplate stripping, and structural preservation."""

import re

from app.web.extraction.html_parser import HTMLNode
from app.web.extraction.table_extractor import TableExtractor
from app.web.models.document import ExtractedHeading, ExtractedTable

BOILERPLATE_TAGS = {"header", "footer", "nav", "aside", "form"}

BOILERPLATE_PATTERNS = re.compile(
    r"(?:cookie[-_]?banner|cookie[-_]?consent|cookie[-_]?notice|ad[-_]?container|"
    r"advertisement|sidebar|newsletter|social[-_]?share|disclaimer|breadcrumb|"
    r"site[-_]?footer|site[-_]?header|nav[-_]?menu)",
    re.IGNORECASE,
)

HEADING_TAGS = {"h1": 1, "h2": 2, "h3": 3, "h4": 4, "h5": 5, "h6": 6}


class MainContentExtractor:
    """Extracts meaningful content from HTML markup while stripping page boilerplate."""

    @classmethod
    def extract_clean_content(
        cls,
        root: HTMLNode,
        extracted_tables: list[ExtractedTable] | None = None,
    ) -> tuple[str, list[ExtractedHeading], int]:
        """Extracts sanitized structured clean text, headings list, and word count.

        Returns:
            tuple: (clean_text, list[ExtractedHeading], word_count)
        """
        # 1. Prune boilerplate nodes
        cls._prune_boilerplate(root)

        # 2. Extract Headings hierarchy
        headings = cls._extract_headings(root)

        # 3. Locate Main Content Root Node
        content_root = cls._find_content_root(root)

        # 4. Render clean structured text
        clean_text = cls._render_node_text(content_root)

        # If tables were extracted and not represented, append markdown tables
        if extracted_tables:
            table_mds = [
                TableExtractor.format_table_as_markdown(t) for t in extracted_tables if t.rows
            ]
            if table_mds:
                clean_text = clean_text + "\n\n" + "\n\n".join(table_mds)

        # Normalize whitespace and compute word count
        lines = [line.strip() for line in clean_text.split("\n")]
        # Collapse multiple blank lines
        cleaned_lines: list[str] = []
        prev_blank = False
        for line in lines:
            if not line:
                if not prev_blank:
                    cleaned_lines.append("")
                    prev_blank = True
            else:
                cleaned_lines.append(line)
                prev_blank = False

        final_text = "\n".join(cleaned_lines).strip()
        word_count = len(final_text.split())

        return final_text, headings, word_count

    @classmethod
    def _prune_boilerplate(cls, node: HTMLNode) -> None:
        """Recursively removes navigation, footer, cookie banners, and hidden elements."""
        pruned_children: list[HTMLNode | str] = []

        for child in node.children:
            if isinstance(child, str):
                pruned_children.append(child)
                continue

            # Tag check
            if child.tag in BOILERPLATE_TAGS:
                continue

            # Hidden element checks
            if child.get_attr("hidden") is not None or child.get_attr("aria-hidden") == "true":
                continue

            style = child.get_attr("style", "").lower()
            if "display:none" in style or "visibility:hidden" in style:
                continue

            # Class/ID boilerplate pattern checks
            class_str = child.get_attr("class", "")
            id_str = child.get_attr("id", "")
            if BOILERPLATE_PATTERNS.search(class_str) or BOILERPLATE_PATTERNS.search(id_str):
                continue

            # Recurse
            cls._prune_boilerplate(child)
            pruned_children.append(child)

        node.children = pruned_children

    @classmethod
    def _extract_headings(cls, root: HTMLNode) -> list[ExtractedHeading]:
        """Finds all H1-H6 headings preserving document sequence."""
        headings: list[ExtractedHeading] = []
        heading_nodes = root.find_all(list(HEADING_TAGS.keys()))

        for node in heading_nodes:
            level = HEADING_TAGS.get(node.tag, 1)
            text = node.get_text()
            if text:
                headings.append(ExtractedHeading(level=level, text=text))

        return headings

    @classmethod
    def _find_content_root(cls, root: HTMLNode) -> HTMLNode:
        """Finds the most specific semantic content container (<main>, <article>, or <body>)."""
        for tag in ("main", "article"):
            candidates = root.find_all(tag)
            for cand in candidates:
                if len(cand.get_text()) > 150:
                    return cand

        # Check role="main"
        all_divs = root.find_all("div")
        for div in all_divs:
            if div.get_attr("role") == "main" and len(div.get_text()) > 150:
                return div

        body = root.find("body")
        return body or root

    @classmethod
    def _render_node_text(cls, node: HTMLNode) -> str:
        """Renders HTML node tree to clean text preserving headings, paragraphs, and lists."""
        output: list[str] = []

        def _walk(n: HTMLNode | str) -> None:
            if isinstance(n, str):
                cleaned = n.strip()
                if cleaned:
                    output.append(cleaned)
                return

            tag = n.tag

            if tag in HEADING_TAGS:
                level = HEADING_TAGS[tag]
                prefix = "#" * level
                text = n.get_text()
                if text:
                    output.append(f"\n{prefix} {text}\n")
                return

            if tag == "p":
                text = n.get_text()
                if text:
                    output.append(f"\n{text}\n")
                return

            if tag in ("ul", "ol"):
                output.append("\n")
                for li in n.children:
                    if isinstance(li, HTMLNode) and li.tag == "li":
                        li_text = li.get_text()
                        if li_text:
                            output.append(f"- {li_text}")
                output.append("\n")
                return

            if tag == "blockquote":
                text = n.get_text()
                if text:
                    output.append(f"\n> {text}\n")
                return

            if tag in ("table", "thead", "tbody", "tr", "th", "td"):
                # Tables are formatted by TableExtractor
                return

            for child in n.children:
                _walk(child)

        _walk(node)
        return "\n".join(output)
