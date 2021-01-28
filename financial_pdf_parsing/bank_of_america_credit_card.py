import datetime
import re

from dateutil import parser

# TODO: use internal types for transactions so that the core parsing doesn't
#       need to depend on Beancount and so is fully generic?
from beancount.core import data
from beancount.core import flags

from financial_pdf_parsing import pdf

FILE_PATTERN =  r'^eStmt_.*\.pdf$'

def compileRE(pattern):
    return re.compile(pattern, re.DOTALL)

AMOUNT = r'-?\$?[0-9,]+\.[0-9]{1,2}'

BALANCE_RE = compileRE(r'\bNew Balance Total +('+AMOUNT+r')\b')

CLOSE_DATE_RE = compileRE(r'\bStatement Closing Date (\d+/\d+/\d+)\b')

# Example:  12/05 12/07 WHOLE FOODS #1234 SF CA 8538 3456 251.49
TRANSACTION_RE = compileRE(r'\b(\d{2}/\d{2}) \d{2}/\d{2} (.*?) \d+ \d+ ('+AMOUNT+r')\b')

def reduceMatches(pattern, text, match_transform):
    results = set()
    for match in pattern.finditer(text):
        r = match_transform(match)
        results.add(r)
    return results

def reduceSingleMatch(pattern, text, match_transform):
    results = reduceMatches(pattern, text, match_transform)
    if len(results) == 0:
        raise ValueError('found no balance')
    if len(results) > 1:
        raise ValueError(f'found more than one balance: {results}')
    return results.pop()
        

def Read(filename, account):
    """Reads the PDF at filename and returns a list of Beancount transactions.

    account is the string account name to which one side of
    transactions should be recorded. Should be a liability account.
    """
    contents = pdf.PDFToText(filename)

    def balanceTransform(m):
        b = pdf.ParseAmount(m.group(1))
        # We are treating as a liability so invert.
        return pdf.InvertAmount(b)
    balance = reduceSingleMatch(BALANCE_RE, contents, balanceTransform)

    def closeDateTransform(m):
        return parser.parse(m.group(1)).date()
    closing_date = reduceSingleMatch(CLOSE_DATE_RE, contents, closeDateTransform)

    transactions = []
    def txnTransform(m):
        date = parser.parse(m.group(1)).date()
        date = pdf.AdjustDateForYearBoundary(date, closing_date)
        descr = m.group(2)
        amt = pdf.ParseAmount(m.group(3))
        # We are treating as a liability so invert.
        amt = pdf.InvertAmount(amt)

        postings = [data.Posting(account, amt, None, None, None, None)]
        meta = data.new_metadata(filename, len(transactions))
        transactions.append(data.Transaction(
            meta=meta,
            date=date,
            flag=flags.FLAG_OKAY,
            payee=None,
            narration=descr,
            tags=set(),
            links=set(),
            postings=postings,
        ))
    for match in TRANSACTION_RE.finditer(contents):
        txnTransform(match)

    transactions.append(
            data.Balance(
                data.new_metadata(filename, len(transactions)),
                closing_date + datetime.timedelta(days=1),
                account, balance, None, None),
    )

    return transactions

