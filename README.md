Updates to the original source https://github.com/jpfleury/gedit-markdown:

- works in newer gedit versions (tested on 3.22)
- added custom stylesheet for Markdown Preview, see screenshot bellow

---

**Note: if you use gedit 2 or gedit 3.0 to 3.6, please refer to the [documentation of gedit-markdown v1](https://github.com/jpfleury/gedit-markdown/tree/v1#readme). Below is the documentation of the version 2 for gedit 3.8 and 3.10.**

## Overview

gedit-markdown adds support for Markdown preview in gedit, the default Gnome text editor.

Specifically, it adds:

- Markdown snippets;

- plugin *Markdown Preview* for gedit, displayed in the side panel or the bottom panel and previewing in HTML the current document or selection;

- an external tool exporting to HTML the current document or selection;

![screenshot1](doc/exemple1.png "Default Markdown syntax highlighting in gedit.")

## Requirements

- gedit-markdown v2 supports gedit 3.8 and 3.10. It's shipped with an installer for GNU/Linux.

- The plugin *Markdown Preview* depends on the package `python3-markdown`.

- For users of Ubuntu (and maybe other distributions) 11.10 or later, the package `gir1.2-webkit-3.0` must be installed to use the plugin *Markdown Preview*.

## Installation (or update)

- download and extract the repo
- `$ ./gedit-markdown.sh install`

Markdown support will be added for the current user (so no need root privileges). The folder created by the extraction can be deleted after installation.

## Uninstallation

- Open a terminal in the extracted folder.

- Run the uninstaller in the terminal:

		./gedit-markdown.sh uninstall

## Usage

First of all, restart gedit if it's already running.

### Plugin *Markdown Preview*

To enable this plugin, go to *Edit > Preferences > Plugins* and check *Markdown Preview*.

Two items are added in the gedit menu *Tools*:

- *Update Markdown Preview*: displays in the side panel or in the bottom panel a preview in HTML of the current document or selection.

	Note: there are two other ways to update preview:
	
	  - with the keyboard shortcut *Ctrl+Alt+m* (can be changed in the configuration file);
	
	  - by right clicking on the preview area (side or bottom panel) and selecting the item *Update Preview*.

- *Toggle Markdown Preview visibility*: allows to display or hide the Markdown Preview panel tab.

	Note: the keyboard shortcut *Ctrl+Alt+v* (can be changed in the configuration file) can be used to do the same.

When right clicking on the preview area, a context menu appears and lists several options. Besides the default ones (previous page, next page, copy, etc.), we have:

- *Update Preview*: reloads in the side panel or in the bottom panel the preview in HTML of the current document or selection.

Local files will be followed in the preview area while global ones will be opened with your default web browser.

Here's a screenshot of the plugin when it's displayed in the bottom panel:

![screenshot](doc/exemple3.png "Markdown Preview in the bottom panel of gedit.")

Now the same plugin displayed in the side panel (click to see the original image):

![screenshot](doc/exemple4.png "")

[![screenshot][2]][1]

  [1]: doc/exemple4-grand.png
  [2]: doc/exemple4-petit.png (Markdown Preview in the side panel of gedit.)


Note that when the cursor passes over a link in the preview area, a tooltip displays the URL:

![screenshot](doc/exemple5.png "Tooltip displaying URL when the cursor passes over a link.")

### Table of contents

When the Markdown extension `toc` is enabled (see _Configuration file_, default), add `[TOC]` to your Markdown source to generate a table of contents with clickable links.

### Snippets

To use Markdown snippets, activate the plugin *Snippets* in *Edit > Preferences > Plugins*. Then, go to *Tools > Manage Snippets...* to see the possibilities.

### Converters (external tools)

The following tools are included:

- Export to HTML
- Export to PDF

To use the external tool, activate the plugin *External Tools* in *Edit > Preferences > Plugins*. Then, go to *Tools > External Tools > Export to HTML* to access the tool. The keyboard shortcut *Ctrl+Alt+h* does the same. The code of the currently opened Markdown file or the selection will be converted in HTML/PDF, and the result will be put in a new document.

To edit the tool, go to *Tools > Manage External Tools...*.

### Configuration file

The configuration file of gedit-markdown is the following:

	$XDG_CONFIG_HOME/gedit/gedit-markdown.ini

Most of the time, it will correspond to:

	$HOME/.config/gedit/gedit-markdown.ini

The section `markdown-preview` contains several properties:

- `panel`: emplacement of the preview. Possibles values: `bottom` (default value) or `side`.

- `shortcut`: shortcut to refresh the preview. The default value is `<Control><Alt>m`.

- `extensions`: a whitespace separated list of [Markdown extensions](https://python-markdown.github.io/extensions/#officially-supported-extensions). See link for possible values. Defaults to "extra toc".

- `visibility`: visibility of the Markdown Preview panel tab when gedit starts. Possible values: `0` (hidden) or `1` (displayed; default value).

- `visibilityShortcut`: shortcut to toggle Markdown Preview visibility. The default value is `<Control><Alt>v`.

- `autoReload`: automatically reload the preview when the text is changed. Possible values: `0` (disabled) or `1` (enabled; default value).

- `autoReloadSelection`: automatically reload the preview when the selection is changed. Possible values: `0` (disabled) or `1` (enabled; default value).

## Localization

The plugin *Markdown Preview* is localizable. The file containing strings is `plugins/markdown-preview/locale/markdown-preview.pot`.

## License

Author: Jean-Philippe Fleury (<http://www.jpfleury.net/en/contact.php>)  
Copyright © 2009 Jean-Philippe Fleury

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.

### Third-party code

The plugin *Markdown Preview* shipped with gedit-markdown is a modification of the [plugin of the same name written by Michele Campeotto](https://wiki.gnome.org/Apps/Gedit/MarkdownSupport), under the GPL v2 or any later version.
