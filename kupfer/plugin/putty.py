# -*- coding: UTF-8 -*-
from __future__ import with_statement

import os
import urllib

from kupfer.objects import Action, AppLeafContentMixin
from kupfer.helplib import FilesystemWatchMixin, PicklingHelperMixin
from kupfer import utils, icons
from kupfer.obj.grouping import ToplevelGroupingSource 
from kupfer.obj.hosts import HOST_NAME_KEY, HostLeaf

__kupfer_name__ = _("PuTTY Sessions")
__kupfer_sources__ = ("PuttySessionSource", )
__kupfer_actions__ = ("PuttyOpenSession", )
__description__ = _("Quick access to PuTTY Sessions")
__version__ = "2010-01-07"
__author__ = "Karol Będkowski <karol.bedkowski@gmail.com>"



PUTTY_SESSION_KEY = "PUTTY_SESSION"


class PuttySession(HostLeaf):
	""" Leaf represent session saved in PuTTy"""

	def __init__(self, name, hostname, description):
		slots = {HOST_NAME_KEY: hostname, PUTTY_SESSION_KEY: name}
		HostLeaf.__init__(self, slots, name)
		self._description = description

	def get_description(self):
		return self._description

	def get_gicon(self):
		return icons.ComposedIcon("computer", "putty")


class PuttyOpenSession(Action):
	''' opens putty session '''
	def __init__(self):
		Action.__init__(self, _('Start Session'))

	def activate(self, leaf):
		session = leaf[PUTTY_SESSION_KEY]
		utils.launch_commandline("putty -load '%s'" % session)

	def get_icon_name(self):
		return 'putty'

	def item_types(self):
		yield HostLeaf

	def valid_for_item(self, item):
		return item.check_key(PUTTY_SESSION_KEY)


class PuttySessionSource(AppLeafContentMixin, ToplevelGroupingSource, 
		PicklingHelperMixin, FilesystemWatchMixin):
	''' indexes session saved in putty '''

	appleaf_content_id = 'putty'

	def __init__(self, name=_("PuTTY Sessions")):
		super(PuttySessionSource, self).__init__(name, "Sessions")
		self._version = 2
		self._putty_sessions_dir = os.path.expanduser('~/.putty/sessions')
		self.unpickle_finish()

	def unpickle_finish(self):
		self.monitor_token = self.monitor_directories(self._putty_sessions_dir)

	def get_items(self):
		if not os.path.isdir(self._putty_sessions_dir):
			return

		for filename in os.listdir(self._putty_sessions_dir):
			if filename == 'Default%20Settings':
				continue

			obj_path = os.path.join(self._putty_sessions_dir, filename)
			if os.path.isfile(obj_path):
				name = urllib.unquote(filename)
				description, host = self._load_host_from_session_file(obj_path)
				yield PuttySession(name, host, description)

	def get_description(self):
		return None

	def get_icon_name(self):
		return "putty"

	def provides(self):
		yield PuttySession

	def _load_host_from_session_file(self, filepath):
		user = None
		host = None
		try:
			with open(filepath, 'r') as session_file:
				for line in session_file:
					if line.startswith('HostName='):
						host = line.split('=', 2)[1].strip()

					elif line.startswith('UserName='):
						user = line.split('=', 2)[1].strip()

		except IOError, err:
			self.output_error(err)

		else:
			if host:
				return unicode(user + '@' + host if user else host, "UTF-8",
						"replace"), unicode(host, 'UTF-8', 'replace')

		return u'PuTTY Session', None




