import urllib

from kupfer.objects import Action, Source, Leaf, UrlLeaf
from kupfer.objects import TextLeaf
from kupfer import utils, config

__kupfer_name__ = _("Google Search")
__kupfer_actions__ = ("Search", )
__description__ = _("Search the web with OpenSearch search engines")
__version__ = ""
__author__ = "Ulrik Sverdrup <ulrik.sverdrup@gmail.com>"

try:
	import cjson
	json_decoder = cjson.decode
except ImportError:
	import json
	json_decoder = json.loads

SEARCH_URL = 'http://ajax.googleapis.com/ajax/services/search/web?v=1.0&'

class Search (Action):
	def __init__(self):
		Action.__init__(self, _("Google Search"))

	def is_factory(self):
		return True
	def activate(self, leaf):
		return SearchResults(leaf.object)
		
	def item_types(self):
		yield TextLeaf

class CustomDescriptionUrl (UrlLeaf):
	def __init__(self, obj, title, desc):
		UrlLeaf.__init__(self, obj, title)
		self.description = desc
	def get_description(self):
		return self.description

class SearchResults (Source):
	def __init__(self, query):
		Source.__init__(self, _('Results for "%s"') % query)
		self.query = query

	def get_items(self):
		query = urllib.urlencode({'q': self.query})
		search_response = urllib.urlopen(SEARCH_URL + query)
		ctype = search_response.headers.get("content-type") or ""
		parts = ctype.split("charset=", 1)
		encoding = parts[-1] if len(parts) > 1 else "UTF-8"
		search_results = search_response.read().decode(encoding)
		search_response.close()
		results = json_decoder(search_results)
		data = results['responseData']
		more_results_url = data['cursor']['moreResultsUrl']
		total_results = data['cursor']['estimatedResultCount']
		for h in data['results']:
			yield UrlLeaf(h['url'], h['titleNoFormatting'])
		yield CustomDescriptionUrl(more_results_url,
				_('Show More Results For "%s"') % self.query,
				_("%s total found") % total_results)

	def provides(self):
		yield UrlLeaf

