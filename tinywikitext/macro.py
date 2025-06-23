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

from tinymarkup.exceptions import UnsuitableMacro
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
    def start_tag(self, *args, **kw):
        return html_start_tag(self.name, **kw)

    def end_tag(self):
        return f"</{self.name}>"

    def start_searchable_text_block(self, compiler, *args, **kw):
        # compiler.push_weight(...)
        pass

    def end_searchable_text_block(self, compiler):
        # compiler.pop_weight()
        pass

class RAWMacro(Macro):
    """
    Baseclass for macros that process the source text between start and
    end tag themselves. These are handed only one argument, the source,
    and the opening tag’s attributes as keyword parameters.
    """
    def html(self, source, **params):
        raise NotImplementedError()

    def add_searchable_text(self, writer, *args):
        # compiler.write(text, language, weight)
        pass

class LinkMacro(Macro):
    """
    Baseclass for those macros that use the syntax of a link (with
    a Wiki Text “namespace” as for example [[Image:file.jpg]].
    """
    def html(self, *params):
        raise NotImplementedError()

    def add_searchable_text(self, writer, *args):
        # compiler.write(text, language, weight)
        pass

class blockquote(TagMacro):
    environments = { "block" }

class div(TagMacro):
    environments = { "block" }

class s(TagMacro):
    environments = { "inline" }

class u(TagMacro):
    environments = { "inline" }

macro_library = MacroLibrary()
macro_library.register_module(globals())
