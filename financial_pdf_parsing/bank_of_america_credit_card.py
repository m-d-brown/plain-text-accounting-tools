import collections
import datetime
import re

from dateutil import parser

# TODO: use internal types for transactions so that the core parsing doesn't
#       need to depend on Beancount and so is fully generic?
from beancount.core import data
from beancount.core import flags

from financial_pdf_parsing import pdf

FILE_PATTERN =  r'^eStmt_.*\.pdf$'


Transaction = collections.namedtuple('Transaction', 'date descr amount')

class BeancountLedgerItems:
    def __init__(self, filename):
        self.items = []
        self.filename = filename

    def _metadata(self):
        return data.new_metadata(self.filename, len(self.items))

    def AddTransactions(self, account, txns):
        for t in txns:
            postings = [data.Posting(account, t.amount, None, None, None, None)]
            self.items.append(data.Transaction(
                meta=self._metadata(),
                date=t.date,
                flag=flags.FLAG_OKAY,
                payee=None,
                narration=t.descr,
                tags=set(),
                links=set(),
                postings=postings,
            ))

    def AddBalance(self, account, closing_date, balance):
        self.items.append(data.Balance(
            self._metadata(),
            closing_date + datetime.timedelta(days=1),
            account, balance, None, None))

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

AMOUNT = r'-?\$?[0-9,]+\.[0-9]{1,2}'

def Read(filename, account):
    """Reads the PDF at filename and returns a list of Beancount transactions.

    account is the string account name to which one side of
    transactions should be recorded. Should be a liability account.
    """
    contents = pdf.PDFToText(filename)

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

    l = BeancountLedgerItems(filename)
    l.AddTransactions(account, transactions)
    l.AddBalance(account, closing_date, balance)
    return l.items
