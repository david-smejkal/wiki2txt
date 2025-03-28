import pytest

from wiki2txt.processor import Processor
from io import BytesIO


@pytest.mark.parametrize(
    "input_file, expected_output, redirects_file, expected_redirects_output, "
    + "links_file, expected_links_output, "
    + "categories_file, expected_categories_output, "
    + "jobs",  # Added jobs parameter
    [
        ### TEST #1 simple input output test
        (  # cat tests/data/52-pages-wikimedia.xml | python wiki2txt.py > tests/data/52p-txt.xml
            "tests/data/52-pages-wikimedia.xml",
            "tests/data/52p-txt.xml",
            None,
            None,
            None,
            None,
            None,
            None,
            1,  # default behaviour, single-threaded
        ),
        ### TEST #2 parsing out redirects
        (  # cat tests/data/52-pages-wikimedia.xml | python wiki2txt.py -r tests/data/52p-red.edg > tests/data/52p-txt-no-red.xml
            "tests/data/52-pages-wikimedia.xml",
            "tests/data/52p-txt-no-red.xml",
            BytesIO(),
            "tests/data/52p-red.edg",
            None,
            None,
            None,
            None,
            1,  # single-threaded
        ),
        ### TEST #3 parsing out links
        (  # cat tests/data/52-pages-wikimedia.xml | python wiki2txt.py -l tests/data/52p-lnk.edg > tests/data/52p-txt-no-lnk.xml
            "tests/data/52-pages-wikimedia.xml",
            "tests/data/52p-txt-no-lnk.xml",
            None,
            None,
            BytesIO(),
            "tests/data/52p-lnk.edg",
            None,
            None,
            1,  # single-threaded
        ),
        ### TEST #4 parsing out categories
        (  # cat tests/data/52-pages-wikimedia.xml | python wiki2txt.py -c tests/data/52p-cat.edg > tests/data/52p-txt-no-cat.xml
            "tests/data/52-pages-wikimedia.xml",
            "tests/data/52p-txt-no-cat.xml",
            None,
            None,
            None,
            None,
            BytesIO(),
            "tests/data/52p-cat.edg",
            1,  # single-threaded
        ),
        ### TEST #5 parsing out everything (redirects, links and categories)
        (  # cat tests/data/52-pages-wikimedia.xml | python wiki2txt.py -r tests/data/52p-red.edg -l tests/data/52p-lnk-no-red.edg -c tests/data/52p-cat-no-red.edg > tests/data/52p-txt-no-lnk-no-cat.xml
            "tests/data/52-pages-wikimedia.xml",
            "tests/data/52p-txt-no-red-no-lnk-no-cat.xml",
            BytesIO(),
            "tests/data/52p-red.edg",
            BytesIO(),
            "tests/data/52p-lnk-no-red.edg",  # NOTICE: if redirects are being parsed out then those pages will be left out of links edg file as well
            BytesIO(),
            "tests/data/52p-cat-no-red.edg",  # NOTICE: if redirects are being parsed out then those pages will be left out of categories edg file as well
            1,  # single-threaded
        ),
        ### TEST #6 multiprocessing with 2 jobs
        (  # cat tests/data/52-pages-wikimedia.xml | python wiki2txt.py -j 2 > tests/data/52p-txt.xml
            "tests/data/52-pages-wikimedia.xml",
            "tests/data/52p-txt.xml",
            None,
            None,
            None,
            None,
            None,
            None,
            2,  # multiprocessing with 2 jobs
        ),
    ],
)
def test_wikimedia_parsing(
    input_file,
    expected_output,
    redirects_file,
    expected_redirects_output,
    links_file,
    expected_links_output,
    categories_file,
    expected_categories_output,
    jobs,  # Added jobs parameter
):
    processor = Processor()
    processor.get_options()

    # alter parameters of processor to read test input and capture the output
    processor.arg_input = open(input_file, "rb")
    processor.arg_output = BytesIO()  # output into memory

    # configure processor depending on what's being tested
    processor.arg_redirects_file = redirects_file
    processor.arg_links_file = links_file
    processor.arg_categories_file = categories_file
    processor.jobs = jobs  # Set number of jobs for multiprocessing

    processor.ParseWiki()  # start parsing

    with open(expected_output, "rb") as e_o:
        assert processor.arg_output.getvalue() == e_o.read()  # test main output
        if processor.arg_redirects_file:  # parsing out redirects?
            with open(expected_redirects_output, "rb") as e_r_o:
                assert (
                    processor.arg_redirects_file.getvalue() == e_r_o.read()
                )  ## test redirects output
        if processor.arg_links_file:  # parsing out links?
            with open(expected_links_output, "rb") as e_l_o:
                assert (
                    processor.arg_links_file.getvalue() == e_l_o.read()
                )  ## test links output
        if processor.arg_categories_file:  # parsing out categories?
            with open(expected_categories_output, "rb") as e_c_o:
                assert (
                    processor.arg_categories_file.getvalue() == e_c_o.read()
                )  ## test categories output

    # Clean up input file handle
    # processor.arg_input.close()  # Explicitly close since it’s always a file handle
    del processor
