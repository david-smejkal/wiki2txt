# wiki2txt

A tool to extract plain (unformatted) multilingual / language-agnostic text, redirects, links and categories from wikipedia backups.
Designed to prepare clean training data for AI Training / Machine Learning software.<br />

Written in Python, utilizes `lxml` SAX (memory efficient) parser and leans heavily on the powers of the `regex` library.<br /><br />
![wiki2txt demo](https://smejkal.software/img/wiki2txt-demo.gif)

[Wiki XML dumps](https://dumps.wikimedia.org/backup-index-bydb.html):

* <https://dumps.wikimedia.org/enwiki/> (English)
* <https://dumps.wikimedia.org/ruwiki/> (Russian)
* <https://dumps.wikimedia.org/zhwiki/> (Chinese)

# Installation

Supported Python versions: `3.4+`<br />
*NOTICE: Older version `0.5.0` of this script works with Python `2.7+`*<br /><br />

\[ Optional: Install and configure [virtualenvwrapper](https://virtualenvwrapper.readthedocs.io/en/latest/) to create your virtual environment with `mkproject` ]

```bash
$ mkproject wiki2txt
```

Alternatively if you don't have `mkproject` then create your virtual environment manually:

```bash
$ virtualenv --python=`which python3` wiki2txt
$ source ./wiki2txt/bin/activate
(wiki2txt) $
```

```csharp
(wiki2txt) $ git clone https://github.com/david-smejkal/wiki2txt.git .
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
  -j JOBS, --jobs=JOBS         Number of parallel JOBS (1 to 8, up to the CPU count).
  -n, --no-text                don't parse text (designed for use with -r -l -c options)
  -t, --text                   produce plain (unformatted) text (DEFAULT)
  -s NUMBER, --skip=NUMBER     skip (resume after) NUMBER of articles (append to -o FILE)
  -q, --quiet                  stop making noise
  -R, --references             retain references in text (links and categories)
  -r FILE, --redirects=FILE    outsource redirect articles to the FILE
  -l FILE, --links=FILE        capture articles' links in the FILE
  -c FILE, --categories=FILE   capture articles' categories in the FILE
  -T, --test                   test by parsing directly from STDIN (bypasses lxml parser)
```

# Output Format

```xml
<article>
  <id>12</id>
  <title>Anarchism</title>
  <text>Anarchism is a political philosophy ...</text>
</article>
```

# Performance

> Tested using a single process running on one core of Intel i7 1.8 GHz processor

`Python v3.11 (lxml v4.9.2)` - Wikidump processing speed of `9.7 MB/s`<br />
`Python v3.10 (lxml v4.9.2)` - Wikidump processing speed of `9.2 MB/s`<br />
`Python v3.9  (lxml v4.6.4)` - Wikidump processing speed of `7.6 MB/s`<br />
`Python v2.7  (lxml v4.6.4)` - Wikidump processing speed of `5.2 MB/s`<br />
*NOTICE: Parsing speed usually improves with newer versions of Python and lxml library.*<br />
*e.g. parsing with python `v3.11` is about 86% faster than with `v2.7`.* <br />

> Tested by utilizing multiple cores of Intel i7 1.8 GHz () processor

`wiki2txt v0.7.0-beta using --job=8, Python v3.13 (lxml v5.3.1)` - Wikidump processing speed of `18.2 MB/s`<br />

Based on the above, with one job (default parsing) it should take about 2 hours to process the latest `en` wikidump (72 GB of decompressed data).
Utilizing multiprocessing with `--job=8` in the latest beta version (current master) doubles the parsing speed.

# Examples

## Download => Decompress => Parse

```console
(wiki2txt) $ wget -O articles1.xml.bz2 https://dumps.wikimedia.org/enwiki/latest/enwiki-latest-pages-articles1.xml-p1p41242.bz2 # 254 MB
(wiki2txt) $ bzip2 --decompress articles1.xml.bz2 # 940 MB
(wiki2txt) $ python wiki2txt.py -i articles1.xml -o parsed.xml -r redirects.edg # 400 MB
```

## Download latest complete wikidump

```csharp
$ wget https://dumps.wikimedia.org/enwiki/latest/enwiki-latest-pages-articles.xml.bz2 # 19 GB
```

**HINT:** add `--continue` parameter if you need to resume the download

## Decompress

```console
$ bzip2 --decompress enwiki-latest-pages-articles.xml.bz2 # 72 GB
```

**HINT:** add `-k` parameter if you want to preserve the original archive

## Parse

```shell-session
(wiki2txt) $ python wiki2txt.py -i enwiki-latest-pages-articles.xml -o clean-data.xml
```

### Utilize multiprocessing

```shell-session
(wiki2txt) $ python wiki2txt.py -j 2 -i enwiki-latest-pages-articles.xml -o clean-data.xml
```

### Piping input

```
(wiki2txt) $ cat enwiki-latest-pages-articles.xml | python wiki2txt.py > clean-data.xml
```

### Piping input + multiprocessing

```
(wiki2txt) $ cat enwiki-latest-pages-articles.xml | python wiki2txt.py --job=8 > clean-data.xml
```

**HINT:** diverting output to a file like this yields slightly faster parsing.
