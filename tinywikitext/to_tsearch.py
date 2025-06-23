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

from tinymarkup.writer import TSearchWriter
from tinymarkup.context import Context

from .parser import WikiTextParser
from .compiler import WikiTextCompiler
from .to_html import CmdlineTool

class TSearchCompiler(WikiTextCompiler):
    def __init__(self, context, output):
        WikiTextCompiler.__init__(self, context)
        self.writer = TSearchWriter(output, self.context.root_language)

    def word(self, s:str):
        self.writer.word(s)

    def other_characters(self, s:str):
        pass

    def end_document(self):
        self.writer.end_document()

    def line_break(self): pass
    def begin_paragraph(self): pass
    def end_paragraph(self): self.writer.tsvector_break()
    def begin_italic(self): pass
    def end_italic(self): pass
    def begin_bold(self): pass
    def end_bold(self): pass
    def begin_list_item(self, signature): pass
    def end_list_item(self): pass
    def finalize_list(self): pass
    def begin_definition_list(self): pass
    def end_definition_list(self): pass
    def begin_definition_term(self): pass
    def end_definition_term(self): pass
    def begin_definition_def(self): pass
    def end_definition_def(self): pass
    def horizontal_line(self): pass

    def link(self, text, target):
        self.writer.word(text)

    def begin_heading(self, level:int):
        if level < 3:
            self.writer.push_weight("B")
        else:
            self.writer.push_weight("C")

    def end_heading(self, level:int):
        self.writer.pop_weight()

    def begin_tag_macro(self, macro, params):
        macro.start_searchable_text_block(self.writer, **params)

    def end_tag_macro(self, macro):
        macro.end_searchable_text_block(self.writer)

    def process_raw_macro(self, macro, source, params):
        macro.add_searchable_text(self.writer, **params)

    def process_link_macro(self, macro, params):
        macro.add_searchable_text(self.writer, *params)


class CmdlineTool(CmdlineTool):
    def to_tsearch(self, outfile, source):
        parser = WikiTextParser()
        compiler = TSearchCompiler(self.context, outfile)
        compiler.compile(parser, source)

    to_html = to_tsearch
    def begin_html(self): pass
    def end_html(self): pass

def cmdline_main(context:Context=None):
    cmdline_tool = CmdlineTool(context)
    cmdline_tool()

if __name__ == "__main__":
    print("SELECT ")
    cmdline_main()
