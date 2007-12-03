import gnomevfs
from os import path

def get_dirlist(folder, depth=0, include=None, exclude=None):
	"""
	Return a list of absolute paths in folder
	include, exclude: a function returning a boolean
	def include(filename):
		return ShouldInclude
	"""
	from os import walk
	paths = []
	def include_file(file):
		return (not include or include(file)) and (not exclude or not exclude(file))
		
	for dirname, dirnames, fnames in walk(folder):
		# skip deep directories
		head, dp = dirname, 0
		while not path.samefile(head, folder):
			head, tail = path.split(head)
			dp += 1
		if dp > depth:
			del dirnames[:]
			continue
		
		excl_dir = []
		for dir in dirnames:
			if not include_file(dir):
				excl_dir.append(dir)
				continue
			abspath = path.join(dirname, dir)
			paths.append(abspath)
		
		for file in fnames:
			if not include_file(file):
				continue
			abspath = path.join(dirname, file)
			paths.append(abspath)

		for dir in reversed(excl_dir):
			dirnames.remove(dir)

	return paths

def get_icon_for_uri(uri, icon_size=48):
	"""
	Return a pixbuf representing the file at
	the URI generally (mime-type based)

	return None if not found
	
	@param icon_size: a pixel size of the icon
	@type icon_size: an integer object.
	 
	"""
	from gtk import icon_theme_get_default, ICON_LOOKUP_USE_BUILTIN
	from gnomevfs import get_mime_type
	from gnome.ui import ThumbnailFactory, icon_lookup

	mtype = get_mime_type(uri)
	icon_theme = icon_theme_get_default()
	thumb_factory = ThumbnailFactory(16)
	icon_name, num = icon_lookup(icon_theme, thumb_factory,  file_uri=uri, custom_icon="")
	return get_icon_for_name(icon_name, icon_size)

def get_icon_for_name(icon_name, icon_size=48):
	from gtk import icon_theme_get_default, ICON_LOOKUP_USE_BUILTIN
	from gobject import GError
	icon_theme = icon_theme_get_default()
	try:
		icon = icon_theme.load_icon(icon_name, icon_size, ICON_LOOKUP_USE_BUILTIN)
	except GError:
		return None
	return icon

def get_desktop_icon(desktop_file, icon_size=48):
	"""
	Return the pixbuf of a desktop file

	Use some hackery. Take the icon directly if it is absolutely given,
	otherwise use the name minus extension from current icon theme
	"""
	from gtk import icon_theme_get_default
	from gnomedesktop import item_new_from_basename, find_icon, LOAD_ONLY_IF_EXISTS, KEY_ICON
	desktop = item_new_from_basename(desktop_file, LOAD_ONLY_IF_EXISTS)
	icon_name = desktop.get_string(KEY_ICON)
	if not icon_name:
		return None
	print icon_name

	if not path.isabs(icon_name):
		icon_name, extension = path.splitext(icon_name)
		icon_info = icon_theme_get_default().lookup_icon(icon_name, icon_size, 0)
		if icon_info:
			icon_file = icon_info.get_filename()
		else:
			icon_file = None
	else:
		icon_file = icon_name

	#icon_file = desktop.get_icon(icon_theme_get_default())
	print icon_file

	if not icon_file:
		return None
	return get_icon_from_file(icon_file, icon_size)


def get_icon_from_file(icon_file, icon_size=48):
	from gtk.gdk import pixbuf_new_from_file_at_size
	return pixbuf_new_from_file_at_size(icon_file, icon_size, icon_size)


def get_default_application_icon(icon_size=48):
	icon = get_icon_for_name("exec", icon_size)
	return icon

def spawn_async(argv, in_dir=None):
	import gobject
	from os import chdir, getcwd
	if in_dir:
		oldwd = getcwd()
		chdir(in_dir)
	ret = gobject.spawn_async (argv, flags=gobject.SPAWN_SEARCH_PATH)
	if in_dir:
		chdir(oldwd)

def get_xdg_data_dirs():
	"""
	Return a list of XDG data directories

	From the deskbar applet project
	"""
	import os

	dirs = os.getenv("XDG_DATA_HOME")
	if dirs == None:
		dirs = os.path.expanduser("~/.local/share")
	
	sysdirs = os.getenv("XDG_DATA_DIRS")
	if sysdirs == None:
		sysdirs = "/usr/local/share:/usr/share"
	
	dirs = "%s:%s" % (dirs, sysdirs)
	return [dir for dir in dirs.split(":") if dir.strip() != "" and path.exists(dir)]

def find_desktop_file(basename):
	"""
	Return the absolute path to desktop file basename

	if not found return None
	"""
	dirs = get_xdg_data_dirs()
	for d in dirs:
		abs = path.join(d, "applications", basename)
		if path.exists(abs):
			return abs
	return None
