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
from gi.repository import Gdk, Gtk, GtkSource, Gedit, GObject, WebKit2, Gio
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

markdownPanel = "bottom"
markdownShortcut = "<Control><Alt>m"
markdownExtensions = "extra toc"
markdownVisibility = "1"
markdownVisibilityShortcut = "<Control><Alt>v"
markdownAutoReload = "1"
markdownAutoReloadSelection = "1"

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
parser.set("markdown-preview", "panel", markdownPanel)
parser.set("markdown-preview", "shortcut", markdownShortcut)
parser.set("markdown-preview", "extensions", markdownExtensions)
parser.set("markdown-preview", "visibility", markdownVisibility)
parser.set("markdown-preview", "visibilityShortcut", markdownVisibilityShortcut)
parser.set("markdown-preview", "autoReload", markdownAutoReload)
parser.set("markdown-preview", "autoReloadSelection", markdownAutoReloadSelection)

if os.path.isfile(confFile):
	parser.read(confFile)
	markdownPanel = parser.get("markdown-preview", "panel")
	markdownShortcut = parser.get("markdown-preview", "shortcut")
	markdownExtensions = parser.get("markdown-preview", "extensions")
	markdownExtensionsList = markdownExtensions.split()
	markdownVisibility = parser.get("markdown-preview", "visibility")
	markdownVisibilityShortcut = parser.get("markdown-preview", "visibilityShortcut")
	markdownAutoReload = parser.get("markdown-preview", "autoReload")
	markdownAutoReloadSelection = parser.get("markdown-preview", "autoReloadSelection")

if not os.path.exists(confDir):
	os.makedirs(confDir)

with open(confFile, "w") as confFile:
	parser.write(confFile)

