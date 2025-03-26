#!/usr/bin/env python
# -*- coding: UTF-8 -*-

# Authors:     Marek Schmidt 2007, David Smejkal 2008
# Repository:  https://github.com/david-smejkal/wiki2txt
# License:     GPLv2

# standard libraries
import sys
import os
from io import BytesIO

# import re
import optparse
import locale
import unicodedata

# non-standard libraries
import lxml.etree  # pip install lxml
import regex as re

# local imports
from languages import LANGUAGES_SET

# using regex instead of re in order to access regex timeout to deal with runaway regex during catastrophic backtracking
# this happens rarely, when parsing a badly formatted page, often a corrupted page that wouldn't even load in a browser

# XML OUTPUT FORMAT
# <article>
#   <id>12</id>
#   <title>Anarchism</title>
#   <text>Anarchism is a political philosophy ...</text>
# </article>

REGEX_TIMEOUT = 30  # seconds

DEFAULT_ENCODING = "utf-8"

# TODO list:
#   TODO: Break up classes into individual files
#   DONE: Implement a set of basic functional tests
#   DONE: Fix STDIN processing to actually allow piping of input and separate it from the -T option
#   TODO: Cover as much code as possible with unit tests
#   TODO: Optimize code where appropriate to speed up processing / parsing
#   TODO: Imlement a better way to handle runnaway regex than REGEX_TIMEOUT (then switch back to standard re library)
#   TODO: Redesign REGEX parsing so that it would be able to utilize more CPU cores (use multithreading library)
#   TODO: Drop Python v2 support
#   TODO: Review the necessity for unicodedata normalization (it seems unnecessary to normalize unicode strings in v3)
#   TODO: Think about allowing wikimedia syntax one-shot parsing (wrap STDIN input in a mediawiki like structure?)


################################################################################
# --------------------------------<CLASSES>----------------------------------- #
################################################################################

# List of classes used in this script:
# class WikiData             - Holds parsed data
# class Conductor            - Performs script related operations (option parsing, printing progress, etc.)
# class Processor(Conductor) - Performs parsing related operations (core of wiki2txt)


class WikiData:
    """Data structure designed to hold parsed data."""

    def __init__(self):
        self.plain_text = None
        self.redirect = None
        self.links = []
        self.categories = []


class Conductor:
    """Helper / handler / orchestrator of this script. Performs script related operations (option parsing, printing progress, etc.)."""

    def get_options(self):
        """This function is self-explained."""
        opt_parser = optparse.OptionParser(
            usage="usage: %prog [options]", version="%prog 0.6.0"
        )

        opt_parser.add_option(
            "-i",
            "--input-file",
            dest="input",
            metavar="FILE",
            help="take xml input from FILE otherwise from STDIN",
        )
        opt_parser.add_option(
            "-o",
            "--output-file",
            dest="output",
            metavar="FILE",
            help="output parsed articles to FILE otherwise to STDOUT",
        )
        opt_parser.add_option(
            "-n",
            "--no-text",
            action="store_false",
            dest="text",
            default=False,
            help="don't parse text (designed for use with -r -l -c options)",
        )
        opt_parser.add_option(
            "-t",
            "--text",
            action="store_true",
            dest="text",
            default=True,
            help="produce plain (unformatted) text (DEFAULT)",
        )
        opt_parser.add_option(
            "-s",
            "--skip",
            dest="skip",
            metavar="NUMBER",
            help="skip (resume after) NUMBER of articles (and append to -o FILE)",
        )
        opt_parser.add_option(
            "-q",
            "--quiet",
            action="store_false",
            dest="verbose",
            default=True,
            help="stop making noise",
        )
        opt_parser.add_option(
            "-R",
            "--references",
            action="store_true",
            dest="references",
            default=False,
            help="retain references in text (links and categories)",
        )
        opt_parser.add_option(
            "-r",
            "--redirects",
            dest="redirects_file",
            metavar="FILE",
            help="outsource redirect articles to the FILE",
        )
        opt_parser.add_option(
            "-l",
            "--links",
            dest="links_file",
            metavar="FILE",
            help="capture articles' links in the FILE",
        )
        opt_parser.add_option(
            "-c",
            "--categories",
            dest="categories_file",
            metavar="FILE",
            help="capture articles' categories in the FILE",
        )
        opt_parser.add_option(
            "-T",
            "--test",
            action="store_true",
            dest="test",
            default=False,
            help="test by parsing directly from STDIN (bypasses lxml parser)",
        )
        (options, args) = opt_parser.parse_args()

        self.arg_text = options.text

        self.arg_skip = False
        try:
            if options.skip != None:
                self.arg_skip = int(options.skip)
        except:
            sys.stderr.write("\nWARNING: Skip argument not integer (not skipping).\n")
            self.arg_skip = False

        self.arg_verbose = options.verbose
        if self.arg_verbose:
            locale.setlocale(locale.LC_ALL, "C")

        self.arg_references = options.references

        if options.input != None:
            self.arg_input_name = options.input
            self.arg_input = open(options.input, "rb")
        else:
            self.arg_skip = False
            self.arg_input_name = "stdin"
            self.arg_input = sys.stdin

        if options.output != None:
            if self.arg_text:
                self.arg_output_name = options.output
                if self.arg_skip:
                    self.arg_output = open(options.output, "a+b")
                else:
                    self.arg_output = open(options.output, "wb")
            else:
                self.arg_output_name = None
                self.arg_output = None
        else:
            if self.arg_text:
                self.arg_skip = False
                self.arg_output_name = "stdout"
                self.arg_output = sys.stdout
            else:
                self.arg_output_name = None
                self.arg_output = None

        self.arg_redirects_file = options.redirects_file

        self.arg_links_file = options.links_file

        self.arg_categories_file = options.categories_file

        self.arg_test = options.test
        if self.arg_test:
            self.arg_text = True

    def get_file_size(self, file):
        """Self explained."""
        self.arg_input.seek(0, os.SEEK_END)
        size = self.arg_input.tell()
        self.arg_input.seek(0, os.SEEK_SET)
        return size

    def print_progress(self, file_size, size, previous_progress):
        """Prints progress to stdout."""
        progress_percentage = "%.2f" % (float(size) / file_size * 100)

        if previous_progress[0] != progress_percentage:

            output = "%s MB  of  %s MB" % (
                locale.format_string("%0.2f", (float(size) / 1000000), True),
                locale.format_string("%d", (file_size / 1000000), True),
            )
            output += " (" + progress_percentage + " %)"

            for i in range(previous_progress[1]):
                sys.stdout.write("\b")
            sys.stdout.write(output)
            sys.stdout.flush()

            return progress_percentage, len(output)

        return progress_percentage, previous_progress[1]


