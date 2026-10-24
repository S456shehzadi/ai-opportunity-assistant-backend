"""Safe, standard-library based HTML DOM tree parser."""

import html
from html.parser import HTMLParser
from typing import Self

VOID_TAGS = {
    "area",
    "base",
    "br",
    "col",
    "embed",
    "hr",
    "img",
    "input",
    "link",
    "meta",
    "param",
    "source",
    "track",
    "wbr",
}

DISCARD_TAGS = {"script", "style", "noscript", "svg", "canvas", "iframe", "template"}


class HTMLNode:
    """Represents an element in the parsed HTML document tree."""

    def __init__(
        self,
        tag: str,
        attrs: dict[str, str],
        parent: Self | None = None,
    ) -> None:
        self.tag = tag.lower()
        self.attrs = {k.lower(): v for k, v in attrs.items()}
        self.children: list[HTMLNode | str] = []
        self.parent = parent

    def add_child(self, child: "HTMLNode | str") -> None:
        self.children.append(child)

    def get_attr(self, name: str, default: str | None = None) -> str | None:
        return self.attrs.get(name.lower(), default)

    def get_text(self, separator: str = " ", strip: bool = True) -> str:
        """Recursively collects text content of node and its descendants."""
        parts: list[str] = []
        for child in self.children:
            if isinstance(child, str):
                text = child.strip() if strip else child
                if text:
                    parts.append(text)
            else:
                child_text = child.get_text(separator=separator, strip=strip)
                if child_text:
                    parts.append(child_text)
        joined = separator.join(parts)
        return " ".join(joined.split()) if strip else joined

    def find_all(self, tag_name: str | list[str]) -> list["HTMLNode"]:
        """Finds all descendant nodes matching the specified tag name(s)."""
        tags = [t.lower() for t in tag_name] if isinstance(tag_name, list) else [tag_name.lower()]
        results: list[HTMLNode] = []

        def _traverse(node: HTMLNode) -> None:
            for child in node.children:
                if isinstance(child, HTMLNode):
                    if child.tag in tags:
                        results.append(child)
                    _traverse(child)

        _traverse(self)
        return results

    def find(self, tag_name: str | list[str]) -> "HTMLNode | None":
        """Finds the first descendant node matching the specified tag name(s)."""
        matches = self.find_all(tag_name)
        return matches[0] if matches else None


class SafeHTMLTreeBuilder(HTMLParser):
    """Builds a sanitized HTMLNode DOM tree from HTML markup."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.root = HTMLNode(tag="[document]", attrs={})
        self.current: HTMLNode = self.root
        self._discard_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        clean_tag = tag.lower()
        attrs_dict = {k: (v or "") for k, v in attrs}

        if clean_tag in DISCARD_TAGS:
            self._discard_depth += 1
            return

        if self._discard_depth > 0:
            return

        new_node = HTMLNode(tag=clean_tag, attrs=attrs_dict, parent=self.current)
        self.current.add_child(new_node)

        if clean_tag not in VOID_TAGS:
            self.current = new_node

    def handle_endtag(self, tag: str) -> None:
        clean_tag = tag.lower()

        if clean_tag in DISCARD_TAGS:
            if self._discard_depth > 0:
                self._discard_depth -= 1
            return

        if self._discard_depth > 0:
            return

        if clean_tag in VOID_TAGS:
            return

        # Ascend tree until matching tag found or root reached
        walker: HTMLNode | None = self.current
        while walker is not None and walker != self.root:
            if walker.tag == clean_tag:
                if walker.parent:
                    self.current = walker.parent
                break
            walker = walker.parent

    def handle_data(self, data: str) -> None:
        if self._discard_depth > 0:
            return
        unescaped = html.unescape(data)
        if unescaped.strip():
            self.current.add_child(unescaped)


def parse_html_tree(raw_html: str) -> HTMLNode:
    """Parses raw HTML markup into a clean HTMLNode tree."""
    builder = SafeHTMLTreeBuilder()
    builder.feed(raw_html)
    return builder.root
