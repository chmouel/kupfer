import os
from urlparse import urlparse, urlunparse
import re

import gobject

from kupfer.objects import TextSource, TextLeaf, FileLeaf, UrlLeaf, OpenUrl
from kupfer import utils

__kupfer_name__ = _("Free-text Queries")
__kupfer_sources__ = ()
__kupfer_text_sources__ = ("BasicTextSource", "PathTextSource", "URLTextSource",)
__kupfer_actions__ = ("OpenTextUrl", )
__description__ = _("Basic support for free-text queries")
__version__ = ""
__author__ = "Ulrik Sverdrup <ulrik.sverdrup@gmail.com>"


_USER = r"[\w\d]+[-\w\d.+-_]*"
_PORT = r"(:\d{1,5})?"
_PATHCHARS = r"[-\w\d_$.+!*,;@&=?/~#%]"
_SCHEME = r"(news:|telnet:|nntp:|file:\/|https?:|ftps?:|webcal:)?"
_PASS = r"([-\w\d,?;./!%$^*&~\"#']+:)?" 
_PATH = (r"(/" + _PATHCHARS + r"(\(" + _PATHCHARS + r"*\))*" + _PATHCHARS \
		+ r"*)*")
_HOSTIP = r"(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"
_HOSTNAME = r"(" + _HOSTIP + r"|([\w\d.-_]+\.\w{2,5}))"

_URL_REGEX_PATTERNS = [ re.compile(regex, re.IGNORECASE) for regex in (
	(_SCHEME + r"//(" + _PASS + _USER + r"@)?" + _HOSTNAME + _PORT + _PATH \
			+ r"$"),
	r"(" + _PASS + _USER + r"@)?" + _HOSTIP + _PORT + _PATH + r"$",
	r"(www|ftp)" + _HOSTNAME + _PORT + _PATH + r"$",
	(r"(callto:|h323:|sip:)" + _USER + r"(" + _PORT + r"/[\w\d]+)?\@" \
			+ _HOSTNAME + r"$"),
	r"(mailto:)?" + _USER + r"@" + _HOSTNAME + r"$",
	r"news:[\w\d^_{|}~!\"#$%&'()*+,./;:=?`]+" + r"$",
)]

_MAIL_PATTERN = re.compile(r"^" + _USER + r"@" + _HOSTNAME + r"$", re.IGNORECASE)


class BasicTextSource (TextSource):
	"""The most basic TextSource yields one TextLeaf"""
	def __init__(self):
		TextSource.__init__(self, name=_("Text Matches"))

	def get_items(self, text):
		if not text:
			return
		yield TextLeaf(text)
	def provides(self):
		yield TextLeaf


class PathTextSource (TextSource):
	"""Return existing full paths if typed"""
	def __init__(self):
		TextSource.__init__(self, name=_("Filesystem Text Matches"))

	def get_rank(self):
		return 80
	def get_items(self, text):
		# Find directories or files
		prefix = os.path.expanduser(u"~/")
		filepath = text if os.path.isabs(text) else os.path.join(prefix, text)
		# use filesystem encoding here
		filepath = gobject.filename_from_utf8(filepath)
		if os.access(filepath, os.R_OK):
			yield FileLeaf(filepath)
	def provides(self):
		yield FileLeaf

def is_url(text):
	"""check if @text is an URL"""
	text = text.strip()
	schema = urlparse(text)[0]
	return bool(schema) or any((
		re.match(regex, text) for regex in _URL_REGEX_PATTERNS))

def _cleanup_url(text):
	''' Cleanup @text - add mising schema '''
	text = text.strip()
	if _MAIL_PATTERN.match(text):
		return 'mailto:' + text
	scheme, netloc, path, params, query, fragment = urlparse(url)
	if schema:
		return text
	if netloc.startswith('ftp.'):
		return 'ftp://' + text
	return 'http://' + text

class OpenTextUrl (OpenUrl):
	rank_adjust = 10

	def activate(self, leaf):
		url = _cleanup_url(leaf.object)
		utils.show_url(url)
	def item_types(self):
		yield TextLeaf
	def valid_for_item(self, leaf):
		return is_url(leaf.object)

class URLTextSource (TextSource):
	"""detect URLs and webpages"""
	def __init__(self):
		TextSource.__init__(self, name=_("URL Text Matches"))

	def get_rank(self):
		return 75
	def get_items(self, text):
		# Only detect "perfect" URLs
		text = text.strip()
		components = list(urlparse(text))
		domain = "".join(components[1:])

		# If urlparse parses a scheme (http://), it's an URL
		if len(domain.split()) == 1 and components[0]:
			url = text
			name = ("".join(components[1:3])).strip("/")
			if name:
				yield UrlLeaf(url, name=name)

	def provides(self):
		yield UrlLeaf
