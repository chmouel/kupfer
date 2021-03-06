======
kupfer
======

-----------------------------------------------------------------
Convenient command and access tool for applications and documents
-----------------------------------------------------------------

:Author: Ulrik Sverdrup <ulrik.sverdrup@gmail.com>
:Date: 17 September 2009
:Manual section: 1

SYNOPSIS
========

``kupfer`` [ *OPTIONS* | *QUERY* ]

DESCRIPTION
===========

Kupfer is a launcher. You do not primarily use it to search your files,
you use it to summon the object you are thinking about.

Kupfer is written using Python and has a flexible architecture. It can
work with applications and files, recent documents and web browser
bookmarks, and many more types of user data.

The philosophy of Kupfer is simplicity. The implementation is simple,
makes the easy things work first, and does not overimplement unnecessary
parts of the program.

SPAWNING
========

Running kupfer on the command line (without options) will try to summon
it if already running.

If the keybinder module is installed, kupfer will listen to a
keybinding. By default the keybinding is ``<Control>space`` to focus
kupfer.

Kupfer can be invoked with a text query, with

        ``kupfer`` *QUERY*

This can be used to focus files given as command-line arguments with
kupfer.

OPTIONS
=======

--no-splash     Launch without presenting main interface

--list-plugins  Display a list of all available plugins

--debug         Enable more verbose output that can help understanding
                program operation.

The following are generic options

--help          Display usage information

--version       Display version information

CONFIGURATION
=============

Custom plugins are added to kupfer by installing them to the directory
*~/.local/share/kupfer/plugins*, or any kupfer/plugins directory in any
of ``$XDG_DATA_DIRS``.

.. vim: ft=rst tw=72
.. this document best viewed with::
        rst2pdf Quickstart.rst && xdg-open Quickstart.pdf
