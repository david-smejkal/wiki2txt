# wiki2txt
A tool to extract plaintext, links and categories from `wikidumps` (https://dumps.wikimedia.org/enwiki/).<br />
Designed to prepare "digestible food" (cleaner data) for AI learning software.<br />

Written in Python, utilizes `lxml` parser and leans heavily on the powers of the `re` (regex) library.

# Installation
Optional: Use [virtualenvwrapper](https://virtualenvwrapper.readthedocs.io/en/latest/) to create your virtual environment
```csharp
$ mkproject --python="`which python2`" wiki2txt
$ workon wiki2txt
(wiki2txt) $ pip install -r requirements.txt
```

# Usage
```csharp
(wiki2txt) $ python wiki2txt.py --help
Usage: wiki2txt.py [options]

Options:
  --version                    show program's version number and exit
  -h, --help                   show this help message and exit
  -i FILE, --input-file=FILE   Intput xml text will come from FILE otherwise from STDIN.
  -o FILE, --output-file=FILE  Output text will go to FILE otherwise to STDOUT.
  -n, --no-text                Don't parse text (designed for use with -r -l -c options).
  -t, --text                   Parse text from input to output (DEFAULT).
  -s NUMBER, --skip=NUMBER     Skip NUMBER of articles and append to output files.
  -q, --quiet                  Don't make any noise.
  -R, --references             Print references in text (links and categories).
  -r FILE, --redirects=FILE    Outsource redirect articles to the specified file.
  -l FILE, --links=FILE        Capture articles' links in the specified file).
  -c FILE, --categories=FILE   Capture articles' categories in the specified file.
  -T, --test                   Parse input from STDIN. Use Ctrl + D to end input.
```

# Output Format
```xml
<article>
  <id>ID</id>
  <title>TITLE</title>
  <text>PLAINTEXT</text>
  <categories>CATEGORIES</categories>
</article>
```

# Examples

## Download > Decompress > Parse
```console
(wiki2txt) $ wget https://dumps.wikimedia.org/enwiki/latest/enwiki-latest-pages-articles1.xml-p1p41242.bz2 # Download: 234 MB
(wiki2txt) $ bzip2 --decompress enwiki-latest-pages-articles1.xml-p1p41242.bz2 # Decompress: 893 MB
(wiki2txt) $ wiki2txt.py -i enwiki-latest-pages-articles1.xml-p1p41242.bz2 -o latest-pages-articles1-parsed.xml -r redirects.edg
```

## Download latest
**HINT:** add `--continue` parameter if you need to resume the download
```csharp
$ wget https://dumps.wikimedia.org/enwiki/latest/enwiki-latest-pages-articles.xml.bz2
```

## Decompress latest
**HINT:** add `-k` parameter if you want to preserve the original archive
```console
$ bzip2 --decompress enwiki-latest-pages-articles.xml.bz2
```

## Parse latest
```shell-session
(wiki2txt) $ python wiki2txt.py -t -i enwiki-latest-pages-articles.xml -o latest-food.xml -r redirects.edg
```