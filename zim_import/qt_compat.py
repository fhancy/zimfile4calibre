"""Qt5/Qt6 enum helpers for Calibre 6–9 (qt.core)."""

from __future__ import annotations

from qt.core import QAbstractItemView, QDialog, QDialogButtonBox, QHeaderView, Qt


def _enum(owner, legacy: str, group: str | None, name: str):
    value = getattr(owner, legacy, None)
    if value is not None:
        return value
    if group is None:
        raise AttributeError(f"{owner!r} has no attribute {legacy!r}")
    nested = getattr(owner, group)
    return getattr(nested, name)


DisplayRole = _enum(Qt, "DisplayRole", "ItemDataRole", "DisplayRole")
CheckStateRole = _enum(Qt, "CheckStateRole", "ItemDataRole", "CheckStateRole")
UserRole = _enum(Qt, "UserRole", "ItemDataRole", "UserRole")
EditRole = _enum(Qt, "EditRole", "ItemDataRole", "EditRole")
Horizontal = _enum(Qt, "Horizontal", "Orientation", "Horizontal")
ItemIsEnabled = _enum(Qt, "ItemIsEnabled", "ItemFlag", "ItemIsEnabled")
ItemIsSelectable = _enum(Qt, "ItemIsSelectable", "ItemFlag", "ItemIsSelectable")
ItemIsUserCheckable = _enum(Qt, "ItemIsUserCheckable", "ItemFlag", "ItemIsUserCheckable")
NoItemFlags = getattr(Qt, "NoItemFlags", None)
if NoItemFlags is None:
    NoItemFlags = Qt.ItemFlag(0)
Checked = _enum(Qt, "Checked", "CheckState", "Checked")
Unchecked = _enum(Qt, "Unchecked", "CheckState", "Unchecked")
SelectRows = _enum(
    QAbstractItemView, "SelectRows", "SelectionBehavior", "SelectRows"
)
Stretch = _enum(QHeaderView, "Stretch", "ResizeMode", "Stretch")
Cancel = _enum(QDialogButtonBox, "Cancel", "StandardButton", "Cancel")
ActionRole = _enum(QDialogButtonBox, "ActionRole", "ButtonRole", "ActionRole")
DialogAccepted = _enum(QDialog, "Accepted", "DialogCode", "Accepted")
