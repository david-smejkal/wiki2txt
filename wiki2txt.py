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
from multiprocessing import Pool, cpu_count  # Added for multiprocessing

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

MAX_JOBS = (
    cpu_count()
)  # might increase above no. of CPUs to keep more tasks in flight to compensate for I/O delays and variable article length

ARTICLES_PER_JOB = 50  # batch size of lxml parsed articles processed per job

# TODO list:
#   DONE: Implemented a set of basic functional tests
#   DONE: Dropped Python v2 support
#   DONE: Fixed STDIN processing to actually allow piping of input and separate it from the -T option
#   DONE: Redesigned parsing so that it would be able to utilize more CPU cores (now using multiprocessing library)
#   TODO: Start using tox for running tests (instead of running pytest directly)
#   TODO: Break up classes into individual files
#   TODO: Implement a proper logger to simplify debugging
#   TODO: Implement an option to store parsed output in SQLite DB format
#   TODO: Profile and optimize code where appropriate to speed up processing / parsing
#   TODO: Explore an idea to replace standard lxml lib with an lxml lib that has C optimizations
#   TODO: Implement a better way to handle runnaway regex than REGEX_TIMEOUT (then switch back to the standard re library)
#   TODO: Cover 100% of code with unit tests
#   TODO: Review the necessity for unicodedata normalization (it seems unnecessary to normalize unicode strings in Python v3)
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
            usage="usage: %prog [options]", version="%prog 0.7.0-beta"
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
        opt_parser.add_option(  # multiprocessing if jobs > 1
            "-j",
            "--jobs",
            dest="jobs",
            type="int",
            default=1,
            help=f"Number of parallel jobs (1 to {MAX_JOBS}, up to the CPU count). Defaults to 1.",
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

        # Validate jobs parameter
        if (
            not isinstance(options.jobs, int)
            or options.jobs < 1
            or options.jobs > MAX_JOBS
        ):
            sys.stderr.write(
                f"\nWARNING: Invalid number of jobs ({options.jobs}). Must be between 1 and {MAX_JOBS} (up to 2x the CPU count). Defaulting to 1.\n"
            )
            self.jobs = 1
        else:
            self.jobs = options.jobs

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
        if hasattr(file, "seek"):  # Check if seekable (file handle or BytesIO)
            file.seek(0, os.SEEK_END)
            size = file.tell()
            file.seek(0, os.SEEK_SET)
            return size
        return 0  # Return 0 for non-seekable (e.g., stdin)

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

        try:
            context, ns = self.get_etree_and_namespace(self.arg_input)
            event, root = next(context)
        except:
            raise
            sys.stderr.write(
                '\nERROR: Bad input file (not a wikidump), try "-T" for testing purposes.\n'
            )

        count = 0
        if self.arg_skip:
            count = self.arg_skip

        if self.arg_skip:
            try:
                for i in range(count):
                    event, element = next(context)
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

        nsdict = {"ns": ns}
        ns = "{%s}" % ns

        # Prepare file handles for output
        if self.arg_links_file:
            self.arg_lnk_file = (
                self.arg_links_file
                if type(self.arg_links_file) == BytesIO
                else open(self.arg_links_file, "ab" if self.arg_skip else "wb")
            )
        if self.arg_categories_file:
            self.arg_cat_file = (
                self.arg_categories_file
                if type(self.arg_categories_file) == BytesIO
                else open(self.arg_categories_file, "ab" if self.arg_skip else "wb")
            )
        if self.arg_redirects_file:
            self.arg_red_file = (
                self.arg_redirects_file
                if type(self.arg_redirects_file) == BytesIO
                else open(self.arg_redirects_file, "ab" if self.arg_skip else "wb")
            )

        if self.jobs > 1:
            # Use multiprocessing with streaming
            with Pool(processes=self.jobs) as pool:
                article_args = []
                for event, element in context:
                    try:
                        count += 1
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

                            if len(titles) != 1 or len(ids) != 1:
                                continue

                            title = titles[0]
                            id = ids[0]
                            wiki = unicodedata.normalize("NFKD", "".join(texts))
                            article_args.append(
                                (
                                    title,
                                    id,
                                    wiki,
                                    self.arg_text,
                                    self.arg_links_file,
                                    self.arg_categories_file,
                                    self.arg_redirects_file,
                                    self.arg_references,
                                )
                            )

                            element.clear()
                            while element.getprevious() is not None:
                                del element.getparent()[0]

                        # Process articles in chunks to limit memory usage
                        if (
                            len(article_args) >= self.jobs * ARTICLES_PER_JOB
                        ):  # Process in small batches
                            results = pool.imap(process_article, article_args)
                            for (
                                output,
                                link_text,
                                category_text,
                                redirect_text,
                            ) in results:
                                if link_text and self.arg_lnk_file:
                                    self.arg_lnk_file.write(
                                        link_text.encode(DEFAULT_ENCODING)
                                    )
                                    # self.arg_lnk_file.flush()
                                if category_text and self.arg_cat_file:
                                    self.arg_cat_file.write(
                                        category_text.encode(DEFAULT_ENCODING)
                                    )
                                    # self.arg_cat_file.flush()
                                if redirect_text and self.arg_red_file:
                                    self.arg_red_file.write(
                                        redirect_text.encode(DEFAULT_ENCODING)
                                    )
                                    # self.arg_red_file.flush()
                                if output:
                                    if self.arg_output == sys.stdout:
                                        print(output.decode())
                                    elif self.arg_output is not None:
                                        self.arg_output.write(output)
                                        # self.arg_output.flush()  # Ensure immediate write
                            article_args = []

                    except TimeoutError:
                        sys.stderr.write(
                            f"\nWARNING: Skipping article. Took longer than {REGEX_TIMEOUT} seconds to parse.\n"
                        )
                        continue
                    except KeyboardInterrupt:
                        sys.stderr.write("\nWARNING: Prematurely aborted parsing.\n")
                        break
                    except IOError:
                        sys.stderr.write("\nERROR: I/O error.\n")
                        break
                    except:
                        import traceback

                        sys.stderr.write(
                            f"\nWARNING: Skipping article due to unexpected error: {traceback.format_exc()}\n"
                        )
                        continue

                # Process remaining articles
                if article_args:
                    results = pool.imap(process_article, article_args)
                    for output, link_text, category_text, redirect_text in results:
                        if link_text and self.arg_lnk_file:
                            self.arg_lnk_file.write(link_text.encode(DEFAULT_ENCODING))
                            # self.arg_lnk_file.flush()
                        if category_text and self.arg_cat_file:
                            self.arg_cat_file.write(
                                category_text.encode(DEFAULT_ENCODING)
                            )
                            # self.arg_cat_file.flush()
                        if redirect_text and self.arg_red_file:
                            self.arg_red_file.write(
                                redirect_text.encode(DEFAULT_ENCODING)
                            )
                            # self.arg_red_file.flush()
                        if output:
                            if self.arg_output == sys.stdout:
                                print(output.decode())
                            elif self.arg_output is not None:
                                self.arg_output.write(output)
                                # self.arg_output.flush()  # Ensure immediate write

        else:
            # Single-threaded processing (unchanged)
            for event, element in context:
                try:
                    count += 1
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

                        if len(titles) != 1 or len(ids) != 1:
                            continue

                        title = titles[0]
                        id = ids[0]
                        wiki = unicodedata.normalize("NFKD", "".join(texts))

                        repaired_title = self.repair_article_name(title)
                        self.wiki_data.__init__()
                        self.get_wiki_data(wiki)

                        if self.arg_links_file:
                            link_text = "".join(
                                repaired_title + "\t" + i + "\n"
                                for i in self.wiki_data.links
                            )
                            self.arg_lnk_file.write(link_text.encode(DEFAULT_ENCODING))
                        if self.arg_categories_file:
                            category_text = "".join(
                                repaired_title + "\t" + i + "\n"
                                for i in self.wiki_data.categories
                            )
                            self.arg_cat_file.write(
                                category_text.encode(DEFAULT_ENCODING)
                            )
                        if self.arg_redirects_file and self.wiki_data.redirect:
                            redirect_text = (
                                repaired_title + "\t" + self.wiki_data.redirect + "\n"
                            )
                            self.arg_red_file.write(
                                redirect_text.encode(DEFAULT_ENCODING)
                            )

                        if self.wiki_data.plain_text and self.arg_text:
                            page_element = lxml.etree.Element("article")
                            id_element = lxml.etree.SubElement(page_element, "id")
                            id_element.text = id
                            title_element = lxml.etree.SubElement(page_element, "title")
                            title_element.text = title
                            text_element = lxml.etree.SubElement(page_element, "text")
                            text_element.text = self.wiki_data.plain_text
                            if self.arg_references and self.wiki_data.categories:
                                categories_element = lxml.etree.SubElement(
                                    page_element, "categories"
                                )
                                categories_text = "".join(
                                    f'<category target="{i}"/>'
                                    for i in self.wiki_data.categories
                                )
                                categories_element.text = categories_text
                            output = (
                                lxml.etree.tostring(
                                    page_element, encoding=DEFAULT_ENCODING
                                )
                                + b"\n"
                            )
                            if self.arg_output == sys.stdout:
                                print(output.decode())
                            else:
                                self.arg_output.write(output)

                        element.clear()
                        while element.getprevious() is not None:
                            del element.getparent()[0]
                except TimeoutError:
                    sys.stderr.write(
                        f'\nWARNING: Skipping article "{repaired_title}". Took longer than {REGEX_TIMEOUT} seconds.\n'
                    )
                    continue
                except KeyboardInterrupt:
                    sys.stderr.write("\nWARNING: Prematurely aborted parsing.\n")
                    break
                except IOError:
                    sys.stderr.write("\nERROR: I/O error.\n")
                    break
                except:
                    sys.stderr.write(
                        f'\nWARNING: Skipping article "{repaired_title}". Unexpected error.\n'
                    )
                    continue

        # Cleanup
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
# --------------------------------<MULTIPROCESSING>--------------------------- #
################################################################################


def process_article(args):
    """
    Process a single article and return its output.
    Deliberately declared outside of the processor as a standalone function (not a method) to avoid pickling the Processor instance.
    """
    (
        title,
        id,
        wiki,
        arg_text,
        arg_links_file,
        arg_categories_file,
        arg_redirects_file,
        arg_references,
    ) = args
    processor = Processor()  # Create a new instance for each process
    processor.arg_text = arg_text
    processor.arg_links_file = arg_links_file
    processor.arg_categories_file = arg_categories_file
    processor.arg_redirects_file = arg_redirects_file
    processor.arg_references = arg_references

    repaired_title = processor.repair_article_name(title)
    processor.get_wiki_data(wiki)  # Populates processor.wiki_data

    link_text = None
    category_text = None
    redirect_text = None
    output = None

    if processor.arg_links_file and processor.wiki_data.links:
        link_text = "".join(
            repaired_title + "\t" + i + "\n" for i in processor.wiki_data.links
        )
    if processor.arg_categories_file and processor.wiki_data.categories:
        category_text = "".join(
            repaired_title + "\t" + i + "\n" for i in processor.wiki_data.categories
        )
    if processor.arg_redirects_file and processor.wiki_data.redirect:
        redirect_text = repaired_title + "\t" + processor.wiki_data.redirect + "\n"

    if processor.wiki_data.plain_text and processor.arg_text:
        page_element = lxml.etree.Element("article")
        id_element = lxml.etree.SubElement(page_element, "id")
        id_element.text = id
        title_element = lxml.etree.SubElement(page_element, "title")
        title_element.text = title
        text_element = lxml.etree.SubElement(page_element, "text")
        text_element.text = processor.wiki_data.plain_text
        if processor.arg_references and processor.wiki_data.categories:
            categories_element = lxml.etree.SubElement(page_element, "categories")
            categories_text = "".join(
                f'<category target="{i}"/>' for i in processor.wiki_data.categories
            )
            categories_element.text = categories_text
        output = lxml.etree.tostring(page_element, encoding=DEFAULT_ENCODING) + b"\n"

    return output, link_text, category_text, redirect_text


################################################################################
# --------------------------------</MULTIPROCESSING>-------------------------- #
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

    # Clean up file handle for single-threaded case
    if processor.jobs == 1 and processor.arg_input != sys.stdin:
        processor.arg_input.close()
    if processor.arg_output != sys.stdout and processor.arg_output is not None:
        processor.arg_output.close()

    del processor  # clean-up

################################################################################
# --------------------------------</MAIN>------------------------------------- #
################################################################################

# END OF SCRIPT
