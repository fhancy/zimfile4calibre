"""Qt dialog: pick a ZIM, select Gutenberg books, extract for Calibre."""

from __future__ import annotations

from pathlib import Path

from qt.core import (
    QAbstractTableModel,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QModelIndex,
    QProgressBar,
    QPushButton,
    QSortFilterProxyModel,
    QTableView,
    QThread,
    QVBoxLayout,
    pyqtSignal,
)

from calibre.gui2 import error_dialog
from calibre.ptempfile import PersistentTemporaryDirectory
from calibre.utils.localization import _

from .gutenberg_catalog import GutenbergBook, list_gutenberg_books
from .plugin_import import extract_records, filter_books_for_import
from .qt_compat import (
    ActionRole,
    Cancel,
    Checked,
    CheckStateRole,
    DisplayRole,
    EditRole,
    Horizontal,
    ItemIsEnabled,
    ItemIsSelectable,
    ItemIsUserCheckable,
    NoItemFlags,
    SelectRows,
    Stretch,
    Unchecked,
    UserRole,
)
from .zim_reader import ZimArchive, ZimError


class CatalogWorker(QThread):
    loaded = pyqtSignal(object)
    failed = pyqtSignal(str)

    def __init__(self, zim_path: str, parent=None):
        QThread.__init__(self, parent)
        self.zim_path = zim_path

    def run(self):
        try:
            with ZimArchive(self.zim_path) as archive:
                books = list_gutenberg_books(archive)
            self.loaded.emit(books)
        except (ZimError, OSError) as exc:
            self.failed.emit(str(exc))


class ImportWorker(QThread):
    progressed = pyqtSignal(int, int, str)
    finished_ok = pyqtSignal(object, object)
    failed = pyqtSignal(str)

    def __init__(
        self,
        zim_path: str,
        books: list[GutenbergBook],
        dest: str,
        html_format: str = "epub",
        parent=None,
    ):
        QThread.__init__(self, parent)
        self.zim_path = zim_path
        self.books = books
        self.dest = dest
        self.html_format = html_format

    def run(self):
        try:
            with ZimArchive(self.zim_path) as archive:
                records, errors = extract_records(
                    archive,
                    self.books,
                    Path(self.dest),
                    html_format=self.html_format,
                    progress=lambda i, n, title: self.progressed.emit(i, n, title),
                )
            self.finished_ok.emit(records, errors)
        except (ZimError, OSError) as exc:
            self.failed.emit(str(exc))


class BookTableModel(QAbstractTableModel):
    # EPUB/PDF/HTML = formats present in the ZIM (read-only), not output choice.
    HEADERS = ("", "ID", _("Title"), "EPUB", "PDF", "HTML")

    def __init__(self, books: list[GutenbergBook] | None = None, parent=None):
        QAbstractTableModel.__init__(self, parent)
        self.books = list(books or [])
        self.checked: set[int] = set()

    def rowCount(self, parent=QModelIndex()):
        if parent.isValid():
            return 0
        return len(self.books)

    def columnCount(self, parent=QModelIndex()):
        return 6

    def headerData(self, section, orientation, role=DisplayRole):
        if orientation == Horizontal and role == DisplayRole:
            return self.HEADERS[section]
        return None

    def flags(self, index):
        if not index.isValid():
            return NoItemFlags
        flags = ItemIsEnabled | ItemIsSelectable
        if index.column() == 0:
            flags |= ItemIsUserCheckable
        return flags

    @staticmethod
    def _mark(present: bool) -> str:
        return "✅" if present else ""

    def data(self, index, role=DisplayRole):
        if not index.isValid():
            return None
        book = self.books[index.row()]
        col = index.column()
        if role == CheckStateRole and col == 0:
            return Checked if id(book) in self.checked else Unchecked
        if role == DisplayRole:
            if col == 1:
                return str(book.gutenberg_id)
            if col == 2:
                return book.title
            if col == 3:
                return self._mark(book.has_epub)
            if col == 4:
                return self._mark(book.has_pdf)
            if col == 5:
                # Catalog entries are HTML book pages; HTML is always available.
                return self._mark(True)
        if role == UserRole:
            return book
        return None

    def setData(self, index, value, role=EditRole):
        if not index.isValid() or index.column() != 0:
            return False
        # Qt may pass ItemDataRole enum or plain int.
        try:
            role_ok = int(role) == int(CheckStateRole)
        except (TypeError, ValueError):
            role_ok = role == CheckStateRole
        if not role_ok:
            return False
        book = self.books[index.row()]
        key = id(book)
        # Calibre/Qt6 often sends CheckState as int (2/0); enum == int is False.
        try:
            is_checked = int(value) == int(Checked.value)
        except (TypeError, ValueError, AttributeError):
            is_checked = value == Checked
        if is_checked:
            self.checked.add(key)
        else:
            self.checked.discard(key)
        self.dataChanged.emit(index, index, [CheckStateRole])
        return True

    def reset_books(self, books: list[GutenbergBook]):
        self.beginResetModel()
        self.books = list(books)
        self.checked = set()
        self.endResetModel()

    def selected_books(self) -> list[GutenbergBook]:
        return [book for book in self.books if id(book) in self.checked]

    def set_checked_books(self, books: list[GutenbergBook], checked: bool):
        self.beginResetModel()
        keys = {id(book) for book in books}
        if checked:
            self.checked |= keys
        else:
            self.checked -= keys
        self.endResetModel()


