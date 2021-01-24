import datetime

from dateutil import parser

# TODO: use internal types for transactions so that the core parsing doesn't
#       need to depend on Beancount and so is fully generic?
from beancount.core import data
from beancount.core import flags

from financial_pdf_parsing import pdf

FILE_PATTERN =  r'^eStmt_.*\.pdf$'

def readTransactions(f, filename, account, closing_date):
    transactions = []
    index = 0

    for line in f:
        line = line.strip('\n')
        # Line structure:
        # 0-txn-date 1-post-date description -3-ref-date -2-acct -1-amount
        parts = line.split()
        if len(parts) < 6:
            break # Assume we've hit the end.

        try:
            date = parser.parse(parts[0]).date()
        except parser.ParserError:
            break # Assume we've hit the end.
        date = pdf.AdjustDateForYearBoundary(date, closing_date)
        amt = pdf.ParseAmount(parts[-1])
        # We are treating as a liability so invert.
        amt = pdf.InvertAmount(amt)
        descr = ' '.join(parts[2:-3])

        meta = data.new_metadata(filename, index)
        index += 1
        postings = [data.Posting(account, amt, None, None, None, None)]
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

    return transactions


def Read(filename, account):
    """Reads the PDF at filename and returns a list of Beancount transactions.

    account is the string account name to which one side of
    transactions should be recorded. Should be a liability account.
    """
    contents = pdf.StringIO(filename)

    balance = None
    closing_date = None
    transactions = []

    for line in contents:
        line = line.strip('\n')
        # TODO: process rewards balance too

        if line.startswith('New Balance Total'):
            if balance is None:
                parts = line.split()
                balance = pdf.ParseAmount(parts[-1])
                # We are treating as a liability so invert.
                balance = pdf.InvertAmount(balance)

        elif line.startswith('Statement Closing Date'):
            if closing_date is not None:
                raise ValueError('already processed closing_date')
            parts = line.split()
            closing_date = parser.parse(parts[-1]).date()

        elif line == 'Purchases and Adjustments':
            if closing_date is None:
                raise ValueError('unable to find Closing Date before reaching transactions')
            transactions.extend(readTransactions(contents, filename, account, closing_date))

        elif line == 'Payments and Other Credits':
            if closing_date is None:
                raise ValueError('unable to find Closing Date before reaching transactions')
            transactions.extend(readTransactions(contents, filename, account, closing_date))

    transactions.append(
            data.Balance(
                data.new_metadata(filename, len(transactions)),
                closing_date + datetime.timedelta(days=1),
                account, balance, None, None),
    )

    return transactions

