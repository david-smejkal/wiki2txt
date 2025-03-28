import optparse
import sys
import os
import locale

from multiprocessing import cpu_count

MAX_JOBS = (
    cpu_count()
)  # might increase above no. of CPUs to keep more tasks in flight to compensate for I/O delays and variable article length


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
            if options.skip is not None:
                self.arg_skip = int(options.skip)
        except Exception:
            sys.stderr.write("\nWARNING: Skip argument not integer (not skipping).\n")
            self.arg_skip = False

        self.arg_verbose = options.verbose
        if self.arg_verbose:
            locale.setlocale(locale.LC_ALL, "C")

        self.arg_references = options.references

        if options.input is not None:
            self.arg_input_name = options.input
            self.arg_input = open(options.input, "rb")
        else:
            self.arg_skip = False
            self.arg_input_name = "stdin"
            self.arg_input = sys.stdin

        if options.output is not None:
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

            # Add newline only at 100% completion
            if progress_percentage == "100.00":
                output += "\n"

            for i in range(previous_progress[1]):
                sys.stdout.write("\b")
            sys.stdout.write(output)
            sys.stdout.flush()

            return progress_percentage, len(output)

        return progress_percentage, previous_progress[1]
