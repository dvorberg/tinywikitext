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

import re
import ply.lex

from tinymarkup.exceptions import (InternalError, ParseError, UnknownMacro,
                                   Location)
from tinymarkup.parser import Parser
from tinymarkup.macro import MacroLibrary
from tinymarkup.res import paragraph_break_re
from tinymarkup.utils import parse_tag_params

from .compiler import WikiTextCompiler
from . import lextokens
from .macro import TagMacro, RAWMacro

wikitext_base_lexer = ply.lex.lex(module=lextokens,
                                  reflags=re.MULTILINE|re.IGNORECASE|re.DOTALL,
                                  optimize=False,
                                  lextab=None)

class WikiTextParser(Parser):
    """
    Base class for content parser showing the required API.

    You can also instantiate this by itself to show a trace of the
    tokens from the lexer.
    """
    def __init__(self):
        super().__init__(wikitext_base_lexer)

    def parse(self, source:str, compiler:WikiTextCompiler):
        compiler.begin_document(self)

        self.current_procedural = None
        def begin_procedural(name):
            if self.current_procedural is not None:
                oldname, oldlocation = self.current_procedural
                raise ParseError(f"Procedural markup may not nest, "
                                 f"starting {name} while in "
                                 f"{oldname} starting about here:",
                                 location=oldlocation)
            else:
               self.current_procedural = name, self.location

        def end_procedural(name):
            p, oldlocation = self.current_procedural
            if p != name:
                raise ParseError(f"Can’t terminate {p} with {name}.",
                                 location=oldlocation)
            self.current_procedural = None


        self.current_heading_level = None
        self.previous_list_item = None
        self.current_list_item = None
        self.tag_macro_stack = []

        self.in_paragraph = False
        def paragraph_break():
            if self.current_procedural is not None:
                name, location = self.current_procedural
                raise ParseError(f"Unterminated {name}, "
                                 f"missing end about here:",
                                 location)

            if self.current_heading_level is not None:
                level, location = self.current_heading_level
                raise ParseError(f"Unterminated heading."
                                 f"missing end about here:",
                                 location)

            if self.in_paragraph:
                compiler.end_paragraph()
                self.in_paragraph = False

        def ensure_paragraph():
            if not self.in_paragraph \
                     and self.current_list_item is None \
                     and self.current_heading_level is None:
                compiler.begin_paragraph()
                self.in_paragraph = True

        for token in self.lexer.tokenize(source):
            match token.type:
                case "bolditalic":
                    ensure_paragraph()

                    if self.current_procedural is None:
                        begin_procedural("bolditalic")
                        compiler.begin_bold()
                        compiler.begin_italic()
                    else:
                        end_procedural("bolditalic")
                        compiler.end_italic()
                        compiler.end_bold()

                case "bold":
                    ensure_paragraph()

                    if self.current_procedural is None:
                        begin_procedural("bold")
                        compiler.begin_bold()
                    else:
                        end_procedural("bold")
                        compiler.end_bold()

                case "italic":
                    ensure_paragraph()

                    if self.current_procedural is None:
                        begin_procedural("italic")
                        compiler.begin_italic()
                    else:
                        end_procedural("italic")
                        compiler.end_italic()

                case "comment":
                    start_ws, end_ws = token.value

                    # Get the whitespace sourrounding the comment.
                    # If the whitespace before or after the comment
                    # amounts to a paragraph break, do it.
                    match = paragraph_break_re.match(start_ws)
                    if match is None:
                        match = paragraph_break_re.match(end_ws)

                    if match is not None:
                        paragraph_break()
                    elif start_ws or end_ws:
                        # If there is whitespace around the comment,
                        # it is rendered as a single space.
                        compiler.characters(" ")

                case "br":
                    compiler.line_break()

                case "link":
                    text, target = token.value
                    compiler.link(text, target or None)

                case "eols":
                    if token.value.count("\n") > 1:
                        if self.current_list_item is None:
                            paragraph_break()
                        else:
                            compiler.end_list_item()
                            compiler.finalize_list()
                            self.previous_list_item = None
                            self.current_list_item = None
                    else:
                        if self.current_list_item is not None:
                            compiler.end_list_item()
                            self.previous_list_item = self.current_list_item
                            self.current_list_item = None
                        else:
                            # Single newlines are still whitespace.
                            compiler.characters(" ")

                case "hr":
                    compiler.horizontal_line()

                case "list_item":
                    signature = token.value
                    paragraph_break()

                    if self.previous_list_item is None:
                        oldlevel = 0
                    else:
                        oldlevel = len(self.previous_list_item)

                    if len(signature) > oldlevel + 1:
                        raise SyntaxError(
                            "List nesting error. You may only increase the "
                            "nesting level by one per line.",
                            location=Location.from_lextoken(token))

                    compiler.begin_list_item(signature)

                    # import pdb ; pdb.set_trace()

                    if self.previous_list_item is not None:
                        # List item signature must match according
                        # to the shorter of the two. You cannot, for example,
                        # change list type mid-list as in:
                        #
                        # *
                        # **
                        # *#
                        # *
                        l = min(len(self.previous_list_item), len(signature))
                        if self.previous_list_item[:l] != signature[:l]:
                            raise ParseError(
                                "You cannot change list type mid list.",
                                location=Location.from_lextoken(token))

                    self.current_list_item = signature

                case "heading_start":
                    paragraph_break()

                    if self.current_heading_level is not None:
                        level, oldlocation = self.current_heading_level
                        raise ParseError("Can’t nest headings.",
                                         location=oldlocation)
                    else:
                        level = len(token.value)
                        compiler.begin_heading(level)
                        self.current_heading_level = level, self.location

                case "heading_end":
                    level = len(token.value)
                    oldlevel, oldlocation = self.current_heading_level
                    if oldlevel != level:
                        raise ParseError("Heading level mismatch",
                                         location=oldlocation)
                    else:
                        compiler.end_heading(level)
                        self.current_heading_level = None

                case "htmltag_start":
                    name, params = token.value
                    # Parse those params!

                    params = parse_tag_params(params)

                    macro_class = compiler.context.macro_library.get(
                        name, Location.from_lextoken(token))

                    if macro_class.context == "block" and self.in_paragraph:
                        raise UnsuitableMacro(
                            f"{name} must be used as block-level macro "
                            f"(it’s its own paragraph).",
                            location=Location.from_lextoken(token))

                    if macro_class.context == "inline":
                        ensure_paragraph()

                    macro = macro_class(compiler.context)

                    if issubclass(macro_class, TagMacro):
                        self.tag_macro_stack.append(macro)
                        compiler.begin_tag_macro(macro, params)
                    elif issubclass(macro_class, RAWMacro):
                        # We have to go looking for the end of it,
                        # extract the source in between,
                        # move the laxpos and tell the compiler to
                        # call it.
                        end_tag = f"</{name}>"
                        try:
                            pos = self.lexer.remainder.index(end_tag)
                        except ValueError:
                            raise ParseError(
                                f"Unterminated <{name}> macro",
                                location=Location.from_lextoken(token))

                        source = self.lexer.remainder[:pos]
                        self.lexer.lexpos += pos + len(end_tag)

                        compiler.process_raw_macro(macro, source, params)

                case "htmltag_end":
                    tag = token.value
                    lastopen = self.tag_macro_stack.pop()

                    if lastopen.name != tag:
                        raise ParseError(f"Macro nesting error, trying to "
                                         f"close <{lastopen.name}> "
                                         f"with </{tag}>.",
                                         location=Location.from_lextoken(token))

                    if lastopen.__class__.context == "block":
                        paragraph_break()

                    compiler.end_tag_macro(lastopen)

                case "macro":
                    self.process_macro_call(token)

                case "whitespace":
                    compiler.characters(" ")

                case "word" | "text":
                    ensure_paragraph()
                    compiler.characters(token.value)

        # Make sure the last paragraph is closed in case
        # there is no whitespace at the end of the file.
        paragraph_break()

        compiler.end_document()

if __name__ == "__main__":
    import argparse, pathlib, time

    from tinymarkup.context import Context

    from .compiler import WikiTextCompiler
    from .macro import macro_library, RAWMacro

    # example inline RAW macro
    class cite(RAWMacro):
        context = "inline"

        def html(self, source, **params):
            return "".join(['<code>',
                            f'source = {repr(source)}',
                            f'params = {repr(params)}',
                            '</code>'])

    macro_library.register(cite)

    ap = argparse.ArgumentParser()
    ap.add_argument("infilepath", type=pathlib.Path)
    args = ap.parse_args()

    with args.infilepath.open() as fp:
        wikitext = fp.read()

        parser = WikiTextParser()
        compiler = WikiTextCompiler(Context(macro_library))
        parser.parse(wikitext, compiler)
