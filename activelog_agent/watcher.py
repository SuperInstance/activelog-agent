"""Log watcher that tails log sources and feeds lines to rules."""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Generator


@dataclass
class LogEntry:
    """A single log line with metadata."""

    line: str
    source: str
    line_number: int
    timestamp: float = field(default_factory=time.time)

    def __str__(self) -> str:
        return self.line


@dataclass
class LogWatcher:
    """Tails one or more log sources, yielding :class:`LogEntry` objects.

    Supports real files (tail-style) and in-memory line feeds for testing.

    Attributes:
        sources: Mapping of source name → file path.
        poll_interval: Seconds between file polls when tailing.
        max_line_length: Truncate lines longer than this.
    """

    sources: dict[str, str] = field(default_factory=dict)
    poll_interval: float = 0.5
    max_line_length: int = 10_000

    # internal bookkeeping per source
    _offsets: dict[str, int] = field(default_factory=dict, repr=False)
    _stopped: bool = field(default=False, repr=False)

    # -- public API -------------------------------------------------------

    def add_source(self, name: str, path: str) -> None:
        """Register a new log source."""
        self.sources[name] = path
        self._offsets[name] = 0

    def remove_source(self, name: str) -> None:
        """Remove a log source."""
        self.sources.pop(name, None)
        self._offsets.pop(name, None)

    def stop(self) -> None:
        """Signal the watcher to stop (used by :meth:`tail`)."""
        self._stopped = True

    def read_existing(self, source: str | None = None) -> list[LogEntry]:
        """Read all current content from one or all sources.

        Args:
            source: Specific source name, or None for all.
        """
        entries: list[LogEntry] = []
        names = [source] if source else list(self.sources)
        for name in names:
            path = self.sources.get(name)
            if not path or not os.path.isfile(path):
                continue
            with open(path, "r", errors="replace") as fh:
                for i, line in enumerate(fh, 1):
                    truncated = line[: self.max_line_length]
                    entries.append(
                        LogEntry(
                            line=truncated.rstrip("\n"),
                            source=name,
                            line_number=i,
                        )
                    )
        return entries

    def tail(self, source: str) -> Generator[LogEntry, None, None]:
        """Generator that yields new lines from *source* as they appear.

        Blocks between polls. Call :meth:`stop` to break the loop.
        """
        self._stopped = False
        path = self.sources.get(source)
        if not path:
            return

        offset = self._offsets.get(source, 0)
        # If file doesn't exist yet, wait for it
        while not self._stopped:
            if os.path.isfile(path):
                break
            time.sleep(self.poll_interval)

        while not self._stopped:
            with open(path, "r", errors="replace") as fh:
                fh.seek(offset)
                line_num = offset  # approximate
                for raw in fh:
                    line_num += 1
                    truncated = raw[: self.max_line_length]
                    yield LogEntry(
                        line=truncated.rstrip("\n"),
                        source=source,
                        line_number=line_num,
                    )
                offset = fh.tell()
            self._offsets[source] = offset
            time.sleep(self.poll_interval)

    def scan_lines(self, lines: list[str], source: str = "memory") -> list[LogEntry]:
        """Convert raw strings into :class:`LogEntry` objects (for testing)."""
        return [
            LogEntry(line=l, source=source, line_number=i)
            for i, l in enumerate(lines, 1)
        ]
