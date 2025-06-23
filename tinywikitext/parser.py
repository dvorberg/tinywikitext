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

import sys, re, dataclasses
import ply.lex

from tinymarkup.exceptions import (InternalError, ParseError, UnknownMacro,
                                   Location, UnsuitableMacro)
from tinymarkup.parser import Parser
from tinymarkup.macro import MacroLibrary
from tinymarkup.res import paragraph_break_re
from tinymarkup.utils import parse_tag_params

from .compiler import WikiTextCompiler
from . import lextokens
from .macro import TagMacro, RAWMacro, LinkMacro

wikitext_base_lexer = ply.lex.lex(module=lextokens,
                                  reflags=re.MULTILINE|re.IGNORECASE|re.DOTALL,
                                  optimize=False,
                                  lextab=None)

@dataclasses.dataclass
class ProceduralStart:
    name: str
    location: Location

defelement_is_next_re = re.compile(r"^[;:]\s*")
listitem_is_next_re = re.compile(lextokens.t_list_item.__doc__)
next_is_newline_re = re.compile(r"[ \t]*\n")

class WikiTextParser(Parser):
    """
    Base class for content parser showing the required API.

    You can also instantiate this by itself to show a trace of the
    tokens from the lexer.
    """
    def __init__(self):
        super().__init__(wikitext_base_lexer)

    # Man, this needs to be reworked.
    @property
    def current_procedural(self):
        if self.procedural_stack:
            return self.procedural_stack[-1]
        else:
            return None

    @property
    def current_procedural_name(self):
        if self.procedural_stack:
            return self.procedural_stack[-1].name
        else:
            return None


    def parse(self, source:str, compiler:WikiTextCompiler):
        compiler.begin_document(self)

        def process_macro_call(token, name, params):
            macro_class = compiler.context.macro_library.get(
                name, Location.from_lextoken(token))

            end_tag = f"</{name}>"

            start = token.lexer.lexmatch.start()
            previous_is_newline = (
                start == 0 or self.lexer.base.lexdata[start-1] == "\n")

            next_is_newline = next_is_newline_re.match(
                self.lexer.remainder) is not None

            rest_of_line = self.lexer.remainder.split("\n", 1)[0]
            endtag_on_line = rest_of_line.endswith(end_tag)

            if previous_is_newline and (next_is_newline or endtag_on_line):
                # The macro sits alone on its line.
                environment = "block"
            else:
                # The macro does not sit alone on its line.
                environment = "inline"

            try:
                macro_class.check_environment(environment)
            except UnsuitableMacro as exc:
                if environment == "block":
                    # Maybe the macro likes to be part of a paragraph?
                    ensure_paragraph()
                    environment = "inline"
                    macro_class.check_environment(environment)
                else:
                    exc.location = Location.from_lextoken(token)
                    raise

            if (token.type == "linkmacro"
                and not issubclass(macro_class, LinkMacro)):
                raise UnsuitableMacro(f"Macros used with the link syntax must "
                                      f"inherit from LinkMacro "
                                      f"(“{name}” does not.)",
                                      location = Location.from_lextoken(token))

            macro = macro_class(compiler.context, environment)

            if isinstance(macro, TagMacro):
                self.tag_macro_stack.append( (macro, token.lexpos,) )
                compiler.begin_tag_macro(macro, params)

            elif isinstance(macro, RAWMacro):
                # We have to go looking for the end of it,
                # extract the source in between,
                # move the laxpos and tell the compiler to
                # call it.
                try:
                    pos = self.lexer.remainder.index(end_tag)
                except ValueError:
                    raise ParseError(
                        f"Unterminated <{name}> macro",
                        location=Location.from_lextoken(token))

                source = self.lexer.remainder[:pos]
                self.lexer.lexpos += pos + len(end_tag)

                compiler.process_raw_macro(macro, source, params)

            elif isinstance(macro, LinkMacro):
                compiler.process_link_macro(macro, params)


        self.procedural_stack = []
        def begin_procedural(name):
            #if self.current_procedural is not None:
            #    oldname, oldlocation = self.current_procedural
            #    raise ParseError(f"Procedural markup may not nest, "
            #                     f"starting {name} while in "
            #                     f"{oldname} starting about here:",
            #                     location=oldlocation)
            #else:
            #   self.current_procedural = name, self.location
            self.procedural_stack.append(ProceduralStart(
                name, self.location))

        def end_procedural(name):
            #p, oldlocation = self.current_procedural
            #if p != name:
            #    raise ParseError(f"Can’t terminate {p} with {name}.",
            #                     location=oldlocation)
            #self.current_procedural = None
            entry = self.procedural_stack.pop()
            if entry.name != name:
                raise ParseError(f"Procedural markup mismatch."
                                 f"Can’t terminate {p} with {name}.",
                                 location=entry.location)

        self.current_heading_level = None

        self.previous_list_item = None
        self.current_list_item = None

        self.tag_macro_stack = []

        self.in_definition = None

        self.in_paragraph = False
        def paragraph_break():
            if self.current_procedural is not None:
                p = self.current_procedural
                raise ParseError(f"Unterminated {p.name}, "
                                 f"missing end about here:",
                                 p.location)

            if self.current_heading_level is not None:
                level, location = self.current_heading_level
                raise ParseError(f"Unterminated heading."
                                 f"missing end about here:",
                                 location=Location.from_lextoken(token))

            if self.in_paragraph:
                compiler.end_paragraph()
                self.in_paragraph = False

        def ensure_paragraph():
            if self.in_definition == "list":
                raise InternalError("Can’t put contents in a definition list.",
                                    location=self.lexer.location)

            if not self.in_paragraph \
                     and self.current_list_item is None \
                     and self.current_heading_level is None \
                     and not self.in_definition in { "term", "def", }:
                compiler.begin_paragraph()
                self.in_paragraph = True

        for token in self.lexer.tokenize(source):
            match token.type:
                case "bolditalic":
                    ensure_paragraph()

                    if self.current_procedural_name != "bolditalic":
                        begin_procedural("bolditalic")
                        compiler.begin_bold()
                        compiler.begin_italic()
                    else:
                        end_procedural("bolditalic")
                        compiler.end_italic()
                        compiler.end_bold()

                case "bold":
                    ensure_paragraph()

                    if self.current_procedural_name != "bold":
                        begin_procedural("bold")
                        compiler.begin_bold()
                    else:
                        end_procedural("bold")
                        compiler.end_bold()

                case "italic":
                    ensure_paragraph()

                    if self.current_procedural_name != "italic":
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
                        compiler.other_characters(" ")

                case "br":
                    compiler.line_break()

                case "link":
                    ensure_paragraph()
                    text, target = token.value
                    compiler.link(text, target or None)

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
                        raise ParseError(
                            "List nesting error. You may only increase the "
                            "nesting level by one per line.",
                            location=Location.from_lextoken(token))

                    compiler.begin_list_item(signature)

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

                case "definition_term":
                    if self.in_definition is None:
                        compiler.begin_definition_list()
                        # self.in_definition = "list"

                    compiler.begin_definition_term()
                    self.in_definition = "term"

                case "definition_def":
                    if self.in_definition is None:
                        raise ParseError(
                            "A definition must always follow a term.",
                            location=Location.from_lextoken(token))

                    # The definition_term is terminated by a newline
                    # compiler.end_definition_term() is called when
                    # handling a single eol below.
                    compiler.begin_definition_def()
                    self.in_definition = "def"

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
                    if self.current_heading_level is None:
                        raise ParseError(
                            "Attempt to close a heading that has not been"
                            "opened", location=Location.from_lextoken(token))

                    level = len(token.value)
                    oldlevel, oldlocation = self.current_heading_level
                    if oldlevel != level:
                        raise ParseError("Heading level mismatch",
                                         location=oldlocation)

                    compiler.end_heading(level)
                    self.current_heading_level = None

                case "htmltag_start":
                    name, params = token.value
                    # Parse those params!
                    params = parse_tag_params(params)

                    process_macro_call(token, name, params)

                case "htmltag_end":
                    tag = token.value
                    if len(self.tag_macro_stack) == 0:
                        raise ParseError(f"Cannot close macro “{tag}”; "
                                         f"not opened.",
                                         location=Location.from_lextoken(token))
                    lastopen, lexpos = self.tag_macro_stack.pop()

                    if lastopen.name != tag:
                        raise ParseError(f"Macro nesting error, trying to "
                                         f"close <{lastopen.name}> "
                                         f"with </{tag}>.",
                                         location=Location.from_lextoken(token))

                    if lastopen.environment == "block":
                        paragraph_break()

                    compiler.end_tag_macro(lastopen)

                case "linkmacro":
                    name, params = token.value

                    macro_class = compiler.context.macro_library.get(
                        name, Location.from_lextoken(token))

                    if params:
                        params = params.split("|")
                    else:
                        params = []

                    process_macro_call(token, name, params)

                case "whitespace":
                    compiler.other_characters(" ")

                case "eols":
                    nlcount = token.value.count("\n")

                    if self.in_definition == "term":
                        compiler.end_definition_term()
                        self.in_definition = "list"

                    elif self.in_definition == "def":
                        compiler.end_definition_def()

                        # Perform a look-ahead: if there is a new term
                        # comming up, do not close the definition list.
                        remainder = self.lexer.remainder
                        if defelement_is_next_re.match(remainder) is None:
                            compiler.end_definition_list()
                            self.in_definition = None
                        else:
                            self.in_definition = "list"

                    elif self.current_list_item is not None:
                        compiler.end_list_item()

                        # Perform a look-ahead: if there is a new term
                        # comming up, do not close the definition list.
                        remainder = self.lexer.remainder
                        if listitem_is_next_re.match(remainder) is None \
                              or nlcount > 1:
                            compiler.finalize_list()
                            self.previous_list_item = None
                            self.current_list_item = None
                        else:
                            self.previous_list_item = self.current_list_item
                            self.current_list_item = None

                    elif nlcount == 1:
                        # Single newlines are still whitespace.
                        compiler.other_characters(" ")
                    else:
                        # Double newline.
                        paragraph_break()

                case "word":
                    ensure_paragraph()
                    compiler.word(token.value)

                case "other_characters":
                    ensure_paragraph()
                    compiler.other_characters(token.value)


        # Make sure the last paragraph is closed in case
        # there is no whitespace at the end of the file.
        paragraph_break()

        if len(self.tag_macro_stack) > 0:
            lastopen, lexpos = self.tag_macro_stack[-1]
            raise ParseError(f"Macro {lastopen.name} not closed. Started at:",
                             location=Location.from_lexdatapos(
                                 self.lexer.base.lexdata, lexpos))

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
