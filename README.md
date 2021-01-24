# financial-pdf-parsing

This project has Python libraries for extracting data from some American
bank and credit card monthly PDF statements. I use them with my
[Beancount](https://github.com/beancount/beancount) set up. The Beancount
importer logic is separated from the PDF parsing logic so that the latter is
more reusable. It also helps show the connection to Beancount's APIs (which
took me some time to learn).

My preferred workflow for double-entry accounting with
[Beancount](https://github.com/beancount/beancount) is to download PDF
statements, extract transaction data, add them to my ledger, and file the
original PDF. I prefer PDF statements over alternatives like CSV and OFX
because I don't need to download additional files or trust tools with sensitive
credentials. With PDF statements, my banks and credit card providers email me
monthly and I can then check the original source statement, account them and
file away with minimal overhead.

The following institutions are supported:

* Bank of America credit cards

The project depends on:

* Beancount
* dateutil
* pdftotext

Beancount regression test PDF files are created by running `pdftotext` on
original statements, anonymizing the produced text, then printing to a PDF:

```console
% pdftotext -raw ~/Downloads/eStmt_2021-01-04.pdf > \
    financial-pdf-parsing/raw_test_data/eStmt_2021-01-04.txt

# Edit raw to anonymize values
% vi financial-pdf-parsing/raw_test_data/eStmt_2021-01-04.txt

# Open raw in Chrome and print to PDF to
# financial-pdf-parsing/financial_pdf_parsing/importer_regression/eStmt_2021-01-04.pdf
```
