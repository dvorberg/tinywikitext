# Copyright (C) 2023 Diedrich Vorberg
#
# Contact: diedrich@tux4web.de
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.

from tinymarkup.macro import Macro, MacroLibrary
from tinymarkup.utils import html_start_tag

class TagMacro(Macro):
    """
    Baseclass for macros that provide start and end tags with regular
    wikitext processing in between.

    The default implementation assumes that the macro’s name
    and the HTML tag generated happen to be identical. It also passes
    through the tag’s attributes which allows you to basically write
    HTML tags into your Wiki Text.
    """
    context = None # either "block" or "inline"

    def start_tag(self, *args, **kw):
        return html_start_tag(self.name, **kw)

    def end_tag(self):
        return f"</{self.name}>"

    @property
    def end(self):
        if self.__class__.context == "block":
            return "\n"
        else:
            return ""

class RAWMacro(Macro):
    """
    Baseclass for macros that process the source text between start and
    end tag themselves. These are handed only one argument, the source,
    and the opening tag’s attributes as keyword parameters.
    """
    context = None # "block" or "inline"

    def html(self, source, **params):
        raise NotImplementedError()

class blockquote(TagMacro):
    context = "block"

class div(TagMacro):
    context = "block"

class s(TagMacro):
    context = "inline"

class u(TagMacro):
    context = "inline"


class bibtex(RAWMacro):
    context = "block"

    def html(self, source, **params):
        return f'<pre>\n{repr(params)}\n\n{source.strip()}</pre>'

class pre(RAWMacro):
    context = "block"

    def html(self, source, **params):
        return f'<pre>{source.strip()}</pre>'

class poem(RAWMacro):
    context = "block"

    def html(self, source, **params):
        return f'<pre>\n{repr(params)}\n\n{source.strip()}</pre>'

class DPL(RAWMacro):
    context = "block"

    def html(self, source, **params):
        """
        I don’t even know whats this does.
        """
        return None

class gallery(RAWMacro):
    context = "block"

    def html(self, source, **params):
        return None

class ref(TagMacro):
    context = "inline"

    def start_tag(self, *args, **kw):
        return html_start_tag("span", class_="subdued") + "("

    def end_tag(self):
        return ")</span>"

macro_library = MacroLibrary()
macro_library.register_module(globals())