class BookFilterProxy(QSortFilterProxyModel):
    def __init__(self, parent=None):
        QSortFilterProxyModel.__init__(self, parent)
        self.query = ""
        self.epub_only = False

    def set_query(self, text: str):
        self.query = text.strip().lower()
        self.invalidateFilter()

    def set_epub_only(self, value: bool):
        self.epub_only = value
        self.invalidateFilter()

    def filterAcceptsRow(self, source_row, source_parent):
        model = self.sourceModel()
        book = model.books[source_row]
        if self.epub_only and not book.has_epub:
            return False
        if not self.query:
            return True
        haystack = f"{book.gutenberg_id} {book.title}".lower()
        return self.query in haystack


class ZimImportDialog(QDialog):
    def __init__(self, gui, icon=None):
        QDialog.__init__(self, gui)
        self.gui = gui
        self.result_payload = []
        self.result_errors = []
        self._zim_path = ""
        self._temp_dir = None
        self._catalog_worker = None
        self._import_worker = None
        self.setWindowTitle(_("Import books from ZIM"))
        if icon is not None and not icon.isNull():
            self.setWindowIcon(icon)
        self.resize(820, 560)
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)

        path_row = QHBoxLayout()
        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText(_("Path to a Gutenberg .zim file"))
        browse = QPushButton(_("Browse…"))
        browse.clicked.connect(self._browse)
        load = QPushButton(_("Load catalog"))
        load.clicked.connect(self._load_catalog)
        path_row.addWidget(self.path_edit, 1)
        path_row.addWidget(browse)
        path_row.addWidget(load)
        layout.addLayout(path_row)

        filter_row = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText(_("Search title or Gutenberg id"))
        self.search.textChanged.connect(self._on_search)
        self.epub_only = QCheckBox(_("EPUB only"))
        # Off by default so HTML-only books (no native EPUB) remain visible.
        self.epub_only.setChecked(False)
        self.epub_only.toggled.connect(self._on_epub_only)
        filter_row.addWidget(self.search, 1)
        filter_row.addWidget(self.epub_only)
        layout.addLayout(filter_row)

        html_row = QHBoxLayout()
        html_row.addWidget(QLabel(_("When only HTML is available, convert to:")))
        self.html_format = QComboBox()
        self.html_format.addItem(_("EPUB"), "epub")
        self.html_format.addItem(_("PDF"), "pdf")
        html_row.addWidget(self.html_format)
        html_row.addStretch(1)
        layout.addLayout(html_row)

        self.model = BookTableModel([])
        self.proxy = BookFilterProxy(self)
        self.proxy.setSourceModel(self.model)
        self.table = QTableView()
        self.table.setModel(self.proxy)
        self.table.setSelectionBehavior(SelectRows)
        self.table.setSortingEnabled(True)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(2, Stretch)
        header.resizeSection(0, 28)
        header.resizeSection(1, 70)
        header.resizeSection(3, 48)
        header.resizeSection(4, 48)
        header.resizeSection(5, 48)
        layout.addWidget(self.table, 1)

        layout.addWidget(
            QLabel(
                _(
                    "EPUB / PDF = native files in the ZIM. HTML = catalog page "
                    "(always present; used only when no native EPUB/PDF). "
                    "Many books have both EPUB and HTML — they are not exclusive. "
                    "Import prefers native EPUB, then PDF, else HTML→chosen format."
                )
            )
        )

        select_row = QHBoxLayout()
        all_btn = QPushButton(_("Select visible"))
        none_btn = QPushButton(_("Clear selection"))
        all_btn.clicked.connect(self._select_visible)
        none_btn.clicked.connect(self._clear_selection)
        self.status = QLabel(_("Open a .zim catalog to list books."))
        self.status.setWordWrap(True)
        select_row.addWidget(all_btn)
        select_row.addWidget(none_btn)
        select_row.addWidget(self.status, 1)
        layout.addLayout(select_row)

        self.progress = QProgressBar()
        self.progress.setTextVisible(True)
        self.progress.hide()
        layout.addWidget(self.progress)

        buttons = QDialogButtonBox(Cancel)
        self.import_btn = buttons.addButton(_("Import selected"), ActionRole)
        self.import_btn.clicked.connect(self._import_selected)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _selected_html_format(self) -> str:
        data = self.html_format.currentData()
        return data if data in {"epub", "pdf"} else "epub"

    def _browse(self):
        path, _ok = QFileDialog.getOpenFileName(
            self,
            _("Select ZIM file"),
            self.path_edit.text() or str(Path.home()),
            _("ZIM archives (*.zim);;All files (*.*)"),
        )
        if path:
            self.path_edit.setText(path)

    def _set_busy(self, busy: bool, maximum: int = 0) -> None:
        self.import_btn.setEnabled(not busy)
        if busy:
            self.progress.setMaximum(maximum)
            self.progress.setValue(0)
            self.progress.show()
        else:
            self.progress.hide()
            self.progress.setMaximum(0)
            self.progress.setValue(0)

    def _load_catalog(self):
        path = self.path_edit.text().strip()
        if not path or not Path(path).is_file():
            error_dialog(self, _("ZIM Import"), _("Choose an existing .zim file."), show=True)
            return
        self._zim_path = path
        self.status.setText(_("Reading catalog (no content extraction)…"))
        self._set_busy(True, 0)  # indeterminate
        self._catalog_worker = CatalogWorker(path, self)
        self._catalog_worker.loaded.connect(self._on_catalog)
        self._catalog_worker.failed.connect(self._on_catalog_failed)
        self._catalog_worker.start()

    def _on_catalog(self, books):
        self._set_busy(False)
        visible = filter_books_for_import(
            books, epub_only=False, include_pdf=True, include_html=True
        )
        self.model.reset_books(visible)
        self.proxy.set_epub_only(self.epub_only.isChecked())
        n_epub = sum(1 for book in visible if book.has_epub)
        n_html_only = sum(
            1 for book in visible if not book.has_epub and not book.has_pdf
        )
        if not visible:
            self.status.setText(_("No Gutenberg books found in this ZIM."))
            error_dialog(
                self,
                _("ZIM Import"),
                _(
                    "This archive opened successfully, but no Project Gutenberg "
                    "book pages were found. Supported layouts: legacy A/*.html + I/*.epub "
                    "or modern C/Title.ID (+ C/*.epub). Other ZIM collections "
                    "(DevDocs, Wikipedia, …) are not importable."
                ),
                show=True,
            )
            return
        self.status.setText(
            _(
                "{n} books ({epub} with EPUB, {html_only} HTML-only)."
            ).format(n=len(visible), epub=n_epub, html_only=n_html_only)
        )

    def _on_catalog_failed(self, message):
        self._set_busy(False)
        self.status.setText(_("Failed to read catalog."))
        error_dialog(
            self,
            _("ZIM Import"),
            _("Could not read the ZIM catalog."),
            det_msg=message,
            show=True,
        )

    def _on_search(self, text):
        self.proxy.set_query(text)

    def _on_epub_only(self, checked):
        self.proxy.set_epub_only(checked)

    def _visible_books(self) -> list[GutenbergBook]:
        books = []
        for row in range(self.proxy.rowCount()):
            index = self.proxy.index(row, 0)
            source = self.proxy.mapToSource(index)
            book = self.model.books[source.row()]
            books.append(book)
        return books

    def _select_visible(self):
        self.model.set_checked_books(self._visible_books(), True)
        self._update_status_selection()

    def _clear_selection(self):
        self.model.set_checked_books(self.model.books, False)
        self._update_status_selection()

    def _update_status_selection(self):
        n = len(self.model.selected_books())
        self.status.setText(_("{n} book(s) selected.").format(n=n))

    def _import_selected(self):
        selected = self.model.selected_books()
        if self.epub_only.isChecked():
            selected = [book for book in selected if book.has_epub]
        if not selected:
            error_dialog(
                self,
                _("ZIM Import"),
                _("Select one or more books to import (EPUB-first)."),
                show=True,
            )
            return
        if not self._zim_path:
            error_dialog(self, _("ZIM Import"), _("Load a ZIM catalog first."), show=True)
            return
        self._temp_dir = PersistentTemporaryDirectory("_zim_import")
        self._set_busy(True, len(selected))
        self.status.setText(_("Extracting books…"))
        self._import_worker = ImportWorker(
            self._zim_path,
            selected,
            self._temp_dir,
            html_format=self._selected_html_format(),
            parent=self,
        )
        self._import_worker.progressed.connect(self._on_import_progress)
        self._import_worker.finished_ok.connect(self._on_import_done)
        self._import_worker.failed.connect(self._on_import_failed)
        self._import_worker.start()

    def _on_import_progress(self, current, total, title):
        self.progress.setMaximum(total)
        self.progress.setValue(current)
        short = title if len(title) <= 60 else title[:57] + "…"
        self.status.setText(
            _("Extracting {current}/{total}: {title}").format(
                current=current, total=total, title=short
            )
        )

    def _on_import_done(self, records, errors):
        self._set_busy(False)
        self.result_payload = records
        self.result_errors = errors
        if not records:
            self.status.setText(_("Nothing could be extracted."))
            error_dialog(
                self,
                _("ZIM Import"),
                _("Nothing could be extracted."),
                det_msg="\n".join(f"{book.title}: {msg}" for book, msg in errors),
                show=True,
            )
            return
        self.accept()

    def _on_import_failed(self, message):
        self._set_busy(False)
        self.status.setText(_("Import failed."))
        error_dialog(self, _("ZIM Import"), _("Import failed."), det_msg=message, show=True)
