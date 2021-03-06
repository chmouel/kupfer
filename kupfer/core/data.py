import itertools
import operator
import os

import gobject

from kupfer.obj import base, sources, compose
from kupfer import pretty, scheduler, task
from kupfer import commandexec
from kupfer import datatools
from kupfer.core import search, learn
from kupfer.core import settings
from kupfer.core import qfurl

from kupfer.core.sources import GetSourceController

# "Enums"
# Which pane
SourcePane, ActionPane, ObjectPane = (1,2,3)

# In two-pane or three-pane mode
SourceActionMode, SourceActionObjectMode = (1,2)

def identity(x):
	return x

def dress_leaves(seq, action):
	"""yield items of @seq "dressed" by the source controller"""
	sc = GetSourceController()
	for itm in seq:
		sc.decorate_object(itm.object, action=action)
		yield itm

class Searcher (object):
	"""
	This class searches KupferObjects efficiently, and
	stores searches in a cache for a very limited time (*)

	(*) As of this writing, the cache is used when the old key
	is a prefix of the search key.
	"""

	def __init__(self):
		self._source_cache = {}
		self._old_key = None

	def search(self, sources, key, score=True, item_check=None, decorator=None):
		"""
		@sources is a sequence listing the inputs, which should be
		Sources, TextSources or sequences of KupferObjects

		If @score, sort by rank.
		filters (with identity() as default):
			@item_check: Check items before adding to search pool
			@decorator: Decorate items before access

		Return (first, match_iter), where first is the first match,
		and match_iter an iterator to all matches, including the first match.
		"""
		if not self._old_key or not key.startswith(self._old_key):
			self._source_cache.clear()
		self._old_key = key

		if not item_check: item_check = identity
		if not decorator: decorator = identity

		match_iters = []
		for src in sources:
			fixedrank = 0
			rankables = None
			if isinstance(src, base.Source):
				try:
					# stored rankables
					rankables = self._source_cache[src]
				except KeyError:
					# check uncached items
					items = item_check(src.get_leaves())
			elif isinstance(src, base.TextSource):
				items = item_check(src.get_items(key))
				fixedrank = src.get_rank()
			else:
				items = item_check(src)

			if not rankables:
				rankables = search.make_rankables(items)

			if score:
				if fixedrank:
					rankables = search.add_rank_objects(rankables, fixedrank)
				elif key:
					rankables = search.score_objects(rankables, key)
				matches = search.bonus_objects(rankables, key)
				if isinstance(src, base.Source):
					# we fork off a copy of the iterator to save
					matches, self._source_cache[src] = itertools.tee(matches)
			else:
				# we only want to list them
				matches = rankables

			match_iters.append(matches)
		
		matches = itertools.chain(*match_iters)
		if score:
			matches = sorted(matches, key=operator.attrgetter("rank"),
					reverse=True)

		def as_set_iter(seq):
			key = operator.attrgetter("object")
			return datatools.UniqueIterator(seq, key=key)

		def valid_check(seq):
			"""yield items of @seq that are valid"""
			for itm in seq:
				obj = itm.object
				if (not hasattr(obj, "is_valid")) or obj.is_valid():
					yield itm

		def peekfirst(seq):
			"""This function will return (firstitem, iter)
			where firstitem is the first item of @seq or None if empty,
			and iter an equivalent copy of @seq
			"""
			seq = iter(seq)
			for itm in seq:
				old_iter = itertools.chain((itm, ), seq)
				return (itm, old_iter)
			return (None, seq)

		# Check if the items are valid as the search
		# results are accessed through the iterators
		unique_matches = as_set_iter(matches)
		match, match_iter = peekfirst(decorator(valid_check(unique_matches)))
		return match, match_iter

class Pane (gobject.GObject):
	"""
	signals:
		search-result (match, match_iter, context)
	"""
	__gtype_name__ = "Pane"
	def __init__(self):
		super(Pane, self).__init__()
		self.selection = None
		self.latest_key = None
		self.outstanding_search = -1
		self.outstanding_search_id = -1
		self.searcher = Searcher()

	def select(self, item):
		self.selection = item
	def get_selection(self):
		return self.selection
	def reset(self):
		self.selection = None
	def get_latest_key(self):
		return self.latest_key
	def get_can_enter_text_mode(self):
		return False
	def emit_search_result(self, match, match_iter, context):
		self.emit("search-result", match, match_iter, context)

