from __future__ import annotations

import textwrap


class Indent:
    def __init__(self, char: str = " " * 4, indent: int = 0) -> None:
        self._char = char
        self.indent = indent

    def format(self, text: str) -> str:
        return textwrap.indent(text, self._char * self.indent)
