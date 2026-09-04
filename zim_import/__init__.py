"""Read OpenZIM catalogs (Gutenberg 2021) for a future Calibre plugin."""

from .gutenberg_catalog import GutenbergBook, list_gutenberg_books
from .zim_reader import ZimArchive, ZimEntry, ZimError

__all__ = [
    "GutenbergBook",
    "ZimArchive",
    "ZimEntry",
    "ZimError",
    "list_gutenberg_books",
]