gobject.signal_new("search-result", Pane, gobject.SIGNAL_RUN_LAST,
		gobject.TYPE_BOOLEAN, (gobject.TYPE_PYOBJECT, gobject.TYPE_PYOBJECT, 
		gobject.TYPE_PYOBJECT))

class LeafPane (Pane, pretty.OutputMixin):
	__gtype_name__ = "LeafPane"

	def __init__(self):
		super(LeafPane, self).__init__()
		self.source_stack = []
		self.source = None

	def _load_source(self, src):
		"""Try to get a source from the SourceController,
		if it is already loaded we get it from there, else
		returns @src"""
		sc = GetSourceController()
		return sc.get_canonical_source(src)

	def get_source(self):
		return self.source

	def source_rebase(self, src):
		self.source_stack = []
		self.source = self._load_source(src)
		self.refresh_data()

	def push_source(self, src):
		self.source_stack.append(self.source)
		self.source = self._load_source(src)
		self.refresh_data()

	def pop_source(self):
		"""Return True if succeeded"""
		if not len(self.source_stack):
			return False
		self.source = self.source_stack.pop()
		return True

	def is_at_source_root(self):
		"""Return True if we have no source stack"""
		return not self.source_stack

	def get_can_enter_text_mode(self):
		return self.is_at_source_root()

	def refresh_data(self):
		self.emit("new-source", self.source)

	def browse_up(self):
		"""Try to browse up to previous sources, from current
		source"""
		succ = self.pop_source()
		if not succ:
			if self.source.has_parent():
				self.source_rebase(self.source.get_parent())
				succ = True
		if succ:
			self.refresh_data()
		return succ

	def browse_down(self, alternate=False):
		"""Browse into @leaf if it's possible
		and save away the previous sources in the stack
		if @alternate, use the Source's alternate method"""
		leaf = self.get_selection()
		if leaf and leaf.has_content():
			self.push_source(leaf.content_source(alternate=alternate))
			return True
		return False

	def reset(self):
		"""Pop all sources and go back to top level"""
		Pane.reset(self)
		while self.pop_source():
			pass
		self.refresh_data()

	def soft_reset(self):
		Pane.reset(self)
		while self.pop_source():
			pass
		return self.source

	def search(self, key=u"", context=None, text_mode=False):
		"""
		filter for action @item
		"""
		self.latest_key = key
		sources = [ self.get_source() ] if not text_mode else []
		if key and self.is_at_source_root():
			# Only use text sources when we are at root catalog
			sc = GetSourceController()
			textsrcs = sc.get_text_sources()
			sources.extend(textsrcs)

		decorator = lambda seq: dress_leaves(seq, action=None)
		match, match_iter = self.searcher.search(sources, key, score=bool(key),
				decorator=decorator)
		self.emit_search_result(match, match_iter, context)

gobject.signal_new("new-source", LeafPane, gobject.SIGNAL_RUN_LAST,
		gobject.TYPE_BOOLEAN, (gobject.TYPE_PYOBJECT,))

class PrimaryActionPane (Pane):
	def __init__(self):
		super(PrimaryActionPane, self).__init__()
		self.set_item(None)

	def set_item(self, item):
		"""Set which @item we are currently listing actions for"""
		self.current_item = item
		self._action_valid_cache = {}

	def search(self, key=u"", context=None, text_mode=False):
		"""Search: Register the search method in the event loop

		using @key, promising to return
		@context in the notification about the result, having selected
		@item in SourcePane

		If we already have a call to search, we remove the "source"
		so that we always use the most recently requested search."""

		self.latest_key = key
		leaf = self.current_item
		actions = list(leaf.get_actions()) if leaf else []
		sc = GetSourceController()
		if leaf:
			for act in sc.get_actions_for_leaf(leaf):
				actions.append(act)

		def is_valid_cached(action):
			"""Check if @action is valid for current item"""
			cache = self._action_valid_cache
			valid = cache.get(action)
			if valid is None:
				valid = action.valid_for_item(self.current_item)
			cache[action] = valid
			return valid

		def valid_decorator(seq):
			"""Check if actions are valid before access"""
			for obj in seq:
				if is_valid_cached(obj.object):
					yield obj

		sources = (actions, )
		match, match_iter = self.searcher.search(sources, key,
				decorator=valid_decorator)
		self.emit_search_result(match, match_iter, context)

