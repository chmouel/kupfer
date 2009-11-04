# -*- encoding: UTF-8 -*-
from __future__ import unicode_literals

import locale
from unicodedata import normalize, category

def _folditems():
	_folding_table = {
		# general non-decomposing characters
		# FIXME: This is not complete
		"ł" : "l",
		"œ" : "oe",
		"ð" : "d",
		"þ" : "th",
		"ß" : "ss",
		# germano-scandinavic canonical transliterations
		"ü" : "ue",
		"å" : "aa",
		"ä" : "ae",
		"æ" : "ae",
		"ö" : "oe",
		"ø" : "oe",
	}

	for c, rep in _folding_table.items():
		yield (ord(c.upper()), rep.title())
		yield (ord(c), rep)

folding_table = dict(_folditems())

def tounicode(utf8str):
	"""Return `unicode` from UTF-8 encoded @utf8str
	This is to use the same error handling etc everywhere
	"""
	return utf8str.decode("UTF-8", "replace") if utf8str is not None else ""

def toutf8(ustr):
	"""Return UTF-8 `str` from unicode @ustr
	This is to use the same error handling etc everywhere
	if ustr is `str`, just return it
	"""
	if isinstance(ustr, str):
		return ustr
	return ustr.encode("UTF-8", "replace")

def fromlocale(lstr):
	"""Return a unicode string from locale bytestring @lstr"""
	enc = locale.getpreferredencoding()
	return lstr.decode(enc, "replace")


def tofolded(ustr):
	"""Fold @ustr

	Return a unicode string where composed characters are replaced by
	their base, and extended latin characters are replaced by
	similar basic latin characters.

	>>> tofolded(u'Wyłącz')
	u'Wylacz'
	>>> tofolded(u'naïveté')
	u'naivete'

	Characters from other scripts are not transliterated.

	>>> print(tofolded(u'Ἑλλάς'))
	Ελλας
	"""
	srcstr = normalize("NFKD", ustr.translate(folding_table))
	return "".join(c for c in srcstr if category(c) != 'Mn')

if __name__ == '__main__':
	import sys
	if not sys.getdefaultencoding() == "utf-8":
		reload(sys)
		sys.setdefaultencoding("UTF-8")
	else:
		# for Py 3 we make this absurd hack to update the docstring
		tofolded.__doc__ = tofolded.__doc__.replace("u'", "'")

	import doctest
	doctest.testmod()
