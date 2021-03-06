# Copyright (C) 2009 Ulrik Sverdrup <ulrik.sverdrup@gmail.com>
#
# This program is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation; either version 2, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc., 51 Franklin
# St, Fifth Floor, Boston, MA 02110-1301 USA

"""
This is a Nautilus Extension for Kupfer

It is a Menu Provider, but needs not show a menu. This Extension will be
updated with all file selections in Nautilus, and broadcast them over a D-Bus
signal.
"""

import locale

import dbus
import dbus.glib
from dbus.gobject_service import ExportedGObject
import gio
import gobject, nautilus

service_name="se.kaizer.KupferNautilusPlugin"
interface_name="se.kaizer.KupferNautilusPlugin"
object_path = "/se/kaizer/kupfer/NautilusPlugin"

class Object (ExportedGObject):
	@dbus.service.signal(interface_name, signature="aay")
	def SelectionChanged(self, paths):
		"""Nautilus selection changed. Passes an array of byte strings;
		We have no idea which encoding the filesystem uses, so we
		send filesystem bytes; the receiver should use glib to
		decode the byte strings to strings.
		"""
		return paths

	@dbus.service.signal(interface_name, signature="as")
	def SelectionChangedStrings(self, paths):
		"""Nautilus selection changed. Passes an array of strings;
		We guess the filesystem encoding, and any files that cannot be
		decoded are skipped
		"""
		return paths

class KupferSelectionProvider(nautilus.MenuProvider):
	def __init__(self):
		selfname = type(self).__name__
		print "Initializing", selfname
		self.cur_selection = []
		self.max_threshold = 500
		try:
			session_bus = dbus.Bus()
		except dbus.DBusException, exc:
			print exc
			self.service = None
		else:
			if session_bus.name_has_owner(service_name):
				self.service = None
				print selfname, "already running"
			else:
				bus_name = dbus.service.BusName(service_name, bus=session_bus)
				self.service = Object(bus_name, object_path=object_path)
	
	def get_file_items(self, window, files):
		"""We show nothing, but we get info on files that are selected

		Ask GIO for the file path of each URI item, and pass on any that
		have a defined path.
		Then we try to decode the paths to strings to send if possible to
		decode using the current encoding.

		We use a threshold on the files so that we don't generate too much
		traffic; with more than 500 files selected, we simply send nothing.
		"""
		if len(files) > self.max_threshold:
			return
		uris = (f.get_uri() for f in files)
		paths = filter(None, (gio.File(u).get_path() for u in uris))
		# try to decode filesystem strings
		ustrs = []
		encoding = locale.getpreferredencoding()
		for p in paths:
			try:
				pdec = p.decode(encoding)
			except UnicodeDecodeError:
				continue
			ustrs.append(pdec)
		if paths != self.cur_selection and self.service:
			self.service.SelectionChanged(paths)
			self.service.SelectionChangedStrings(ustrs)
		self.cur_selection = paths
		return

		# Put "Send to Kupfer" item here
		"""
		item = nautilus.MenuItem('PostrExtension::upload_files',
								 _('Upload to Flickr...'),
								 _('Upload the selected files into Flickr'))
		item.connect('activate', self.upload_files, files)

		return item,
		"""
		pass
