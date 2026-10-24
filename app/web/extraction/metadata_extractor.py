"""Metadata, OpenGraph, canonical URL, and header extraction from HTML."""

from typing import Any

from app.web.extraction.html_parser import HTMLNode


class MetadataExtractor:
    """Extracts page title, meta description, canonical URLs, OG tags, and publishing dates."""

    @classmethod
    def extract_metadata(cls, root: HTMLNode) -> tuple[str, dict[str, Any], str | None, str | None]:
        """Extracts title, metadata dictionary, canonical URL, and language code.

        Returns:
            tuple: (title, metadata_dict, canonical_url, language)
        """
        metadata: dict[str, Any] = {}
        og_data: dict[str, str] = {}
        canonical_url: str | None = None
        language: str | None = None
        title: str = ""

        # 1. HTML lang attribute
        html_node = root.find("html")
        if html_node:
            language = html_node.get_attr("lang") or html_node.get_attr("xml:lang")

        # 2. Title tag
        title_node = root.find("title")
        if title_node:
            title = title_node.get_text()

        # 3. Meta and Link tags
        meta_nodes = root.find_all("meta")
        for meta in meta_nodes:
            name = meta.get_attr("name", "").lower()
            prop = meta.get_attr("property", "").lower()
            content = meta.get_attr("content", "")

            if not content:
                continue

            if name == "description":
                metadata["description"] = content
            elif name == "keywords":
                metadata["keywords"] = [k.strip() for k in content.split(",") if k.strip()]
            elif name in ("author", "creator"):
                metadata["author"] = content
            elif name in ("date", "pubdate", "publishdate", "article:published_time"):
                metadata["published_date"] = content
            elif name in ("modified", "lastmod", "article:modified_time"):
                metadata["modified_date"] = content
            elif meta.get_attr("http-equiv", "").lower() == "content-language":
                language = language or content

            # OpenGraph tags
            if prop.startswith("og:"):
                og_key = prop[3:]
                og_data[og_key] = content

        if og_data:
            metadata["og"] = og_data
            if not title and "title" in og_data:
                title = og_data["title"]
            if "description" not in metadata and "description" in og_data:
                metadata["description"] = og_data["description"]

        # Canonical Link
        link_nodes = root.find_all("link")
        for link in link_nodes:
            rel = link.get_attr("rel", "").lower()
            if rel == "canonical":
                canonical_url = link.get_attr("href")
                metadata["canonical_url"] = canonical_url

        return title.strip(), metadata, canonical_url, language
