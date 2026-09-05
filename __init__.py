# The class that all Interface Action plugin wrappers must inherit from
from calibre.customize import InterfaceActionBase


class ZimImportPlugin(InterfaceActionBase):
    """Import individual Gutenberg books from an OpenZIM archive."""

    name = "ZIM Import"
    description = (
        "Import selected books from a Project Gutenberg OpenZIM (.zim) collection "
        "into your Calibre library (EPUB/PDF native, or HTML→EPUB/PDF)."
    )
    supported_platforms = ["windows", "osx", "linux"]
    author = "fhancy"
    version = (0, 1, 7)
    minimum_calibre_version = (6, 0, 0)

    actual_plugin = "calibre_plugins.zim_import.zim_import.ui:ZimImportAction"

    def is_customizable(self):
        return False
