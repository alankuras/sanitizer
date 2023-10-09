import gzip
import re
from typing import List, Type, Dict
from pathlib import PosixPath


class LogFile:
    def __init__(
        self, path: Type[PosixPath] = None,
        content: List[str] = None,
        regexes: List[Dict[str, str]] = [],
        tags: str = ""
    ) -> None:
        self.path = path
        self._content = content
        self._regexes = regexes
        self._tags = tags

    def __repr__(self) -> str:
        return str(self.path)

    @property
    def content(self) -> List[str]:
        """When instantiated object doesnt have the content
        it will assume that the path points to the existing log file
        In that way it can produce a brand new archives or can process
        already existing ones, for sanitization or testing
        """
        if not self._content:
            try:
                with gzip.open(self.path, 'r') as source:
                    self._content = source.readlines()
            except gzip.BadGzipFile:
                with open(self.path, 'r') as source:
                    self._content = source.readlines()
        return self._content

    @content.setter
    def content(self, content) -> None:
        self._content = content

    def dump(self, compress: bool = True) -> None:
        if self.content:
            filename = f"{self.path}{self._tags}"
        if compress:
            filename = f"{filename}.gz"
            with gzip.open(filename, 'wt') as f:
                f.write("\n".join(self._content))
        else:
            with open(filename, 'wt') as f:
                f.write("\n".join(self._content))

    def sanitize_and_dump(self, compress: bool = True) -> None:
        if self.content and self._regexes:
            filename = f"{self.path}{self._tags}.sanitized"
            if compress:
                filename = f"{filename}.gz"
                with gzip.open(filename, 'wt') as f:
                    f.write("\n".join(self.get_sanitized_content()))
            else:
                with open(filename, 'wt') as f:
                    f.write("\n".join(self.get_sanitized_content()))

    def get_sanitized_content(self):
        sanitized_content = []
        for line in self._content:
            sanitized_line = line
            for regex in self._regexes:
                sanitized_line = re.sub(regex.get("pattern"), regex.get("replace"), f"{sanitized_line}", flags=re.IGNORECASE)
            sanitized_content.append(sanitized_line)
        return sanitized_content
