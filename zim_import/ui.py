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
    action_type = "global"

    def genesis(self):
        # Connect first so a later icon failure cannot leave the action dead.
        self.qaction.triggered.connect(self.show_dialog)
        try:
            from qt.core import QIcon, QPixmap

            data = self.load_resources(["images/icon.png"]).get("images/icon.png")
            if data:
                pixmap = QPixmap()
                pixmap.loadFromData(data)
                self.qaction.setIcon(QIcon(pixmap))
        except Exception:
            pass

    def show_dialog(self, *args):
        try:
            from .dialog import ZimImportDialog
            from .qt_compat import DialogAccepted

            dialog = ZimImportDialog(self.gui, self.qaction.icon())
            if dialog.exec() != DialogAccepted:
                return
            records = dialog.result_payload or []
            errors = dialog.result_errors or []
            if not records:
                if errors:
                    error_dialog(
                        self.gui,
                        _("ZIM Import"),
                        _("No books were imported."),
                        det_msg="\n".join(
                            f"{book.title}: {msg}" for book, msg in errors
                        ),
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
                extra = _("\n{} already in the library (skipped).").format(
                    len(duplicates)
                )
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
        except Exception as exc:
            error_dialog(
                self.gui,
                _("ZIM Import"),
                _("Could not open the import dialog."),
                det_msg=str(exc),
                show=True,
            )
            raise