class SecondaryObjectPane (LeafPane):
	__gtype_name__ = "SecondaryObjectPane"
	def __init__(self):
		LeafPane.__init__(self)
		self.current_item = None
		self.current_action = None

	def reset(self):
		LeafPane.reset(self)
		self.searcher = Searcher()

	def set_item_and_action(self, item, act):
		self.current_item = item
		self.current_action = act
		if item and act:
			ownsrc = act.object_source(item)
			if ownsrc:
				self.source_rebase(ownsrc)
			else:
				sc = GetSourceController()
				self.source_rebase(sc.root_for_types(act.object_types()))
		else:
			self.reset()

	def get_can_enter_text_mode(self):
		"""Check if there are any reasonable text sources for this action"""
		atroot = self.is_at_source_root()
		types = tuple(self.current_action.object_types())
		sc = GetSourceController()
		textsrcs = sc.get_text_sources()
		return (atroot and
			any(sc.good_source_for_types(s, types) for s in textsrcs))

	def search(self, key=u"", context=None, text_mode=False):
		"""
		filter for action @item
		"""
		self.latest_key = key
		sources = []
		if not text_mode or isinstance(self.get_source(), base.TextSource):
			sources.append(self.get_source())
		if key and self.is_at_source_root():
			# Only use text sources when we are at root catalog
			sc = GetSourceController()
			textsrcs = sc.get_text_sources()
			sources.extend(textsrcs)

		types = tuple(self.current_action.object_types())
		def type_obj_check(itms):
			valid_object = self.current_action.valid_object
			item = self.current_item
			for i in itms:
				if (isinstance(i, types) and valid_object(i, for_item=item)):
					yield i
		def type_check(itms):
			for i in itms:
				if isinstance(i, types):
					yield i

		if hasattr(self.current_action, "valid_object"):
			item_check = type_obj_check
		else:
			item_check = type_check

		decorator = lambda seq: dress_leaves(seq, action=self.current_action)

		match, match_iter = self.searcher.search(sources, key, score=True,
				item_check=item_check, decorator=decorator)
		self.emit_search_result(match, match_iter, context)

