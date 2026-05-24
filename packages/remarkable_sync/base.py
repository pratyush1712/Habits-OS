"""Shared types for reMarkable sync adapters.

Adapters only handle generated, machine-owned PDFs. They must never inspect or
modify handwritten notebook internals.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, Protocol


MACHINE_ROOT_FOLDER = "HabitOS"
SyncAction = Literal["upload", "update", "list"]
SyncStatus = Literal[
    "not_configured",
    "manual_required",
    "uploaded",
    "updated",
    "unsupported",
]


@dataclass(frozen=True)
class MachineOwnedTarget:
    month: str
    folder_path: tuple[str, ...]
    document_name: str

    @property
    def filename(self) -> str:
        return f"{self.document_name}.pdf"

    @property
    def display_path(self) -> str:
        return "/".join((*self.folder_path, self.filename))


@dataclass(frozen=True)
class SyncRequest:
    local_pdf_path: Path
    document_name: str
    folder_path: tuple[str, ...]
    dry_run: bool = True

    @property
    def target_path(self) -> str:
        return "/".join((*self.folder_path, f"{self.document_name}.pdf"))


@dataclass(frozen=True)
class SyncResult:
    adapter: str
    action: SyncAction
    dry_run: bool
    target_path: str
    status: SyncStatus
    message: str
    local_pdf_path: Path | None = None
    device_mutated: bool = False
    instructions: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class RemarkableDocument:
    id: str
    name: str
    path: str
    type: str
    machine_owned: bool = False


class RemarkableSyncAdapter(Protocol):
    name: str

    async def upload_pdf(self, request: SyncRequest) -> SyncResult:
        ...

    async def update_pdf(self, request: SyncRequest) -> SyncResult:
        ...

    async def list_documents(self) -> list[RemarkableDocument]:
        ...


def build_machine_owned_target(month: str) -> MachineOwnedTarget:
    """Backward-compatible alias for the current month target."""

    return build_current_month_target(month)


def build_current_month_target(month: str) -> MachineOwnedTarget:
    """Build the machine-owned current dashboard target.

    The folder prefix is intentionally fixed so adapters can distinguish
    generated HabitOS artifacts from human-owned notebooks.
    """

    year, month_num = _parse_month(month)
    month_str = f"{year:04d}-{month_num:02d}"
    return MachineOwnedTarget(
        month=month_str,
        folder_path=(MACHINE_ROOT_FOLDER, "00 Current"),
        document_name=f"00 Current Month - {month_str} Habit Dashboard",
    )


def build_archive_month_target(month: str) -> MachineOwnedTarget:
    """Build the machine-owned archive target for a finalized month."""

    year, month_num = _parse_month(month)
    month_str = f"{year:04d}-{month_num:02d}"
    return MachineOwnedTarget(
        month=month_str,
        folder_path=(MACHINE_ROOT_FOLDER, f"{year:04d}", "Archive"),
        document_name=f"{month_str} Habit Dashboard",
    )


def _parse_month(month: str) -> tuple[int, int]:
    try:
        year_s, month_s = month.split("-")
        year = int(year_s)
        month_num = int(month_s)
    except ValueError as e:
        raise ValueError(f"month must be YYYY-MM, got {month!r}") from e
    if month_num < 1 or month_num > 12:
        raise ValueError(f"month must be YYYY-MM, got {month!r}")
    return year, month_num
