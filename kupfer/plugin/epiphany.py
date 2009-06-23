from kupfer.objects import Leaf, Action, Source
from kupfer.objects import UrlLeaf

__kupfer_sources__ = ("EpiphanySource", )
__description__ = _("Index of Epiphany bookmarks")
__version__ = ""
__author__ = "Ulrik Sverdrup <ulrik.sverdrup@gmail.com>"

class EpiphanySource (Source):
	def __init__(self):
		super(EpiphanySource, self).__init__(_("Epiphany Bookmarks"))
	
	def get_items(self):
		from epiphany_support import EpiphanyBookmarksParser
		parser = EpiphanyBookmarksParser()
		bookmarks = parser.get_items()
		return (UrlLeaf(href, title) for title, href in bookmarks)

	def get_description(self):
		return _("Index of Epiphany bookmarks")

	def get_icon_name(self):
		return "web-browser"
