#!/usr/bin/python3
# -*- coding: utf-8 -*-

# HTML preview of Markdown formatted text in gedit
# Copyright © 2005, 2006 Michele Campeotto
# Copyright © 2009 Jean-Philippe Fleury <contact@jpfleury.net>

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import gi
gi.require_version('WebKit2', '4.0')
from gi.repository import Gdk, Gtk, Gedit, GObject, WebKit2, Gio
import codecs
import os
import sys
import markdown
import gettext
from configparser import ConfigParser
import webbrowser

try:
	appName = "markdown-preview"
	fileDir = os.path.dirname(__file__)
	localePath = os.path.join(fileDir, "locale")
	gettext.bindtextdomain(appName, localePath)
	gettext.textdomain(appName)
	_ = gettext.gettext
except:
	_ = lambda s: s

# Can be used to add default HTML code (e.g. default header section with CSS).
htmlTemplate = ""
with open("template.html", 'r') as f:
	htmlTemplate = f.read()

# Configuration.

markdownExternalBrowser = "0"
markdownPanel = "bottom"
markdownShortcut = "<Control><Alt>m"
markdownExtensions = "extra toc"
markdownVisibility = "1"
markdownVisibilityShortcut = "<Control><Alt>v"

try:
	import xdg.BaseDirectory
except ImportError:
	homeDir = os.environ.get("HOME")
	xdgConfigHome = os.path.join(homeDir, ".config")
else:
	xdgConfigHome = xdg.BaseDirectory.xdg_config_home

confDir =  os.path.join(xdgConfigHome, "gedit")
confFile =  os.path.join(confDir, "gedit-markdown.ini")

parser = ConfigParser()
parser.optionxform = str
parser.add_section("markdown-preview")
parser.set("markdown-preview", "externalBrowser", markdownExternalBrowser)
parser.set("markdown-preview", "panel", markdownPanel)
parser.set("markdown-preview", "shortcut", markdownShortcut)
parser.set("markdown-preview", "extensions", markdownExtensions)
parser.set("markdown-preview", "visibility", markdownVisibility)
parser.set("markdown-preview", "visibilityShortcut", markdownVisibilityShortcut)

if os.path.isfile(confFile):
	parser.read(confFile)
	markdownExternalBrowser = parser.get("markdown-preview", "externalBrowser")
	markdownPanel = parser.get("markdown-preview", "panel")
	markdownShortcut = parser.get("markdown-preview", "shortcut")
	markdownExtensions = parser.get("markdown-preview", "extensions")
	markdownExtensionsList = markdownExtensions.split()
	markdownVisibility = parser.get("markdown-preview", "visibility")
	markdownVisibilityShortcut = parser.get("markdown-preview", "visibilityShortcut")

if not os.path.exists(confDir):
	os.makedirs(confDir)

with open(confFile, "w") as confFile:
	parser.write(confFile)

