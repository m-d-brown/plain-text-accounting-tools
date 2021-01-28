"""parsers provides functions that parse PDF credit card statements."""

import collections
import datetime
import re
import subprocess

from dateutil import parser

from financial_pdf_parsing import pdf

def PDFToText(filename):
    """Returns the text for the given PDF."""
    return subprocess.check_output(['pdftotext', '-raw', filename, '-']).decode()

# date is a datetime. descr is a string. amount is a beancount data.Amount.
Transaction = collections.namedtuple('Transaction', 'date descr amount')

# A common pattern for dollar amounts.
AMOUNT = r'-?\$?[0-9,]+\.[0-9]{1,2}'

def compileRE(pattern):
    return re.compile(pattern, re.DOTALL)

def reduceSingleMatch(pattern, parser, text):
    pattern = compileRE(pattern)

    results = set()
    for match in pattern.finditer(text):
        r = parser(match)
        results.add(r)

    if len(results) == 0:
        raise ValueError(f'{parser.__name__}: found no matches')
    if len(results) > 1:
        raise ValueError(f'{parser.__name__}: found more than one match: {results}')
    return results.pop()

def parseAll(pattern, parser, text):
    pattern = compileRE(pattern)
    results = []
    for match in pattern.finditer(text):
        t = parser(match)
        results.append(t)
    return results


################################################################

BANK_OF_AMERICA_CREDIT_CARD_FILE_PATTERN =  r'^eStmt_.*\.pdf$'

def BankOfAmericaCreditCard(filename):
    """Reads the PDF at filename and returns contents.

    Returns (balance, closing_date, [Transaction]).
    """
    contents = PDFToText(filename)

    def _balance(match):
        b = pdf.ParseAmount(match.group(1))
        return pdf.InvertAmount(b) # Treat as liability
    balance = reduceSingleMatch(
            r'\bNew Balance Total +('+AMOUNT+r')\b',
            _balance, contents)

    def _closing(match):
        return parser.parse(match.group(1)).date()
    closing_date = reduceSingleMatch(
            r'\bStatement Closing Date (\d+/\d+/\d+)\b',
            _closing, contents)

    def _transaction(match):
        date = parser.parse(match.group(1)).date()
        date = pdf.AdjustDateForYearBoundary(date, closing_date)
        descr = match.group(2)
        amt = pdf.ParseAmount(match.group(3))
        amt = pdf.InvertAmount(amt) # Treat as liability
        return Transaction(date, descr, amt)
    transactions = parseAll(
            # Example:  12/05 12/07 WHOLE FOODS #1234 SF CA 8538 3456 251.49
            r'\b(\d{2}/\d{2}) \d{2}/\d{2} (.*?) \d+ \d+ ('+AMOUNT+r')\b',
            _transaction, contents)

    return balance, closing_date, transactions