class Processor(Conductor):
    """Core class. Performs parsing and processing related operations."""

    def __init__(self):
        self.repeat = 1  # flag needed for nested elements
        self.wiki_data = WikiData()
        # REGULAR EXPRESSIONS PATTERNS FOR PARSING
        self.wikiRedRE = re.compile(r"(?i)#redirect\s*\[\[(.*?)\]\].*", re.DOTALL)
        self.wikiLanRE = re.compile(r"(.*\[\[Category:.*?\]\]).*", re.DOTALL)
        # self.wikiQuoRE = re.compile(r"\{\{cquote\|.*?\}\}", re.DOTALL)
        self.wikiCurRE = re.compile(r"\{\{.*?\}\}", re.DOTALL)
        # self.wikiClaRE = re.compile(r"\{\{lang\|([^{]*?(?:!\{\{)*?)\}\}", re.DOTALL)
        self.wikiTabRE = re.compile(r"\{\|.*?\|\}", re.DOTALL)
        self.wikiBrtRE = re.compile(
            r"(?:<|(?:&lt;))/?(?:(?:br)|(?:BR)).*?/?\s*(?:>|(?:&gt;))", re.DOTALL
        )
        self.wikiBlqRE = re.compile(
            r"(?:<|(?:&lt;))blockquote(?:>|(?:&gt;))(.*?)(?:<|(?:&lt;))/blockquote(?:>|(?:&gt;))",
            re.DOTALL,
        )
        self.wikiComRE = re.compile(r"(?:<|(?:&lt;))!--.*?--(?:>|(?:&gt;))", re.DOTALL)
        self.wikiTttRE = re.compile(
            r"(?:<|(?:&lt;))(?:[tT]{2})(?:>|(?:&gt;))(.*?)(?:<|(?:&lt;))/(?:[tT]{2})(?:>|(?:&gt;))",
            re.DOTALL,
        )
        # r"(?:<|(?:&lt;))[^/]*?(?!&gt;)/(?:>|(?:&gt;))"
        # <abc asdaaa="aa" />
        self.wikiCtaRE = re.compile(r"(?:<|(?:&lt;))(.*?)/(?:>|(?:&gt;))", re.DOTALL)
        self.wikiOtaRE = re.compile(
            r"(?i)((?:<|(?:&lt;))\s*(?P<tagname>\w+)(?:[^/]*?)(?:>|(?:&gt;)))(.*?)(?:<|(?:&lt;))\s*/\s*(?P=tagname)\s*(?:>|(?:&gt;))",
            re.DOTALL,
        )
        self.wikiStaRE = re.compile(
            r"(?i)(?:<|(?:&lt;))\s*/?\s*(?:div|center|p|small|b|sub|s|blockquote|font|ref|i|gallery|del|sicsic|sup|div\s.*?|noinclude|table|tr|tr\s.*?|li|hr|td|math)\s*/?\s*(?:>|(?:&gt;))",
            re.DOTALL,
        )
        self.wikiSMaRE = re.compile(r"&[a-z]+;")
        self.wikiSChRE = re.compile(
            r"(?!:(?:<|(?:&lt;))(?:(?:tt)|(?:TT))(?:>|(?:&gt;)))&amp;#[0-9]+;(?!:(?:<|(?:&lt;))/(?:(?:tt)|(?:TT))(?:>|(?:&gt;)))",
            re.DOTALL,
        )
        self.wikiRefRE = re.compile(
            r"(?i)\[\[(?!category:)[\s_]*:?[\s_]*([^[]*?(?:!\[\[)*?)\]\]", re.DOTALL
        )
        # self.repaRefRE = re.compile(r"(?i)(^:category:\s*)(.)(.*)", re.DOTALL)
        # remove trailing spaces (used to repair title)
        self.repaTraRE = re.compile(r"^[\s_:]+")
        # repair spaces with "_" (used to repair categories, links and titles)
        self.repaBlaRE = re.compile(r"[\s_]+")
        self.wikiCatRE = re.compile(
            r"(?i)\[\[(category:[^[]*?(?:!\[\[)*?)\]\]", re.DOTALL
        )
        self.repaCatRE = re.compile(r"(?i)(^:?category:[\s_]*)(.)(.*)")
        self.wikiImgRE = re.compile(r"\[\[:?(Image|File):.*?\]\]", re.DOTALL)
        # [[(http | https | ftp) :// ...] ...] or [(http | https | ftp) :// ...]
        self.wikiHttRE = re.compile(
            r"(?:(?:\[\[(?:(?:http[s]?)|(?:ftp))://.*?\].*?\])|(?:\[(?:(?:http[s]?)|(?:ftp))://.*?\]))",
            re.DOTALL,
        )
        self.wikiBolRE = re.compile(r"'''.*?'''", re.DOTALL)
        self.wikiItaRE = re.compile(r"''.*?''", re.DOTALL)
        self.wikiIteRE = re.compile(r"\n[*#(?:;)(?:#)]+[\ ]*")
        self.wikiEolRE = re.compile(r"(?:\n){2,}")
        self.wikiWhiRE = re.compile(
            r"(?:\s){2,}", flags=re.M
        )  # detects clusters of 2 or more white spaces
        self.wikiBraRE = re.compile(r"\(\)")
        self.wikiHeaRE = re.compile(r"[=]{2,4}.*?[=]{2,4}")

    def parse_language_references(self, match_obj):
        """Cuts language references from text."""
        return match_obj.group(1)

    def parse_special_char(self, match_obj):
        """Returns html-ascii-decimal-character's unicode representation."""
        # print "MATCH", match_obj.group(0)
        try:
            ret = unichr(int(match_obj.group(0)[2:-1]))
        except:
            return ""
        return ret

    def parse_special_mark(self, match_obj):
        """Returns '<', '>', '&' or '"'."""
        if match_obj.group(0) == "&lt;":
            return "<"
        elif match_obj.group(0) == "&gt;":
            return ">"
        elif match_obj.group(0) == "&amp;":
            return "&"
        elif match_obj.group(0) == "&quot;":
            return '"'

    def parse_table(self, match_obj):
        """Parsing table.. if tables are nested get rid of most nested and repeat."""
        index = match_obj.group(0)[2:].rfind("{|")
        if index == -1:
            return ""
        else:
            self.repeat = 1
            return match_obj.group(0)[: index + 2]

    def parse_quotation(self, match_obj):
        """Returns unformated quotation."""
        # index = match_obj.group(0).rfind("cquote|")
        # if index == -1:
        #   return ""
        # else:
        return match_obj.group(0)[9:-2]

    def parse_curly_lang(self, match_obj):
        """Returns unformated text."""
        index = match_obj.group(1).rfind("|")
        return match_obj.group(1)[index + 1 :]

    def parse_curly(self, match_obj):
        """Parse a curly bracket. If nested get rid of the most nested one and repeat."""
        deepest_index = match_obj.group(0).rfind(
            "{{"
        )  # start index of last nested element
        if deepest_index != -1:
            self.repeat = 1  # nested element found, setting repeat flag
        else:
            deepest_index = 0  # no nested elements

        # parsing double curly brackets differs acording to text before separator
        # {{lang|de|Ostereich}} is different from {{cquote|Kant is monster...}}
        separator_index = match_obj.group(0)[deepest_index:].find("|")
        if separator_index != -1:
            separator_index += +deepest_index
        else:
            # print "regular"
            # {{ ... }} (no "|" separator)
            return match_obj.group(0)[:deepest_index]

        if match_obj.group(0)[deepest_index + 2 : separator_index] == "cquote":
            # print "cquote|"
            # {{cquote|Kant is monster...}}
            return (
                match_obj.group(0)[:deepest_index]
                + match_obj.group(0)[separator_index + 1 : -2]
            )
        elif match_obj.group(0)[deepest_index + 2 : separator_index] == "lang":
            # print "lang|"
            # {{lang|de|Ostereich}}
            lang_separator_index = match_obj.group(0)[separator_index + 1 : -2].rfind(
                "|"
            )
            if lang_separator_index != -1:
                return (
                    match_obj.group(0)[:deepest_index]
                    + match_obj.group(0)[
                        separator_index + 1 + lang_separator_index + 1 : -2
                    ]
                )
            else:
                return (
                    match_obj.group(0)[:deepest_index]
                    + match_obj.group(0)[separator_index + 1 : -2]
                )
        elif match_obj.group(0)[deepest_index + 2 : separator_index] == "main":
            # print "main|"
            # {{main|History of anarchism}}
            return "Main article: " + match_obj.group(0)[separator_index + 1 : -2]
        else:
            # print "unknown|"
            # {{...|...}}
            return match_obj.group(0)[:deepest_index]

    def parse_block_quote(self, match_obj):
        """Returns block quote tag content."""
        return match_obj.group(1)

    def parse_closed_tag(self, match_obj):
        """Parse tags. If nested get rid of the deepest element and repeat."""
        # ff = re.compile(r"(?:<|(?:&lt;))", re.DOTALL)
        # if match_obj.group(1).find("<"):
        # return match_obj.group(0)
        # else:
        # return ""
        # print("DEBUG: 0:", match_obj.group(0))
        # print("DEBUG: 1:", match_obj.group(1))
        return ""

    def parse_opened_tag(self, match_obj):
        """Parse tags. If nested get rid of the deepest element and repeat."""
        # print("DEBUG: openedTag")
        # return ""
        # match_obj.group(0) text with tags "<p>aa</p>"
        # match_obj.group(1) opening tag "<p>"
        # match_obj.group(2) tag name
        # print("DEBUG: MATCH:", match_obj.group(0))
        # print("DEBUG: SEARCH IN:", match_obj.group(3)) #text without tags "aa"
        # print("DEBUG: TAGNAME:", match_obj.group("tagname"))
        # print("ot:", match_obj.group("otag"))
        # print("ct:", match_obj.group("ctag"))
        regex = r"(?i)(?:<|(?:&lt;))\s*"
        regex += match_obj.group("tagname")
        regex += r"\s*(?:.*?)(?<!/)(?:>|(?:&gt;))"
        # print("DEBUG: before parse_opened_tag() re.compile()")
        ff = re.compile(regex, re.DOTALL)
        ret = ""
        # print("DEBUG: before parse_opened_tag() ff.findall()")
        for i in ff.findall(match_obj.group(3)):
            # print(match_obj.group(3))
            ret += match_obj.group(1)
        if ret != "":
            # print("DEBUG: REPEATING")
            self.repeat = 1
        return ret

    def parse_soup(self, match_obj):
        """Removes that stinky tag soup."""
        ## test whether we are parsing something that's not a tag soup
        # if len(match_obj.group(0)) > 100:
        # print match_obj.group(0)
        return ""

    def parse_image_text(self, match_obj):
        """Returns unformated reference text."""
        lastNested = match_obj.group(0)[2:].rfind(
            "[["
        )  # start index of last nested element
        if lastNested == -1:  # if not nested
            return ""
        else:
            self.repeat = 1
            return match_obj.group(0)[: lastNested + 2]

    def repair_category(self, match_obj):
        """Repairs bad categories (i.e. \"category:abc\", \"Category:abc\")."""
        return "Category:" + match_obj.group(2).capitalize() + match_obj.group(3)

    def repair_article_name(self, article_name):
        """Repairs bad formated category/link/title."""
        if len(article_name) > 0:
            article_name = self.repaCatRE.sub(self.repair_category, article_name)
            article_name = self.repaBlaRE.sub("_", article_name)
            article_name = self.repaTraRE.sub("_", article_name)
            article_name = article_name[0].upper() + article_name[1:]
        return article_name

    def parse_category(self, match_obj):
        """Collects categories"""
        if self.arg_references or self.arg_categories_file:
            index = match_obj.group(1).find("|")
            if index == -1:
                category = self.repair_article_name(match_obj.group(1))
            else:
                category = self.repair_article_name(match_obj.group(1)[:index])
            self.wiki_data.categories.append(category)
        return ""

    def parse_reference(self, match_obj):
        """Returns unformated reference text."""
        # print "parse_reference"
        annotation = match_obj.group(1)
        ret = "<annotation "

        if annotation[:7] == "http://":
            return ""

        # if annotation[:2] == "s:":
        # ret += "source=\"wikisource\" "
        # annotation = annotation[2:]
        # elif annotation[:2] == "q:":
        # ret += "source=\"wikiquote\" "
        # annotation = annotation[2:]
        # elif annotation[:2] == "m:":
        # ret += "source=\"wikimedia\" "
        # annotation = annotation[2:]
        # elif annotation[:annotation.find(':')] in LANGUAGES_SET:
        # return ""

        lang_separator = annotation.find(":")
        if lang_separator != -1 and annotation[: annotation.find(":")] in LANGUAGES_SET:
            return ""

        link_separator = annotation.find("|")

        if link_separator == -1:  # self reference (e.g. [[aaa]])
            if self.arg_links_file:
                link = self.repair_article_name(annotation)
                self.wiki_data.links.append(link)
            if not self.arg_references:
                return annotation
            ret += 'target="' + annotation + '">' + annotation
        else:
            if self.arg_links_file or self.arg_references:
                link = self.repair_article_name(annotation[:link_separator])
                self.wiki_data.links.append(link)
            if not self.arg_references:
                return annotation[link_separator + 1 :]
            ret += 'target="' + link + '">' + annotation[link_separator + 1 :]
        ret += "</annotation>"
        return ret

    def parse_http(self, match_obj):
        """Returns text from html reference."""
        space_index = match_obj.group(0).find(" ")
        bracket_index = match_obj.group(0).find("]")
        if space_index == -1:
            return ""
        else:
            return (
                match_obj.group(0)[space_index + 1 : bracket_index]
                + match_obj.group(0)[bracket_index + 1 : -1]
            )

    def parse_bold(self, match_obj):
        """Remove bolds."""
        return match_obj.group(0)[3:-3]

    def parse_itallic(self, match_obj):
        """Remove itallics."""
        return match_obj.group(0)[2:-2]

    def parse_heading(self, match_obj):
        """Returns parsed heading."""
        return re.sub(r"[=]+[\ ]*", "\n", match_obj.group(0))

    def parse_item_list(self, match_obj):
        """Returns parsed item list (replaces '*' with '\t' in item list)."""
        return (
            match_obj.group(0)
            .replace(" ", "")
            .replace(":", "")
            .replace(";", "")
            .replace("*", "\t")
            .replace("#", "\t")
        )

    def parse_tag_TT(self, match_obj):
        """This tag is used for displaying speciel marks as text."""
        return match_obj.group(1)

    def get_wiki_data(self, text):
        """Get plain (unformatted) text, references, links, categories from wikidump formatted text."""
        # redirected pages (articles), i.e. #REDIRECT
        # redirection is handeled befor this method ... in xml parsing
        if self.arg_references:
            if text[:9].upper() == "#REDIRECT":
                self.wiki_data.plain_text = (
                    '<redirect target="' + self.wikiRedRE.sub(r"\g<1>", text) + '"/>'
                )
                return

        if self.arg_redirects_file:
            if text[:9].upper() == "#REDIRECT":
                self.wiki_data.redirect = self.repair_article_name(
                    self.wikiRedRE.sub(r"\g<1>", text)
                )
                return

        ### DELETING
        ## GOOD TO PARSE AS FIRST (commented tags can make a mess)
        # comments, i.e. &lt;!-- ... --&gt;
        text = self.wikiComRE.sub("", text)  # <-- TODO: Heavy processing, optimize

        ### DELETING
        # br tags, i.e. &lt;br&gt;
        # &lt; or '<' are the same but it depends on how you get the input
        # both will be used for safety reasons
        text = self.wikiBrtRE.sub("", text)  # <-- TODO: Heavy processing, optimize

        ### DELETING / REPLACING
        # other curly brackets (even nested ones, like Infobox), i.e. {{ ... }}
        while self.repeat:
            self.repeat = 0  # if no nested elements then don't repeat
            text = self.wikiCurRE.sub(
                self.parse_curly, text
            )  # <-- TODO: Heavy processing, optimize
        self.repeat = 1

        ### DELETING
        # some sort of wiki table, i.e. {| ... |}
        while self.repeat:
            self.repeat = 0  # if no nested elements then don't repeat
            text = self.wikiTabRE.sub(self.parse_table, text)
        self.repeat = 1

        ### REPLACING
        # wiki images, i.e. [[Image:...]]
        # wiki files, i.e. [[File:...]]
        # wiki references are sometimes nested in image comments,
        # e.g. [[abc|...[[defg|[[...]]...]]]]
        while self.repeat:
            self.repeat = 0  # if no nested elements then don't repeat
            text = self.wikiImgRE.sub(self.parse_image_text, text)
        self.repeat = 1

        ### REPLACING
        ## MUST GO BEFORE ALL TAGS PARSING
        # blocks of guotes, i.e. <blockquote>...</blockquote>
        text = self.wikiBlqRE.sub(self.parse_block_quote, text)

        ## MUST GO BEFORE TT TAGS PARSING
        # html ascii decimal characters, i.e. &#230
        text = self.wikiSChRE.sub(
            self.parse_special_char, text
        )  # <-- TODO: Heavy processing, optimize
        ## MUST GO BEFORE ALL TAGS PARSING
        # tt tags, i.e. <tt>&amp;amp;#230</tt>
        text = self.wikiTttRE.sub(self.parse_tag_TT, text)

        ### DELETING
        # opened tags, i.e. <abc>...</(abc)>
        # print("DEBUG: before parse_opened_tag()")
        while self.repeat:
            self.repeat = 0  # if no nested elements then don't repeat
            # print(text)
            # with open('last-text2.txt', 'wb') as output: # DEBUG
            #  output.write(text.encode(DEFAULT_ENCODING)) # DEBUG
            # print("DEBUG: before calling re")
            text = self.wikiOtaRE.sub(
                self.parse_opened_tag, text, timeout=REGEX_TIMEOUT
            )  # <-- TODO: Heavy processing, optimize
            # print("DEBUG: after calling re")
        self.repeat = 1

        ### DELETING
        ## MUST GO AFTER OPENNED TAGS PARSING
        # closed tags, i.e. <abc ... />
        # print("DEBUG: before parse_closed_tag()")
        text = self.wikiCtaRE.sub(
            self.parse_closed_tag, text
        )  # <-- TODO: Heavy processing, optimize

        ### DELETING
        ## MUST GO AFTER OPENNED AND CLOSED TAGS PARSING
        # tag soup (bad tags)
        # print("DEBUG: before parse_soup()")
        text = self.wikiStaRE.sub(self.parse_soup, text)

        ### DELETING
        # print("DEBUG: before parse_category()")
        if (
            self.arg_text or self.arg_categories_file
        ):  # if parsing text, categories need to be cut away
            # wiki categories, i.e. [[Category:Anarchism| ]]
            text = self.wikiCatRE.sub(self.parse_category, text)

        ### REPLACING
        # wiki http reference, i.e. [http://abc/ ...]
        text = self.wikiHttRE.sub(self.parse_http, text)

        ### REPLACING
        # wiki references, i.e. [[aa|bb]]
        text = self.wikiRefRE.sub(
            self.parse_reference, text
        )  # <-- TODO: Heavy processing, optimize

        # no need to continue if only categories and/or links are being parsed
        if not self.arg_text:
            return

        ### REPLACING
        # &gt &lt &amp etc.
        text = self.wikiSMaRE.sub(self.parse_special_mark, text)

        ### REPLACING
        # bold, i.e. '''...'''
        text = self.wikiBolRE.sub(self.parse_bold, text)

        ### REPLACING
        # itallic, i.e. ''...''
        text = self.wikiItaRE.sub(self.parse_itallic, text)

        ### REPLACING
        # wiki item listing, i.e. "* ..." or "# ..." or ":; ..." or ":# ..."
        text = self.wikiIteRE.sub(self.parse_item_list, text)

        ### REPLACING
        # EOL formating
        # text = self.wikiEolRE.sub('\n', text)

        ### REPLACING
        # whitespace formating (removes clusters of more than 2 whitespaces)
        text = self.wikiWhiRE.sub(" ", text)  # <-- TODO: Heavy processing, optimize

        ### REPLACING
        # remove empty brackets
        text = self.wikiBraRE.sub("", text)

        ### REPLACING
        # headings, i.e. ===...===
        # print("DEBUG: before parse_heading()")
        text = self.wikiHeaRE.sub(
            self.parse_heading, text
        )  # <-- TODO: Heavy processing, optimize

        self.wiki_data.plain_text = text

        return

    def get_etree_and_namespace(self, xml_file):
        """Designed to grab the namespace from the first element of the xml file.
        Unfortunately to do so it has to start parsing and so it returns both namespace and etree.
        TODO: Find a way to restart lxml parsing and make this function solely about just retrieving namespaces
        """
        events = ("start", "start-ns", "end")
        root = None
        namespaces = {}
        if xml_file == sys.stdin:  # input from STDIN?
            xml_file = xml_file.buffer  # work on stdin buffer

        context = lxml.etree.iterparse(xml_file, events)
        context = iter(context)
        event, elem = next(context)
        if event == "start-ns":
            if elem[0] in namespaces and namespaces[elem[0]] != elem[1]:
                # NOTE: It is perfectly valid to have the same prefix refer
                #     to different URI namespaces in different parts of the
                #     document. This exception serves as a reminder that this
                #     solution is not robust.    Use at your own peril.
                raise KeyError("Duplicate prefix with different URI found.")
            namespaces[elem[0]] = "%s" % elem[1]
        elif event == "start":
            if root is None:
                root = elem

        return context, namespaces[""] if "" in namespaces else namespaces

    def parse_test(self):
        """TODO: Temporary method that will be replaced by unit tests in near future."""

        # print("INPUT (use CTRL-D in Unix or CTRL-Z in Windows to start parsing):\n")
        input_data = bytes(
            self.arg_input.read(), "utf8"
        )  # send EOF to signify end of input
        # input_data = unicodedata.normalize("NFKD", input_data.decode(DEFAULT_ENCODING)) # Normal Form KD

        self.get_wiki_data(input_data)  # convert data to plaintext
        sys.stdout.write(self.wiki_data.plain_text)  # write to STDOUT

    def ParseWiki(self):
        """Parse text, links, categories from a wikidump."""

        # getting file size
        if (
            self.arg_input != sys.stdin
            and self.arg_output != sys.stdout
            and self.arg_verbose
        ):
            input_file_size = self.get_file_size(self.arg_input)
            previous_progress = ("", 0)

        try:  # to initialize wiki2xml parser
            context, ns = self.get_etree_and_namespace(self.arg_input)
            # context = lxml.etree.iterparse(self.arg_input, events = ("start", "end"))
            # context = iter(context)
            event, root = next(context)
        except:
            raise
            sys.stderr.write(
                '\nERROR: Bad input file (not a wikidump), try "-T" for testing purposes.\n'
            )

        # setting skip
        count = 0
        if self.arg_skip:
            count = self.arg_skip

        # skipping N number of articles
        if self.arg_skip:
            try:
                for i in range(count):
                    event, element = next(context)
                    # percentage
                    if (
                        self.arg_input != sys.stdin
                        and self.arg_output != sys.stdout
                        and self.arg_verbose
                    ):
                        current_file_size = self.arg_input.tell()
                        previous_progress = self.print_progress(
                            input_file_size, current_file_size, previous_progress
                        )
                    if event == "end":
                        element.clear()
                    while element.getprevious() is not None:
                        del element.getparent()[0]

            except StopIteration:
                if self.arg_input != sys.stdin and self.arg_output != sys.stdout:
                    sys.stdout.write("\nINFO: Whole wikidump skipped.\n")
                sys.exit(0)

        # prepare namespace variables (later used identifying elements of the tree)
        nsdict = {"ns": ns}
        ns = "{%s}" % ns

        # prepare links file
        if self.arg_links_file:
            if self.arg_skip:
                self.arg_lnk_file = (
                    self.arg_links_file
                    if type(self.arg_links_file) == BytesIO
                    else open(self.arg_links_file, "ab")
                )
            else:
                self.arg_lnk_file = (
                    self.arg_links_file
                    if type(self.arg_links_file) == BytesIO
                    else open(self.arg_links_file, "wb")
                )

        # prepare categories file
        if self.arg_categories_file:
            if self.arg_skip:
                self.arg_cat_file = (
                    self.arg_categories_file
                    if type(self.arg_categories_file) == BytesIO
                    else open(self.arg_categories_file, "ab")
                )
            else:
                self.arg_cat_file = (
                    self.arg_categories_file
                    if type(self.arg_categories_file) == BytesIO
                    else open(self.arg_categories_file, "wb")
                )

        # prepare redirects file
        if self.arg_redirects_file:
            if self.arg_skip:
                self.arg_red_file = (
                    self.arg_redirects_file
                    if type(self.arg_redirects_file) == BytesIO
                    else open(self.arg_redirects_file, "ab")
                )
            else:
                self.arg_red_file = (
                    self.arg_redirects_file
                    if type(self.arg_redirects_file) == BytesIO
                    else open(self.arg_redirects_file, "wb")
                )

        for event, element in context:

            try:

                count += 1

                self.wiki_data.__init__()
                # percentage
                if (
                    self.arg_input != sys.stdin
                    and self.arg_output != sys.stdout
                    and self.arg_verbose
                ):
                    current_file_size = self.arg_input.tell()
                    previous_progress = self.print_progress(
                        input_file_size, current_file_size, previous_progress
                    )

                if element.tag == (ns + "page") and event == "end":

                    titles = element.xpath("ns:title/text()", namespaces=nsdict)
                    ids = element.xpath("ns:id/text()", namespaces=nsdict)
                    texts = element.xpath(
                        "ns:revision/ns:text/text()", namespaces=nsdict
                    )

                    if len(titles) != 1:
                        continue

                    if len(ids) != 1:
                        continue

                    title = titles[0]
                    id = ids[0]

                    ##if ref flag was not found
                    ##ignore redirected pages (articles), i.e. #REDIRECT or #redirect
                    # if (wiki[:9] == "#REDIRECT" or wiki[:9] == "#redirect") and not self.arg_references or :
                    # element.clear()
                    # continue

                    # print("DEBUG: before self.get_wiki_data()")
                    link_text = None
                    category_text = None
                    redirect_text = None
                    repaired_title = self.repair_article_name(title)

                    wiki = unicodedata.normalize(
                        "NFKD", "".join(texts)
                    )  # <-- TODO: Heavy processing, optimize
                    # wiki = u"".join(texts)

                    self.get_wiki_data(wiki)

                    if self.arg_links_file:
                        link_text = ""
                        for i in self.wiki_data.links:
                            link_text += repaired_title + "\t" + i + "\n"

                    if self.arg_categories_file:
                        category_text = ""
                        for i in self.wiki_data.categories:
                            category_text += repaired_title + "\t" + i + "\n"

                    if self.arg_redirects_file:
                        if self.wiki_data.redirect is not None:
                            redirect_text = (
                                repaired_title + "\t" + self.wiki_data.redirect + "\n"
                            )

                    # write to *.edg files
                    if link_text is not None:
                        self.arg_lnk_file.write(link_text.encode(DEFAULT_ENCODING))
                    if category_text is not None:
                        self.arg_cat_file.write(category_text.encode(DEFAULT_ENCODING))
                    if redirect_text is not None:
                        self.arg_red_file.write(redirect_text.encode(DEFAULT_ENCODING))

                    # write text
                    if self.wiki_data.plain_text is not None:

                        # xml output
                        if self.arg_text:
                            page_element = lxml.etree.Element("article")
                            id_element = lxml.etree.SubElement(page_element, "id")
                            id_element.text = id
                            title_element = lxml.etree.SubElement(page_element, "title")
                            title_element.text = title
                            text_element = lxml.etree.SubElement(page_element, "text")
                            text_element.text = self.wiki_data.plain_text
                            if self.arg_references:
                                categories_element = lxml.etree.SubElement(
                                    page_element, "categories"
                                )
                                categories_text = ""
                                for i in self.wiki_data.categories:
                                    categories_text += '<category target="' + i + '"/>'
                                categories_element.text = categories_text

                            if self.arg_output == sys.stdout:  # write to STDOUT?
                                print(
                                    lxml.etree.tostring(
                                        page_element, encoding=DEFAULT_ENCODING
                                    ).decode()
                                )
                            else:  # write to a FILE
                                lxml.etree.ElementTree(page_element).write(
                                    self.arg_output, encoding=DEFAULT_ENCODING
                                )
                                self.arg_output.write(
                                    b"\n"
                                )  # add a line break after each element

                    # free every page element (otherwise the RAM would overflow eventually)
                    element.clear()
                    while element.getprevious() is not None:
                        del element.getparent()[0]

            except TimeoutError:
                sys.stderr.write(
                    f'\nWARNING: Skipping article "{repaired_title}". Took longer than {REGEX_TIMEOUT} seconds to parse.\n'
                )
                element.clear()
                while element.getprevious() is not None:
                    del element.getparent()[0]
                continue

            except KeyboardInterrupt:
                sys.stderr.write(
                    "\nWARNING: Prematurely aborted parsing (not all articles have been processed).\n"
                )
                if self.arg_input != sys.stdin and self.arg_output != sys.stdout:
                    sys.stderr.write(
                        'WARNING: To resume parsing run the same command again with additional "-s '
                        + str(count)
                        + '" option.\n'
                    )
                element.clear()
                while element.getprevious() is not None:
                    del element.getparent()[0]
                if self.arg_links_file:
                    self.arg_lnk_file.close()
                if self.arg_categories_file:
                    self.arg_cat_file.close()
                if self.arg_redirects_file:
                    self.arg_red_file.close()
                break

            except IOError:
                sys.stderr.write(
                    "\nERROR: Input/Output filesystem related problem (File too large, No such file or directory, etc.).\n"
                )
                if self.arg_input != sys.stdin and self.arg_output != sys.stdout:
                    sys.stderr.write(
                        'WARNING: To resume parsing run the same command again with additional "-s '
                        + str(count)
                        + '" option.\n'
                    )
                element.clear()
                while element.getprevious() is not None:
                    del element.getparent()[0]
                if self.arg_links_file:
                    self.arg_lnk_file.close()
                if self.arg_categories_file:
                    self.arg_cat_file.close()
                if self.arg_redirects_file:
                    self.arg_red_file.close()
                break

            except:
                raise
                # Unknown error... continue parsing.
                sys.stderr.write(
                    f'\nWARNING: Skipping article "{repaired_title}". Unexpected error occured.\n'
                )
                element.clear()
                while element.getprevious() is not None:
                    del element.getparent()[0]
                continue

        else:
            element.clear()
            while element.getprevious() is not None:
                del element.getparent()[0]
            if self.arg_links_file and type(self.arg_lnk_file) != BytesIO:
                self.arg_lnk_file.close()
            if self.arg_categories_file and type(self.arg_cat_file) != BytesIO:
                self.arg_cat_file.close()
            if self.arg_redirects_file and type(self.arg_red_file) != BytesIO:
                self.arg_red_file.close()


################################################################################
# --------------------------------</CLASSES>---------------------------------- #
################################################################################


################################################################################
# --------------------------------<MAIN>-------------------------------------- #
################################################################################

if __name__ == "__main__":

    processor = Processor()  # construct a processor (will inherit Conductor)
    processor.get_options()  # evaluate startup options

    # HACK: temporary way to extract plain_text from short wiki-like content (currently aimed to allow some direct testing)
    # TODO: Replace with proper lxml parsing from input
    if processor.arg_test:  # testing? (input from stdin)
        processor.parse_test()
        sys.exit(0)  # don't attempt to continue parsing with lxml during STDIN tests

    # do the actual parsing
    if (
        processor.arg_text
        or processor.arg_links_file
        or processor.arg_categories_file
        or processor.arg_redirects_file
    ):
        processor.ParseWiki()
    else:  # Options misued? / No output expected to be produced?
        if processor.arg_verbose:
            sys.stdout.write(
                "\nINFO: Executed with options that didn't result in any parsed output. Try to use some other option combination.\n"
            )

    del processor  # clean-up

################################################################################
# --------------------------------</MAIN>------------------------------------- #
################################################################################

# END OF SCRIPT
