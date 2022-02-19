# plain-text-accounting-tools

**plain-text-accounting-tools** provides utilities and libraries to use
plain text accounting for managing finances. https://plaintextaccounting.org
is great overview of plain text accounting. Most of the tools in this
repository are built for [Beancount](https://github.com/beancount/beancount),
which I use. I also import transactions with
[beancount-import](https://github.com/jbms/beancount-import), which provides
fully featured importers, a slick web UI, and automatic match to account using
a machine learning algorithm.

The repository contains:

* **[vanguard_pdf_to_txns](#vanguard_pdf_to_txns)** to extract transactions from
  Vanguard history webpages saved as PDFs, which allows much more transaction
  than Vanguard provides through other means.
* **[ofx_pretty](#ofx_pretty)** to prettify OFX files.
* **[financial-pdf-parsing](#financial-pdf-parsing)** to extract transactions
  from PDF financial statements.

## vanguard_pdf_to_txns

**[vanguard_pdf_to_txns.py](vanguard_pdf_to_txns.py)** extracts transactions from
Vanguard history web pages saved to PDF. Vanguard provides structured CSV and
OFX files for only the last year. This provides structured data for the longer
length of time that Vanguard provides history via web pages, in 10 year time
intervals.  It outputs to either CSV or Beancount ledger files.

To get the input PDFs, go to "My Accounts" > "Transaction History"; select an account;
select "10 year", "All Holdings", and "All Transaction Types"; and click
"Update Table".  Save the page to a PDF in a new directory.  Call the PDF
"1.pdf". If you have more transactions, click "Next", save the next page as
"2.pdf" and repeat until you have no more transactions.

vanguard_pdf_to_txns creates '.txt' forms of each PDF when it
processes them. If these txt files exist, the tool reads them instead of
re-parsing the PDF. This allows you to fix formatting errors in the txt file.
Simply run the tool and if it errors out, edit the txt file and try again.

The tool depends on `pdftotext` being in the PATH. It requires the dateutil
and beancount Python packages to be installed.

Example:

```
% ls Vanguard-Retirement
1.pdf 2.pdf 3.pdf

% ./vanguard_pdf_to_txns.py --account_type retirement --output csv Vanguard-Retirement/*.pdf
date,fund,txn_type,shares,price,amount,filename
2021-01-01,Total Intl Stock Ix Inv,Buy,10,100.00 USD,1000 USD,1.pdf
...

% ./vanguard_pdf_to_txns.py --account_type retirement --output beancount Vanguard-Retirement/*.pdf
2021-01-01 * "Buy - Total Intl Stock Ix Inv"
  Assets:Vanguard:401k:VGTSX   10 VGTSX {100 USD}
  Assets:Vanguard:401k:Cash   -1000.00 USD
  Income:CapitalGains:Vanguard:401k:VGTSX

% ls Vanguard-Retirement
1.pdf 1.pdf.txt 2.pdf 2.pdf.txt 3.pdf 3.pdf.txt
```

## ofx_pretty

**[ofx_pretty.py](ofx_pretty.py)** takes a path to an OFX file as the first
argument and prints a prettified version to stdout. Prettified means that each
field is placed on its own line and fields are properly indented in the correct
hierarchy. ofx_pretty.py does not yet include the metadata at the start of the
file! You'll have to copy that yourself.

Requires Python 3.9 and https://github.com/csingley/ofxtools.

Example:

```
% ./ofx_pretty.py data/CapitalOne/2021-01-01_Checking...1234.qfx | head
<OFX>
  <SIGNONMSGSRSV1>
    <SONRS>
      <STATUS>
        <CODE>0</CODE>
        <SEVERITY>INFO</SEVERITY>
      </STATUS>
      <DTSERVER>202101010000.000</DTSERVER>
      <LANGUAGE>ENG</LANGUAGE>
      <FI>
```


## financial-pdf-parsing

**financial-pdf-parsing** provides Python libraries for extracting data from
American bank and credit card PDF statements, as well as importers to bring the
data into a [Beancount](https://github.com/beancount/beancount) ledger. The
Beancount importer logic is separated from the PDF parsing logic so that the
latter is more reusable. It also helps show the connection to Beancount's APIs
(which took me some time to learn).

My preferred workflow for some account, like credit cards, is to download PDF
statements, extract transaction data, add them to my ledger, and file the
original PDF. I prefer PDF statements over alternatives like OFX for credit
cards because and credit card providers email me monthly and I can then check
the original source statement, account them and file away with minimal overhead.

The following institutions and statement types are supported:

* American Express credit cards
* Bank of America bank accounts and credit cards
* Capital One bank accounts and credit cards
* Chase credit cards

The parsing of each has an end-to-end test using Beancount and anonymized
PDF files, described in the "Regression test preparation" section.

### Example Beancount import.py

The basis of my Beancount `import.py` file follows.

```python
#!/usr/bin/env python3

from beancount.ingest import scripts_utils
from beancount.ingest import extract

from financial_pdf_parsing import beancount as fin_importers

CONFIG = [
    fin_importers.AmericanExpressCC('Liabilities:Amex:BlueCash'),
    fin_importers.BankOfAmericaBank('Assets:BofA:Checking', '0123 4567 8901'),
    fin_importers.BankOfAmericaCreditCard('Liabilities:BofA:CashRewards', '4444
5555 6666 7777'),
    fin_importers.CapitalOneBank(
        'Assets:CapitalOne',
        {
            '112345678': 'Assets:CapitalOne:Checking',
            '12345678901': 'Assets:CapitalOne:MoneyMarket',
            '13456789012': 'Assets:CapitalOne:PerfSavings',
        }),
    fin_importers.CapitalOneCreditCard('Liabilities:CapitalOne:Venture'),
    fin_importers.ChaseCC('Liabilities:Chase:AmazonPrime'),
]

extract.HEADER = '' # Don't add the emacs mode
scripts_utils.ingest(CONFIG, hooks=[extract.find_duplicate_entries])
```

It's run as:

```console
$ ./import.py --downloads ~/Downloads extract -e ledger.bean > update.bean
```

### Regression test preparation

Beancount regression test PDF files are created by running `pdftotext` on
original statements, anonymizing the produced text, then printing to a PDF:

```console
% pdftotext -raw ~/Downloads/eStmt_2021-01-04.pdf >
    financial-pdf-parsing/raw_test_data/eStmt_2021-01-04.txt

# Edit raw to anonymize values
% vi financial-pdf-parsing/raw_test_data/eStmt_2021-01-04.txt

# Open raw in Chrome and print to PDF to
# financial-pdf-parsing/financial_pdf_parsing/importer_regression/bank_of_america_credit_card/eStmt_2021-01-04.pdf

# Regnerate regression test output files and view changes.
% pytest --generate
% git diff
```

### Dependencies

* [Beancount](https://github.com/beancount/beancount)
* [dateutil](https://github.com/dateutil/dateutil)
* `pdftotext` from [Poppler](https://github.com/freedesktop/poppler)
