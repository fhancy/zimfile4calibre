"""Calibre toolbar action: open the ZIM import dialog."""

from __future__ import annotations

from calibre.gui2 import error_dialog, info_dialog
from calibre.gui2.actions import InterfaceAction
from calibre.utils.localization import _


class ZimImportAction(InterfaceAction):
    name = "ZIM Import"
    action_spec = (
        _("Import ZIM"),
        None,
        _("Import selected books from a Gutenberg ZIM archive"),
        None,
    )
    action_type = "current"

    def genesis(self):
        from calibre.gui2 import get_icons

        try:
            icon = get_icons("images/icon.png", self.plugin_path)
            self.qaction.setIcon(icon)
        except Exception:
            pass
        self.qaction.triggered.connect(self.show_dialog)

    def show_dialog(self):
        from qt.core import QDialog

        from .dialog import ZimImportDialog

        dialog = ZimImportDialog(self.gui, self.qaction.icon())
        if dialog.exec() != QDialog.Accepted:
            return
        records = dialog.result_payload or []
        errors = dialog.result_errors or []
        if not records:
            if errors:
                error_dialog(
                    self.gui,
                    _("ZIM Import"),
                    _("No books were imported."),
                    det_msg="\n".join(f"{book.title}: {msg}" for book, msg in errors),
                    show=True,
                )
            return
        db = self.gui.current_db.new_api
        ids, duplicates = db.add_books(records, add_duplicates=False)
        self.gui.library_view.model().refresh()
        try:
            self.gui.tags_view.recount()
        except Exception:
            pass
        extra = ""
        if duplicates:
            extra = _("\n{} already in the library (skipped).").format(len(duplicates))
        fail = ""
        if errors:
            fail = _("\n{} failed to extract.").format(len(errors))
        info_dialog(
            self.gui,
            _("ZIM Import"),
            _("Added {n} book(s) to the library.{extra}{fail}").format(
                n=len(ids), extra=extra, fail=fail
            ),
            show=True,
        )
