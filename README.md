# financial-pdf-parsing

**financial-pdf-parsing** provides Python libraries for extracting data from
American bank and credit card PDF statements, as well as importers to bring the
data into a [Beancount](https://github.com/beancount/beancount) ledger. The
Beancount importer logic is separated from the PDF parsing logic so that the
latter is more reusable. It also helps show the connection to Beancount's APIs
(which took me some time to learn).

My preferred workflow for double-entry accounting with
[Beancount](https://github.com/beancount/beancount) is to download PDF
statements, extract transaction data, add them to my ledger, and file the
original PDF. I prefer PDF statements over alternatives like CSV and OFX because
I don't need to download additional files or trust tools with sensitive
credentials. With PDF statements my banks and credit card providers email me
monthly and I can then check the original source statement, account them and
file away with minimal overhead.

The following institutions and statement types are supported:

* American Express credit cards
* Bank of America bank accounts and credit cards
* Capital One bank accounts and credit cards
* Chase credit cards

The parsing of each has an end-to-end test using Beancount and anonymized
PDF files, described in the "Regressioh test peparation" section.

## Dependencies

* [Beancount](https://github.com/beancount/beancount)
* [dateutil](https://github.com/dateutil/dateutil)
* `pdftotext` from [Poppler](https://github.com/freedesktop/poppler)

## Example Beancount import.py

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

https://github.com/m-d-brown/beancount-basics has
more information about Beancount, with links to many better resources to
get started with it and double entry accounting.

## Regression test preparation

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
