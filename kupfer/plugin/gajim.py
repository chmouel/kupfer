# -*- coding: UTF-8 -*-
import os
import dbus

from kupfer.objects import Leaf, Action, Source, AppLeafContentMixin, AppLeaf
from kupfer import pretty

__kupfer_name__ = _("Gajim")
__kupfer_sources__ = ("ContactsSource", )
__kupfer_actions__ = ("ChangeStatus", )
__description__ = _("Access to Gajim Contacts")
__version__ = "0.1"
__author__ = "Karol Będkowski <karol.bedkowski@gmail.com>"



_STATUSES = {
		'online':	_('Available'),
		'chat':		_('Free for Chat'),
		'away':		_('Away'),
		'xa':		_('Not Available'),
		'dnd':		_('Busy'),
		'invisible':_('Invisible'),
		'offline':	_('Offline')
}


def _create_dbus_connection(activate=False):
	''' Create dbus connection to Gajim 
		@activate: true=starts gajim if not running
	'''
	interface = None
	sbus = dbus.SessionBus()
	try:
		#check for running gajim (code from note.py)
		proxy_obj = sbus.get_object('org.freedesktop.DBus', '/org/freedesktop/DBus')
		dbus_iface = dbus.Interface(proxy_obj, 'org.freedesktop.DBus')
		if activate or dbus_iface.NameHasOwner('org.gajim.dbus'):
			obj = sbus.get_object('org.gajim.dbus', '/org/gajim/dbus/RemoteObject')
			if obj:
				interface = dbus.Interface(obj, 'org.gajim.dbus.RemoteInterface')

	except dbus.exceptions.DBusException, err:
		pretty.print_debug(err)

	return interface


class GajimContact(Leaf):
	""" Leaf represent single contact from Gajim """

	def __init__(self, name, jid, account, status, resource):
		# @obj should be unique for each contact
		# we use @jid as an alias for this contact
		obj = (account, jid)
		Leaf.__init__(self, obj, name or jid)

		if unicode(self) != jid:
			self.name_aliases.add(jid)

		self._description = _("[%(status)s] %(userid)s/%(service)s") % \
				{
					"status": _STATUSES.get(status, status),
					"userid": jid,
					"service": resource[0][0] if resource else u"",
				}

	def get_actions(self):
		yield OpenChat()

	def get_description(self):
		return self._description

	def get_icon_name(self):
		return "stock_person"


class AccountStatus(Leaf):
	pass


class OpenChat(Action):
	def __init__(self):
		Action.__init__(self, _('Open Chat'))

	def activate(self, leaf):
		interface = _create_dbus_connection()
		account, jid = leaf.object
		if interface is not None:
			interface.open_chat(jid, account)

	def get_icon_name(self):
		return 'gajim'


class ChangeStatus(Action):
	''' Change global status '''
	rank_adjust = 5

	def __init__(self):
		Action.__init__(self, _('Change Global Status To...'))

	def activate(self, leaf, iobj):
		interface = _create_dbus_connection((iobj.object != 'offline'))
		if interface:
			interface.change_status(iobj.object, '', '')

	def item_types(self):
		yield AppLeaf

	def valid_for_item(self, leaf):
		return leaf.get_id() == 'gajim'

	def requires_object(self):
		return True

	def object_types(self):
		yield AccountStatus

	def object_source(self, for_item=None):
		return StatusSource()

import time
class ContactsSource(AppLeafContentMixin, Source):
	''' Get contacts from all on-line accounts in Gajim via DBus '''
	appleaf_content_id = 'gajim'

	def __init__(self):
		Source.__init__(self, _('Gajim Contacts'))

	def get_items(self):
		st = time.time()
		print "enter get_items", st
		interface = _create_dbus_connection()
		if interface is None:
			return
		print "connected", time.time() - st
		num = 0
		
		for account in interface.list_accounts():
			if interface.get_status(account) == 'offline':
				continue

			for contact in interface.list_contacts(account):
				num += 1
				yield GajimContact(contact['name'], contact['jid'], account, \
						contact['show'], contact['resources'])
		print "sent all", time.time() - st, "for %d contacts" % num

	def is_dynamic(self):
		return True

	def get_icon_name(self):
		return 'gajim'

	def provides(self):
		yield GajimContact


class StatusSource(Source):
	def __init__(self):
		Source.__init__(self, _("Gajim Account Status"))

	def get_items(self):
		for status, name in _STATUSES.iteritems():
			yield AccountStatus(status, name)

	def provides(self):
		yield AccountStatus

