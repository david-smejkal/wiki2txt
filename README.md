# wiki2txt
A tool to extract plaintext, redirects, links and categories from `wikidumps` (https://dumps.wikimedia.org/enwiki/).<br />
Designed to prepare "digestible food" (clean data) for AI learning software.<br />

Written in Python, utilizes `lxml` SAX (easy on memory) parser and leans heavily on the powers of the `re` library.<br /><br />
![wiki2txt demo](https://smejkal.software/img/wiki2txt-demo.gif)

# Installation
Optional: Use [virtualenvwrapper](https://virtualenvwrapper.readthedocs.io/en/latest/) to create your virtual environment
```csharp
$ mkproject --python="`which python2`" wiki2txt
(wiki2txt) $ pip install -r requirements.txt
```

# Usage
```csharp
(wiki2txt) $ python wiki2txt.py --help
Usage: wiki2txt.py [options]

Options:
  --version                    show program's version number and exit
  -h, --help                   show this help message and exit
  -i FILE, --input-file=FILE   take xml input from FILE otherwise from STDIN
  -o FILE, --output-file=FILE  output parsed articles to FILE otherwise to STDOUT
  -n, --no-text                don't parse text (designed for use with -r -l -c options)
  -t, --text                   produce plaintext (DEFAULT)
  -s NUMBER, --skip=NUMBER     skip (resume after) NUMBER of articles (appends to output files)
  -q, --quiet                  stop making noise
  -R, --references             retain references in text (links and categories)
  -r FILE, --redirects=FILE    outsource redirect articles to the FILE
  -l FILE, --links=FILE        capture articles' links in the FILE
  -c FILE, --categories=FILE   capture articles' categories in the FILE
  -T, --test                   parse input from STDIN. Use Ctrl + D to end input
```

# Output Format
```xml
<article>
  <id>ID</id>
  <title>TITLE</title>
  <text>PLAINTEXT</text>
</article>
```

# Examples

## Download > Decompress > Parse
```console
(wiki2txt) $ wget -O articles1.xml https://dumps.wikimedia.org/enwiki/latest/enwiki-latest-pages-articles1.xml-p1p41242.bz2 # 234 MB
(wiki2txt) $ bzip2 --decompress articles1.xml.bz2 # 893 MB
(wiki2txt) $ python wiki2txt.py -i articles1.xml -o parsed.xml -r redirects.edg # 400 MB
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