class DataController (gobject.GObject, pretty.OutputMixin):
	"""
	Sources <-> Actions controller

	The data controller must be created before main program commences,
	so it can register itself at the scheduler correctly.
	"""
	__gtype_name__ = "DataController"

	def __init__(self):
		super(DataController, self).__init__()

		self.source_pane = LeafPane()
		self.object_pane = SecondaryObjectPane()
		self.source_pane.connect("new-source", self._new_source)
		self.object_pane.connect("new-source", self._new_source)
		self.action_pane = PrimaryActionPane()
		self._panectl_table = {
			SourcePane : self.source_pane,
			ActionPane : self.action_pane,
			ObjectPane : self.object_pane,
			}
		for pane, ctl in self._panectl_table.items():
			ctl.connect("search-result", self._pane_search_result, pane)
		self.mode = None
		self._search_ids = itertools.count(1)
		self._execution_context = commandexec.DefaultActionExecutionContext()
		self._execution_context.connect("command-result",
				self._command_execution_result)

		sch = scheduler.GetScheduler()
		sch.connect("load", self._load)
		sch.connect("finish", self._finish)

	def register_text_sources(self, srcs):
		"""Pass in text sources as @srcs

		we register text sources """
		sc = GetSourceController()
		sc.add_text_sources(srcs)
	
	def register_action_decorators(self, actions):
		# Keep a mapping: Decorated Leaf Type -> List of actions
		decorate_types = {}
		for action in actions:
			for appl_type in action.item_types():
				decorate_types.setdefault(appl_type, []).append(action)
		sc = GetSourceController()
		sc.set_action_decorators(decorate_types)
		self.output_debug("Action decorators:")
		for typ in decorate_types:
			self.output_debug(typ.__name__)
			for dec in decorate_types[typ]:
				self.output_debug(type(dec).__module__, type(dec).__name__,sep=".")

	def register_content_decorators(self, contents):
		"""
		Register the sequence of classes @contents as
		potential content decorators. Classes not conforming to
		the decoration protocol (most importantly, ``.decorates_type()``)
		will be skipped
		"""
		# Keep a mapping:
		# Decorated Leaf Type -> Set of content decorator types
		decorate_item_types = {}
		for c in contents:
			try:
				applies = c.decorates_type()
			except AttributeError:
				continue
			decorate_item_types.setdefault(applies, set()).add(c)
		sc = GetSourceController()
		sc.set_content_decorators(decorate_item_types)
		self.output_debug("Content decorators:")
		for typ in decorate_item_types:
			self.output_debug(typ.__name__)
			for dec in decorate_item_types[typ]:
				self.output_debug(dec.__module__, dec.__name__, sep=".")

	def _load(self, sched):
		"""Load data from persistent store"""
		S_s, s_s = self._setup_plugins()
		sc = GetSourceController()
		direct_sources = set(S_s)
		other_sources = set(s_s) - direct_sources
		sc.add(direct_sources, toplevel=True)
		sc.add(other_sources, toplevel=False)
		sc.cache_toplevel_sources()
		self.source_pane.source_rebase(sc.root)
		learn.load()

	def _get_directory_sources(self):
		"""
		Return a tuple of S_sources, s_sources for
		directory sources directly included and for
		catalog inclusion respectively
		"""

		s_sources = []
		S_sources = []

		setctl = settings.GetSettingsController()
		source_config = setctl.get_config

		def dir_source(opt):
			return sources.DirectorySource(opt)

		def file_source(opt, depth=1):
			abs = os.path.abspath(os.path.expanduser(opt))
			return sources.FileSource((abs,), depth)

		for coll, level in zip((s_sources, S_sources), ("Catalog", "Direct")):
			for item in setctl.get_directories(level):
				coll.append(dir_source(item))

		dir_depth = source_config("DeepDirectories", "Depth")

		for item in source_config("DeepDirectories","Catalog"):
			s_sources.append(file_source(item, dir_depth))
		for item in source_config("DeepDirectories", "Direct"):
			S_sources.append(file_source(item, dir_depth))

		return S_sources, s_sources

	def _setup_plugins(self):
		"""
		@S_sources are to be included directly in the catalog,
		@s_souces as just as subitems
		"""
		from kupfer.core import plugins
		from kupfer.core.plugins import (load_plugin_sources, sources_attribute,
				action_decorators_attribute, text_sources_attribute,
				content_decorators_attribute,
				initialize_plugin)

		s_sources = []
		S_sources = []

		setctl = settings.GetSettingsController()

		text_sources = []
		action_decorators = []
		content_decorators = []

		for item in plugins.get_plugin_ids():
			if not setctl.get_plugin_enabled(item):
				continue
			initialize_plugin(item)
			text_sources.extend(load_plugin_sources(item, text_sources_attribute))
			action_decorators.extend(load_plugin_sources(item,
				action_decorators_attribute))
			# Register all Sources as (potential) content decorators
			content_decorators.extend(load_plugin_sources(item,
				sources_attribute, instantiate=False))
			content_decorators.extend(load_plugin_sources(item,
				content_decorators_attribute, instantiate=False))
			if setctl.get_plugin_is_toplevel(item):
				S_sources.extend(load_plugin_sources(item))
			else:
				s_sources.extend(load_plugin_sources(item))

		D_dirs, d_dirs = self._get_directory_sources()
		S_sources.extend(D_dirs)
		s_sources.extend(d_dirs)

		if not S_sources and not s_sources:
			pretty.print_info(__name__, "No sources found!")

		self.register_text_sources(text_sources)
		self.register_action_decorators(action_decorators)
		self.register_content_decorators(content_decorators)
		return S_sources, s_sources

	def _finish(self, sched):
		self.output_info("Saving data...")
		learn.finish()
		GetSourceController().save_data()
		self.output_info("Saving cache...")
		GetSourceController().finish()

	def _new_source(self, ctr, src):
		if ctr is self.source_pane:
			pane = SourcePane
		elif ctr is self.object_pane:
			pane = ObjectPane
		root = ctr.is_at_source_root()
		self.emit("source-changed", pane, src, root)

	def reset(self):
		self.source_pane.reset()
		self.action_pane.reset()

	def soft_reset(self, pane):
		if pane is ActionPane:
			return
		panectl = self._panectl_table[pane]
		return panectl.soft_reset()

	def cancel_search(self, pane=None):
		"""Cancel any outstanding search, or the search for @pane"""
		panes = (pane, ) if pane else iter(self._panectl_table)
		for pane in panes:
			ctl = self._panectl_table[pane]
			if ctl.outstanding_search > 0:
				gobject.source_remove(ctl.outstanding_search)
				ctl.outstanding_search = -1

	def search(self, pane, key=u"", context=None, interactive=False, lazy=False,
			text_mode=False):
		"""Search: Register the search method in the event loop

		Will search in @pane's base using @key, promising to return
		@context in the notification about the result.

		if @interactive, the search result will return immediately
		if @lazy, will slow down search result reporting
		"""

		self.cancel_search(pane)
		ctl = self._panectl_table[pane]
		ctl.outstanding_search_id = self._search_ids.next()
		wrapcontext = (ctl.outstanding_search_id, context)
		if interactive:
			ctl.search(key, wrapcontext, text_mode)
		else:
			timeout = 300 if lazy else 0 if not key else 50/len(key)
			ctl.outstanding_search = gobject.timeout_add(timeout, ctl.search, 
					key, wrapcontext, text_mode)

	def _pane_search_result(self, panectl, match,match_iter, wrapcontext, pane):
		search_id, context = wrapcontext
		if not search_id is panectl.outstanding_search_id:
			self.output_debug("Skipping late search", match, context)
			return True
		self.emit("search-result", pane, match, match_iter, context)

	def select(self, pane, item):
		"""Select @item in @pane to self-update
		relevant places"""
		# If already selected, do nothing
		panectl = self._panectl_table[pane]
		if item is panectl.get_selection():
			return
		self.cancel_search()
		panectl.select(item)
		if pane is SourcePane:
			assert not item or isinstance(item, base.Leaf), \
					"Selection in Source pane is not a Leaf!"
			# populate actions
			self.action_pane.set_item(item)
			self.search(ActionPane, interactive=True)
		elif pane is ActionPane:
			assert not item or isinstance(item, base.Action), \
					"Selection in Source pane is not an Action!"
			if item and item.requires_object():
				newmode = SourceActionObjectMode
			else:
				newmode = SourceActionMode
			if newmode is not self.mode:
				self.mode = newmode
				self.emit("mode-changed", self.mode, item)
			if self.mode is SourceActionObjectMode:
				# populate third pane
				self.object_pane.set_item_and_action(self.source_pane.get_selection(), item)
				self.search(ObjectPane, lazy=True)
		elif pane is ObjectPane:
			assert not item or isinstance(item, base.Leaf), \
					"Selection in Object pane is not a Leaf!"

	def get_can_enter_text_mode(self, pane):
		panectl = self._panectl_table[pane]
		return panectl.get_can_enter_text_mode()

	def validate(self):
		"""Check if all selected items are still valid
		(for example after being spawned again, old item
		still focused)

		This will trigger .select() with None if items
		are not valid..
		"""
		for paneenum, pane in ((SourcePane, self.source_pane),
				(ActionPane, self.action_pane)):
			sel = pane.get_selection()
			if not sel:
				break
			if hasattr(sel, "is_valid") and not sel.is_valid():
				self.emit("pane-reset", paneenum, None)
				self.select(paneenum, None)

	def browse_up(self, pane):
		"""Try to browse up to previous sources, from current
		source"""
		if pane is SourcePane:
			return self.source_pane.browse_up()
		if pane is ObjectPane:
			return self.object_pane.browse_up()
	
	def browse_down(self, pane, alternate=False):
		"""Browse into @leaf if it's possible
		and save away the previous sources in the stack
		if @alternate, use the Source's alternate method"""
		if pane is ActionPane:
			return
		# record used object if we browse down
		panectl = self._panectl_table[pane]
		sel, key = panectl.get_selection(), panectl.get_latest_key()
		if panectl.browse_down(alternate=alternate):
			learn.record_search_hit(sel, key)

	def activate(self):
		"""
		Activate current selection
		"""
		action = self.action_pane.get_selection()
		leaf = self.source_pane.get_selection()
		sobject = self.object_pane.get_selection()
		mode = self.mode
		try:
			ctx = self._execution_context
			res, ret = ctx.run(leaf, action, sobject)
		except commandexec.ActionExecutionError, exc:
			self.output_error(exc)
			return

		# register search to learning database
		learn.record_search_hit(leaf, self.source_pane.get_latest_key())
		learn.record_search_hit(action, self.action_pane.get_latest_key())
		if sobject and mode is SourceActionObjectMode:
			learn.record_search_hit(sobject, self.object_pane.get_latest_key())
		if res not in commandexec.RESULTS_SYNC:
			self.emit("launched-action")

	def _insert_object(self, pane, obj):
		"Insert @obj in @pane: prepare the object, then emit pane-reset"
		sc = GetSourceController()
		sc.decorate_object(obj)
		self.emit("pane-reset", pane, search.wrap_rankable(obj))

	def _command_execution_result(self, ctx, result_type, ret):
		if result_type == commandexec.RESULT_SOURCE:
			self.source_pane.push_source(ret)
		elif result_type == commandexec.RESULT_OBJECT:
			self._insert_object(SourcePane, ret)
		else:
			return
		self.emit("command-result", result_type)

	def find_object(self, url):
		"""Find object with URI @url and select it in the first pane"""
		sc = GetSourceController()
		qf = qfurl.qfurl(url=url)
		found = qf.resolve_in_catalog(sc.sources)
		if found and not found == self.source_pane.get_selection():
			self._insert_object(SourcePane, found)

	def compose_selection(self):
		leaf = self.source_pane.get_selection()
		action = self.action_pane.get_selection()
		if leaf is None or action is None:
			return
		iobj = self.object_pane.get_selection()
		if self.mode is SourceActionObjectMode:
			if iobj is None:
				return
		else:
			iobj = None
		obj = compose.ComposedLeaf(leaf, action, iobj)
		self._insert_object(SourcePane, obj)

