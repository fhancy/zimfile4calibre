# The class that all Interface Action plugin wrappers must inherit from
from calibre.customize import InterfaceActionBase


class ZimImportPlugin(InterfaceActionBase):
    """Import individual Gutenberg books from an OpenZIM archive."""

    name = "ZIM Import"
    description = (
        "Import selected EPUB/PDF books from a Gutenberg OpenZIM (.zim) collection "
        "into the Calibre library."
    )
    supported_platforms = ["windows", "osx", "linux"]
    author = "calibre-zim-plugin"
    version = (0, 1, 4)
    minimum_calibre_version = (6, 0, 0)

    actual_plugin = "calibre_plugins.zim_import.zim_import.ui:ZimImportAction"

    def is_customizable(self):
        return False
