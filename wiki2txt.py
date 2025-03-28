#!/usr/bin/env python
# -*- coding: UTF-8 -*-

# Authors:     Marek Schmidt 2007, David Smejkal 2008
# Repository:  https://github.com/david-smejkal/wiki2txt
# License:     GPLv2

# standard libraries
import sys

# local imports
from wiki2txt.processor import Processor

# XML OUTPUT FORMAT
# <article>
#   <id>12</id>
#   <title>Anarchism</title>
#   <text>Anarchism is a political philosophy ...</text>
# </article>

# TODO list for v1.0.0:
#   DONE: Implemented a set of basic functional tests
#   DONE: Dropped Python v2 support
#   DONE: Fixed STDIN processing to actually allow piping of input and separate it from the -T option
#   DONE: Redesigned parsing so that it would be able to utilize more CPU cores (now using multiprocessing library)
#   DONE: Start using tox for running tests (instead of running pytest directly)
#   DONE: Separated classes into individual files
#   TODO: Implement a proper logger to simplify debugging
#   TODO: Implement an option to store parsed output in SQLite DB format instead of just a in a bare txt output
#   TODO: Profile and optimize code where appropriate to speed up processing / parsing

# TODO list for v1.0.1:
#   TODO: Explore an idea to replace standard lxml lib with an lxml lib that has C optimizations
#   TODO: Implement a better way to handle runnaway regex than REGEX_TIMEOUT (then switch back to the standard re library)
#   TODO: Cover 100% of code with unit tests
#   TODO: Review the necessity for unicodedata normalization (it seems unnecessary to normalize unicode strings in Python v3)
#   TODO: Think about allowing wikimedia syntax one-shot parsing (wrap STDIN input in a mediawiki like structure?)

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
                "\nINFO: Unsupported option combination. Nothing parsed.\n"
            )

    del processor  # clean-up

################################################################################
# --------------------------------</MAIN>------------------------------------- #
################################################################################

# END OF SCRIPT