class MarkdownPreviewPlugin(GObject.Object, Gedit.WindowActivatable):
	__gtype_name__ = "MarkdownPreviewPlugin"
	window = GObject.property(type=Gedit.Window)

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
		self.updatePreview()

		self.scrolledWindow.add(self.htmlView)
		self.scrolledWindow.show_all()

		if markdownVisibility == "1":
			self.addMarkdownPreviewTab()

		self.addWindowActions()

		self.handleTabChanged = self.window.connect("active-tab-changed", self.onTabChangedCb)
		self.handleTabStateChanged = self.window.connect("active-tab-state-changed", self.onTabChangedCb)
		self.addBufferSignals()

	# This is called every time the document is changed
	def do_update_state(self, *args):
		if markdownAutoReload == "1":
			self.updatePreview(self.window)

	def do_deactivate(self):
		# Remove actions
		self.window.remove_action('MarkdownPreview')
		self.window.remove_action('ToggleTab')
		# Remove Markdown Preview from the panel.
		self.removeMarkdownPreviewTab()
		# delete instance variables
		self.action_update = None
		self.action_toggle = None
		self.scrolledWindow = None
		self.htmlView = None
		self.window.disconnect(self.handleTabChanged)
		self.window.disconnect(self.handleTabStateChanged)
		self.removeBufferSignals()


	# Windows and Signals

	def addMarkdownPreviewTab(self):
		if markdownPanel == "side":
			panel = self.window.get_side_panel()
		else:
			panel = self.window.get_bottom_panel()

		panel.add_titled(self.scrolledWindow, "MarkdownPreview", _("Markdown Preview"))
		panel.show()
		panel.set_visible_child(self.scrolledWindow)

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

	def addWindowActions(self):
		self.action_update = Gio.SimpleAction(name='MarkdownPreview')
		self.action_update.connect('activate', lambda x, y: self.updatePreview())
		self.window.add_action(self.action_update)

		self.action_toggle = Gio.SimpleAction(name='ToggleTab')
		self.action_toggle.connect('activate', lambda x, y: self.toggleTab())
		self.window.add_action(self.action_toggle)

	def addBufferSignals(self):
		self.removeBufferSignals()

		if markdownAutoReloadSelection == "1":
			view = self.window.get_active_view()
			if view:
				self.handleBuffer = view.get_buffer()
				self.handleMarkSet = self.handleBuffer.connect("mark-set", self.onMarkSetCb)
				self.handleDocumentLoaded = self.handleBuffer.connect("loaded", self.onDocumentLoadedCb)

	def removeBufferSignals(self):
		if (hasattr(self, "handleMarkSet") and self.handleMarkSet is not None and
			hasattr(self, "handleBuffer") and self.handleBuffer is not None):
			self.handleBuffer.disconnect(self.handleMarkSet)
			self.handleBuffer.disconnect(self.handleDocumentLoaded)
			del self.handleBuffer
			del self.handleMarkSet
			del self.handleDocumentLoaded

	def urlTooltipCreate(self, url):
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

	def urlTooltipDestroy(self):
		if hasattr(self, "urlTooltip") and self.urlTooltip.get_property("visible"):
			self.urlTooltip.destroy()


	# Callbacks

	def onTabChangedCb(self, *args):
		self.addBufferSignals()

		self.updatePreview()

	def onMarkSetCb(self, buf, loc, mark):
		if mark.get_name() == "insert":
			doc = self.handleBuffer
			start = doc.get_iter_at_mark(doc.get_selection_bound())
			end = doc.get_iter_at_mark(mark)
			if not start.equal(end):
				# selection changed
				self.updatePreview()
				self.activeSelection = True
			else:
				if hasattr(self, "activeSelection") and self.activeSelection:
					# selection removed
					self.updatePreview()
					self.activeSelection = False

	def onDocumentLoadedCb(self, *args):
		self.updatePreview()

	def onMouseTargetChangedCb(self, view, hitTestResult, modifiers):
		self.urlTooltipDestroy()

		if hitTestResult.context_is_link():
			self.urlTooltipCreate(hitTestResult.get_link_uri())

	def onDecidePolicyCb(self, view, decision, decisionType):
		if decisionType == WebKit2.PolicyDecisionType.NAVIGATION_ACTION: # type(decision) == WebKit2.NavigationPolicyDecision
			# Navigate to new uri
			currentUri = decision.get_request().get_uri()
			if currentUri.startswith("file:///"):
				# allow navigating local files
				if currentUri.startswith("file://"+self.window.get_active_document().get_uri_for_display()):
					# re-render current document to allow "back" functionality
					self.updatePreview()
					decision.ignore()
				else:
					# render other local files
					lang = GtkSource.LanguageManager.get_default().guess_language(currentUri, None)
					if lang is None:
						self.render()
					if lang.get_id() == "html":
						decision.use()
					elif lang.get_id() == "markdown":
						with open(currentUri[7:], 'r') as file:  # remove "file://"
							text = file.read()
							self.render(text, currentUri, True)
					else:
						self.render()
			else:
				# open in new browser tab
				webbrowser.open_new_tab(currentUri)
				self.urlTooltipDestroy()
				decision.ignore()
		elif decisionType == WebKit2.PolicyDecisionType.NEW_WINDOW_ACTION:  # type(decision) == WebKit2.NavigationPolicyDecision
			# Forbid new windows
			decision.ignore()
		elif decisionType == WebKit2.PolicyDecisionType.RESPONSE:  # type(decision) == WebKit2.ResponsePolicyDecision
			# Allow all responses
			decision.use()
		else:  # WebKit2.PolicyDecision
			# Forbid everything else
			decision.ignore()

		return True

	def onContextMenuCb(self, view, menu, event, hitTestResult):
		self.urlTooltipDestroy()

		for item in menu.get_items():
			try:
				stockAction = item.get_stock_action()
				if (stockAction == WebKit2.ContextMenuAction.OPEN_LINK or
					stockAction == WebKit2.ContextMenuAction.COPY_LINK_TO_CLIPBOARD or
					stockAction == WebKit2.ContextMenuAction.GO_BACK or
					stockAction == WebKit2.ContextMenuAction.GO_FORWARD):
					continue
				else:
					menu.remove(item)
			except:
				menu.remove(item)

		item = WebKit2.ContextMenuItem.new_from_gaction(self.action_update, _("Update Preview"))
		menu.append(item)


	# Rendering

	def updatePreview(self, *args):
		view = self.window.get_active_view()
		if not view:
			return
		doc = view.get_buffer()
		lang = doc.get_language()
		if lang and lang.get_id() in ["markdown", "html"]:
			start = doc.get_start_iter()
			end = doc.get_end_iter()

			if markdownAutoReloadSelection == "1" and doc.get_selection_bounds():
				start = doc.get_iter_at_mark(doc.get_selection_bound())
				end = doc.get_iter_at_mark(doc.get_insert())

			text = doc.get_text(start, end, True)

			if lang.get_id() == "html":
				isMarkdown = False
			elif lang.get_id() == "markdown":
				isMarkdown = True

			activeUri = "file://"+self.window.get_active_document().get_uri_for_display()  # Absolute paths when existing file

			self.render(text, activeUri, isMarkdown)
		else:
			self.render()  # empty page

	def render(self, html=None, activeUri=None, isMarkdown=False):
		if html is None:
			html = ""
		if activeUri is None:
			activeUri = "file:///"

		self.urlTooltipDestroy()

		placement = self.scrolledWindow.get_placement()

		if isMarkdown:
			html = htmlTemplate % markdown.markdown(html, extensions=markdownExtensionsList)
		self.htmlView.load_alternate_html(html, activeUri, self.uriToBase(activeUri))

		self.scrolledWindow.set_placement(placement)

		if markdownPanel == "side":
			panel = self.window.get_side_panel()
		else:
			panel = self.window.get_bottom_panel()

		panel.show()

	def uriToBase(self, uri):
		# special cases: "file:///", "Untitled Document"
		return uri.rpartition("/")[0]+"/"


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
