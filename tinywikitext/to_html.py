# Copyright (C) 2023–25 Diedrich Vorberg
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

import sys, os, io, copy
from html import escape as escape_html

from tinymarkup.writer import HTMLWriter
from tinymarkup.context import Context
from tinymarkup.exceptions import InternalError
from tinymarkup.cmdline import CmdlineTool

from .compiler import WikiTextCompiler
from .parser import WikiTextParser
from .macro import macro_library

def to_html(wikitext, context:Context=None):
    outfile = io.StringIO()
    parser = WikiTextParser()
    compiler = HTMLCompiler(context, outfile)
    compiler.compile(parser, wikitext)
    return outfile.getvalue()

class HTMLCompiler(WikiTextCompiler):
    def __init__(self, context, output):
        WikiTextCompiler.__init__(self, context)
        self.writer = HTMLWriter(output, context.root_language)

        self.open = self.writer.open
        self.close = self.writer.close
        self.print = self.writer.print

    def begin_document(self, parser):
        super().begin_document(parser)
        self.current_list = None

    def other_characters(self, s:str):
        self.print(escape_html(s), end="")

    def word(self, s:str):
        self.print(s, end="")

    def line_break(self): self.print("<br />", end="")
    def begin_paragraph(self): self.open("p")
    def end_paragraph(self): self.close("p")
    def begin_italic(self): self.open("i")
    def end_italic(self): self.close("i")
    def begin_bold(self): self.open("b")
    def end_bold(self): self.close("b")
    def horizontal_line(self): self.print("<hr />")
    def begin_heading(self, level:int): self.open(f"h{level}")
    def end_heading(self, level:int): self.close(f"h{level}")
    def begin_definition_list(self): self.open("dl")
    def end_definition_list(self): self.close("dl")
    def begin_definition_term(self): self.open("dt")
    def end_definition_term(self): self.close("dt")
    def begin_definition_def(self): self.open("dd")
    def end_definition_def(self): self.close("dd")

    def link(self, text, target=None):
        self.print(self.context.html_link_element(text, target), end="")

    def begin_list_item(self, signature):
        try:
            if self.current_list is None:
                self.current_list = ListManager(self)
            self.current_list.begin_list_item(signature)
        except AssertionError as exc:
            raise InternalError(
                "List mechanism failed internally.",
                location=self.parser.location) from exc

    def end_list_item(self):
        pass

    def finalize_list(self):
        self.current_list.finalize()
        self.current_list = None

    def begin_tag_macro(self, macro, params):
        self.print(macro.start_tag(**params), end=macro.end)

    def end_tag_macro(self, macro):
        self.print(macro.end_tag(), end=macro.end)

    def process_raw_macro(self, macro, source, params):
        self.print(macro.html(source, **params), end="")

    def process_link_macro(self, macro, params):
        self.print(macro.html(*params), end="")

class Item(object):
    def __init__(self, parent):
        self.parent = parent
        self.output = io.StringIO()
        self.compiler.writer.output = self.output

    @property
    def compiler(self):
        return self.parent.compiler

    def write_to(self, compiler):
        print(self.output.getvalue(), end="", file=compiler.writer.output)

class List(object):
    def __init__(self, parent, type):
        self.parent = parent
        self._type = type
        self.items = []

    @property
    def type(self):
        return self._type

    @type.setter
    def type(self, type):
        assert self._type is None
        self._type = type

    @property
    def compiler(self):
        return self.parent.compiler

    @property
    def level(self):
        return self.parent.level + 1

    @property
    def tag(self):
        return { "*": "ul",
                 "#": "ol", }[self._type]

    def get_list_for(self, signature):
        # Type must not change within a list. Should be cought in parser.py.
        assert signature[0] == self.type
        rest = signature[1:]
        if rest == "":
            return self
        else:
            if len(self.items) == 0 or type(self.items[-1]) == Item:
                new = List(self, rest[0])
                self.items.append(new)
                return new
            else:
                here = self.items[-1]
                return here.get_list_for(rest)

    def create_item(self):
        self.items.append(Item(self))

    def write_to(self, compiler):
        compiler.open(self.tag)

        for item, nitem in zip(self.items, self.items[1:] + [None,]):
            if isinstance(item, Item):
                compiler.open("li")
            else:
                compiler.print()

            item.write_to(compiler)

            if isinstance(nitem, Item) or nitem is None:
                compiler.close("li")

        compiler.close(self.tag)

class ListManager(object):
    def __init__(self, compiler):
        self.compiler = compiler
        self.original_output = compiler.writer.output
        compiler.writer.output = None
        self.parent = None
        self.level = -1
        self.root = None
        self.current = None
        self.type = "LM"

    @property
    def items(self):
        return [ self.root, ]

    def get_list_for(self, signature):
        if self.root is None:
            # Should be cought in parser.py
            assert len(signature) == 1

            self.root = self.current = List(self, signature[0])
            return self.root
        else:
            return self.root.get_list_for(signature)

    def begin_list_item(self, signature):
        list = self.get_list_for(signature)
        list.create_item()

    def finalize(self):
        self.compiler.writer.output = self.original_output
        self.root.write_to(self.compiler)

class CmdlineTool(CmdlineTool):
    def to_html(self, outfile, source):
        parser = WikiTextParser()
        compiler = HTMLCompiler(self.context, outfile)
        compiler.compile(parser, source)

    def make_context(self):
        return self._context_class(macro_library)

def cmdline_main(context:Context=None):
    cmdline_tool = CmdlineTool(context)
    cmdline_tool()

if __name__ == "__main__":
    cmdline_main()