# pane cleared or set with new item
# pane, item
gobject.signal_new("pane-reset", DataController, gobject.SIGNAL_RUN_LAST,
	gobject.TYPE_BOOLEAN, (gobject.TYPE_INT, gobject.TYPE_PYOBJECT,))

# pane, match, iter to matches, context
gobject.signal_new("search-result", DataController, gobject.SIGNAL_RUN_LAST,
		gobject.TYPE_BOOLEAN, (gobject.TYPE_INT, gobject.TYPE_PYOBJECT, gobject.TYPE_PYOBJECT, gobject.TYPE_PYOBJECT))

gobject.signal_new("source-changed", DataController, gobject.SIGNAL_RUN_LAST,
		gobject.TYPE_BOOLEAN, (int, object, bool))

# mode, None(?)
gobject.signal_new("mode-changed", DataController, gobject.SIGNAL_RUN_LAST,
		gobject.TYPE_BOOLEAN, (gobject.TYPE_INT, gobject.TYPE_PYOBJECT,))

# when an command returned a result
# arguments: result type
gobject.signal_new("command-result", DataController, gobject.SIGNAL_RUN_LAST,
		gobject.TYPE_BOOLEAN, (gobject.TYPE_INT, ))

# when an action was launched
# arguments: none
gobject.signal_new("launched-action", DataController, gobject.SIGNAL_RUN_LAST,
		gobject.TYPE_BOOLEAN, ())


