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

from tinymarkup.context import Context
from tinymarkup.compiler import Compiler
from tinymarkup.macro import Macro, MacroLibrary

class WikiTextCompiler(Compiler):
    def characters(self, s:str):
        print("characters", repr(s))

    def line_break(self):
        print("line_break")

    def begin_paragraph(self):
        print("begin_paragraph")

    def end_paragraph(self):
        print("end_paragraph")

    def begin_italic(self):
        print("begin_italc")

    def end_italic(self):
        print("end_italic")

    def begin_bold(self):
        print("begin_bold")

    def end_bold(self):
        print("end_bold")

    def link(self, text, target):
        print("link", repr(text), repr(target))

    def call_macro(self, name, params):
        print("call_macro", repr(name), repr(params))

    def horizontal_line(self):
        print("horizontal_line")

    def begin_heading(self, level:int):
        print(f"begin_heading level={level}")

    def end_heading(self, level:int):
        print(f"end_heading level={level}")

    def begin_list_item(self, signature):
        print("begin_list_item", repr(signature))

    def end_list_item(self):
        print("end_list_item")

    def finalize_list(self):
        print("finalize_list")

    def begin_definition_list(self):
        print("begin_definition_list")

    def end_definition_list(self):
        print("end_definition_list")

    def begin_definition_term(self):
        print("begin_definition_term")

    def end_definition_term(self):
        print("finalize_list")

    def begin_definition_def(self):
        print("end_definition_term")

    def end_definition_def(self):
        print("end_definition_def")

    def begin_tag_macro(self, macro, params):
        print("begin_tag_macro", repr(macro), repr(params))

    def end_tag_macro(self, macro):
        print("end_tag_macro", repr(macro))

    def process_raw_macro(self, macro, source, params):
        print("process_raw_macro")
        print(source)
        print("-"*60)
