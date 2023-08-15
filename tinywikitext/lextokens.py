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


#
# Spec: https://www.mediawiki.org/wiki/Markup_spec
#

# Supported Markup:

# -> Anywhere
# • Procedural markup:
#   '''''bold italic'''''
#   '''bold'''
#   ''italic''
# • HTML style commends
#   <!-- ... -->
# • <br> and <br/> and <br />
# • [[Link]] and [[Linked text|Target]]

#   Also:

#     [[macro:filename.jpg|param2|param3|param4]]

#   WikiText knows about “Namespaces”. This library reads these as
#   macro calls, macros returning HTML.

# -> At the beginning of a line:
# • blank line: paragraph break
# • ---- (four or more hyphens): Horizontal line
# • Lists
#   * Bullet list
#   # Numbered list
# • Headings
#   = h1 =
#   == h2 ==
#   and so on, up to level 6.
# • <blockquote>
#   ...
#   </blockquote>

# Table formatting is ignored at this point in time.
# Neither are “magic words“, magic links, or templates.


from tinymarkup.exceptions import Location, LexerSetupError

tokens = (
    "bolditalic",
    "bold",
    "italic",
    "comment",
    "br",
    "link",
    "macro",

    "eols",

    "hr",
    "list_item",

    "heading_start",
    "heading_end",

    "htmltag_start",
    "htmltag_end",

    "whitespace",
    "word",
    "text"
)

def group(token, *group_names):
    groupdict = token.lexer.lexmatch.groupdict()

    if len(group_names) == 1:
        return groupdict[group_names[0]]
    else:
        return [groupdict[name] for name in group_names]

groups = group

t_bolditalic = r"'''''"
t_bold =  r"'''"
t_italic =  r"''"

def t_comment(t):
    r"(?P<cmt_start_ws>\s*)<!--.*?-->(?P<cmd_end_ws>\s*)"
    t.value = groups(t, "cmt_start_ws", "cmd_end_ws")
    return t

t_br =  r"<br\s*/?>"

def t_link(t):
    r"\[\[(?P<link_text>.+?)(?:\|(?P<link_target>.+?))?\]\]"
    t.value = groups(t, "link_text", "link_target")
    return t

def t_macro(t):
    r"\[\[(?P<macro_name>[^\d\W]\w+):(?P<macro_params>.*)\]\]"
    t.value = groups(t, "macro_name", "macro_params")
    return t

def t_eols(t):
    r"\n([\t ]*[\n])*"
    t.value = "\n" * t.value.count("\n")
    return t

t_hr =  r"^----+"

def t_list_item(t):
    r"^(?P<listitem_intro>[\*#]+)\s*"
    # (?=\w) makes sure a word follows (look ahead)
    t.value = group(t, "listitem_intro")
    return t

def t_heading_start(t):
    r"^(?P<heading_start>={1,6})[ \t]*"
    t.value = group(t, "heading_start")
    return t

def t_heading_end(t):
    r"[ \t]*(?P<heading_end>={1,6})[^\n\S]*$"
    t.value = group(t, "heading_end")
    return t

def t_htmltag_start(t):
    ( r"<(?P<html_start_tag>[a-z]+)"
     r"(?<!br)" # negative lookbehind assertion for "br"
     r"(?:\s+(?P<html_start_params>[^>]*))?>" )
    t.value = group(t, "html_start_tag", "html_start_params")
    return t

def t_htmltag_end(t):
    r"</(?P<html_end_tag>[a-z]+)>"
    t.value = group(t, "html_end_tag")
    return t

t_whitespace = r"[ \t]+"
t_word = r"\w[\w \t]*\w"
t_text = r"."

def t_error(t):
    raise LexerSetupError(repr(t), location=Location.from_baselexer(t.lexer))