class MarkdownPreviewPlugin(GObject.Object, Gedit.WindowActivatable):
	__gtype_name__ = "MarkdownPreviewPlugin"
	window = GObject.property(type=Gedit.Window)
	actions = []
	currentUri = ""
	overLinkUrl = ""

	def __init__(self):
		GObject.Object.__init__(self)

	def do_activate(self):
		self.scrolledWindow = Gtk.ScrolledWindow()
		self.scrolledWindow.set_property("hscrollbar-policy", Gtk.PolicyType.AUTOMATIC)
		self.scrolledWindow.set_property("vscrollbar-policy", Gtk.PolicyType.AUTOMATIC)
		self.scrolledWindow.set_property("shadow-type", Gtk.ShadowType.IN)

		self.htmlView = WebKit2.WebView()
		self.htmlView.connect("mouse-target-changed", self.onMouseTargetChangedCb)
		self.htmlView.connect("decide-policy", self.onDecidePolicyCb)
		self.htmlView.connect("context-menu", self.onContextMenuCb)
		self.htmlView.load_html((htmlTemplate % ("", )), "file:///")

		self.scrolledWindow.add(self.htmlView)
		self.scrolledWindow.show_all()

		if markdownVisibility == "1":
			self.addMarkdownPreviewTab()

		self.addWindowActions()

	def do_deactivate(self):
		# Remove actions
		self.window.remove_action('MarkdownPreview')
		self.window.remove_action('ToggleTab')
		for action in self.actions:
			action = self.window.remove_action(action.get_name())
		# Remove Markdown Preview from the panel.
		self.removeMarkdownPreviewTab()
		# delete instance variables
		self.action_update = None
		self.action_toggle = None
		for action in self.actions:
			action = None
		self.scrolledWindow = None
		self.htmlView = None

	def addMarkdownPreviewTab(self):
		if markdownPanel == "side":
			panel = self.window.get_side_panel()
		else:
			panel = self.window.get_bottom_panel()

		panel.add_titled(self.scrolledWindow, "MarkdownPreview", _("Markdown Preview"))
		panel.show()
		panel.set_visible_child(self.scrolledWindow)

	def addWindowActions(self):
		self.action_update = Gio.SimpleAction(name='MarkdownPreview')
		self.action_update.connect('activate', lambda x, y: self.updatePreview(y, False))
		self.window.add_action(self.action_update)

		self.action_toggle = Gio.SimpleAction(name='ToggleTab')
		self.action_toggle.connect('activate', lambda x, y: self.toggleTab())
		self.window.add_action(self.action_toggle)

	def addWindowAction(self, func):
		action = Gio.SimpleAction(name="MarkdownAction"+str(len(self.actions)))
		action.connect('activate', func)
		self.window.add_action(action)
		self.actions.append(action)
		return action

	def copyCurrentUrl(self):
		self.clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
		self.clipboard.set_text(self.currentUri, -1)

	def goToAnotherUrl(self):
		newUrl = self.goToAnotherUrlDialog()

		if newUrl:
			if newUrl.startswith("/"):
				newUrl = "file://" + newUrl

			self.htmlView.load_uri(newUrl)

	def goToAnotherUrlDialog(self):
		dialog = Gtk.MessageDialog(None,
		                           Gtk.DialogFlags.MODAL | Gtk.DialogFlags.DESTROY_WITH_PARENT,
		                           Gtk.MessageType.QUESTION,
		                           Gtk.ButtonsType.OK_CANCEL,
		                           _("Enter URL"))
		dialog.set_title(_("Enter URL"))
		dialog.format_secondary_markup(_("Enter the URL (local or distant) of the document or page to display."))

		entry = Gtk.Entry()
		entry.connect("activate", self.onGoToAnotherUrlDialogActivateCb, dialog,
		              Gtk.ResponseType.OK)

		dialog.vbox.pack_end(entry, True, True, 0)
		dialog.show_all()

		response = dialog.run()

		newUrl = ""

		if response == Gtk.ResponseType.OK:
			newUrl = entry.get_text()

		dialog.destroy()

		return newUrl

	def onGoToAnotherUrlDialogActivateCb(self, entry, dialog, response):
		dialog.response(response)

	def onMouseTargetChangedCb(self, view, hitTestResult, modifiers):
		if hitTestResult.context_is_link():
			url = hitTestResult.get_link_uri()
			self.overLinkUrl = url

			self.urlTooltip = Gtk.Window.new(Gtk.WindowType.POPUP)
			self.urlTooltip.set_border_width(2)
			self.urlTooltip.modify_bg(0, Gdk.color_parse("#d9d9d9"))

			label = Gtk.Label()
			text = (url[:75] + "...") if len(url) > 75 else url
			label.set_text(text)
			label.modify_fg(0, Gdk.color_parse("black"))
			self.urlTooltip.add(label)
			label.show()

			self.urlTooltip.show()

			xPointer, yPointer = self.urlTooltip.get_pointer()

			xWindow = self.window.get_position()[0]
			widthWindow = self.window.get_size()[0]

			widthUrlTooltip = self.urlTooltip.get_size()[0]
			xUrlTooltip = xPointer
			yUrlTooltip = yPointer + 15

			xOverflow = (xUrlTooltip + widthUrlTooltip) - (xWindow + widthWindow)

			if xOverflow > 0:
				xUrlTooltip = xUrlTooltip - xOverflow

			self.urlTooltip.move(xUrlTooltip, yUrlTooltip)
		else:
			self.overLinkUrl = ""

			if self.urlTooltipVisible():
				self.urlTooltip.destroy()

	def onDecidePolicyCb(self, view, polDec, polDecType):
		if (polDecType == WebKit2.PolicyDecisionType.NAVIGATION_ACTION or
			polDecType == WebKit2.PolicyDecisionType.NEW_WINDOW_ACTION): # type(polDec) == WebKit2.NavigationPolicyDecision
			networkRequest = polDec.get_request()
			navType = polDec.get_navigation_type()
			ignore = False
			currentUri = networkRequest.get_uri()

			if currentUri.startswith("file://"):
				# local file
				if currentUri == "file://"+self.window.get_active_document().get_uri_for_display():
					# Ignore navigation to current document (should be markdown rendered instead)
					polDec.ignore()
					ignore = True

			elif navType == WebKit2.NavigationType.LINK_CLICKED and markdownExternalBrowser == "1":
				webbrowser.open_new_tab(currentUri)

				if self.urlTooltipVisible():
					self.urlTooltip.destroy()

				polDec.ignore()
				ignore = True

			if not ignore:
				self.currentUri = currentUri
		elif polDecType == WebKit2.PolicyDecisionType.RESPONSE:  # type(decision) == WebKit2.ResponsePolicyDecision
			# Allow all responses
			polDec.use()
		else:  # WebKit2.PolicyDecision
			# Forbid everything else
			polDec.ignore()

		return False

	def openInEmbeddedBrowser(self):
		self.htmlView.load_uri(self.overLinkUrl)

	def openInExternalBrowser(self):
		webbrowser.open_new_tab(self.overLinkUrl)

	def onContextMenuCb(self, view, menu, event, hitTestResult):
		if self.urlTooltipVisible():
			self.urlTooltip.destroy()

		for item in menu.get_items():
			try:
				stockAction = item.get_stock_action()
				if (stockAction == WebKit2.ContextMenuAction.COPY_LINK_TO_CLIPBOARD or
					stockAction == WebKit2.ContextMenuAction.GO_BACK or
					stockAction == WebKit2.ContextMenuAction.GO_FORWARD or
					stockAction == WebKit2.ContextMenuAction.STOP):
					continue
				elif stockAction == WebKit2.ContextMenuAction.RELOAD:
					if self.currentUri.startswith("file:///"):
						# NOTE can't disable item: item.get_gaction().get_state_hint()
						menu.remove(item)
				else:
					menu.remove(item)
			except:
				menu.remove(item)

		if self.overLinkUrl:
			if markdownExternalBrowser == "1":
				action = self.addWindowAction(lambda x, y: self.openInEmbeddedBrowser())
				item = WebKit2.ContextMenuItem.new_from_gaction(action, _("Open in the embedded browser"))
			else:
				action = self.addWindowAction(lambda x, y: self.openInExternalBrowser())
				item = WebKit2.ContextMenuItem.new_from_gaction(action, _("Open in an external browser"))

			menu.append(item)

		action = self.addWindowAction(lambda x, y: self.copyCurrentUrl())
		item = WebKit2.ContextMenuItem.new_from_gaction(action, _("Copy the current URL"))
		if self.currentUri == "file:///":
			# TODO SimpleAction.new_stateful() -> disabled
			pass
		menu.append(item)

		action = self.addWindowAction(lambda x, y: self.goToAnotherUrl())
		item = WebKit2.ContextMenuItem.new_from_gaction(action, _("Go to another URL"))
		menu.append(item)

		item = WebKit2.ContextMenuItem.new_from_gaction(self.action_update, _("Update Preview"))
		documents = self.window.get_documents()
		if not documents:
			# TODO SimpleAction.new_stateful() -> disabled
			pass
		menu.append(item)

		action = self.addWindowAction(lambda x, y: self.updatePreview(self, True))
		item = WebKit2.ContextMenuItem.new_from_gaction(action, _("Clear Preview"))
		menu.append(item)

	def removeMarkdownPreviewTab(self):
		if markdownPanel == "side":
			panel = self.window.get_side_panel()
		else:
			panel = self.window.get_bottom_panel()

		panel.remove(self.scrolledWindow)

	def toggleTab(self):
		if markdownPanel == "side":
			panel = self.window.get_side_panel()
		else:
			panel = self.window.get_bottom_panel()

		if panel.get_visible_child() == self.scrolledWindow:
			self.removeMarkdownPreviewTab()
		else:
			self.addMarkdownPreviewTab()

	def updatePreview(self, window, clear):
		view = self.window.get_active_view()

		if not view and not clear:
			return

		html = ""
		activeUri = "file:///"

		if not clear:
			doc = view.get_buffer()
			start = doc.get_start_iter()
			end = doc.get_end_iter()

			if doc.get_selection_bounds():
				start = doc.get_iter_at_mark(doc.get_insert())
				end = doc.get_iter_at_mark(doc.get_selection_bound())

			text = doc.get_text(start, end, True)

			html = htmlTemplate % (markdown.markdown(text, extensions=markdownExtensionsList), )

			activeUri = "file://"+self.window.get_active_document().get_uri_for_display()  # Absolute paths when existing file

		placement = self.scrolledWindow.get_placement()

		htmlDoc = self.htmlView
		self.htmlView.load_alternate_html(html, activeUri, self.uriToBase(activeUri))

		self.scrolledWindow.set_placement(placement)

		if markdownPanel == "side":
			panel = self.window.get_side_panel()
		else:
			panel = self.window.get_bottom_panel()

		panel.show()

		if not panel.get_visible_child() == self.scrolledWindow:
			self.addMarkdownPreviewTab()
			panel.set_visible_child(self.scrolledWindow)

	def uriToBase(self, uri):
		# special cases: "file:///", "Untitled Document"
		return uri.rpartition("/")[0]+"/"

	def urlTooltipVisible(self):
		if hasattr(self, "urlTooltip") and self.urlTooltip.get_property("visible"):
			return True

		return False

class MarkdownPreviewMenu(GObject.Object, Gedit.AppActivatable):
	app = GObject.property(type=Gedit.App)

	def __init__(self):
		GObject.Object.__init__(self)

	def do_activate(self):
		self.app.set_accels_for_action("win.MarkdownPreview", [markdownShortcut])
		self.app.set_accels_for_action("win.ToggleTab", [markdownVisibilityShortcut])

		self.tools_menu_ext = self.extend_menu("tools-section")

		md_prev_update = Gio.MenuItem.new(_("Update Markdown Preview"), "win.MarkdownPreview")
		md_prev_toggle = Gio.MenuItem.new(_("Toggle Markdown Preview Visibility"), "win.ToggleTab")

		self.tools_menu_ext.append_menu_item(md_prev_update)
		self.tools_menu_ext.append_menu_item(md_prev_toggle)

	def do_deactivate(self):
		self.app.set_accels_for_action("win.MarkdownPreview", [])
		self.app.set_accels_for_action("win.ToggleTab", [])

		self.tools_menu_ext = None
