#!/usr/bin/env python3

"""vanguard_pdf_to_txns extracts transactions from Vanguard history web pages
saved to PDF. Vanguard provides structured CSV and OFX files for only the last
year. This provides structured data for the longer length of time that Vanguard
provides history via web pages, in 10 year time intervals.  It outputs to
either CSV or Beancount ledger files.

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
"""

import argparse
import collections
import csv
import decimal
import locale
import os.path
import re
import subprocess
import sys

from dateutil import parser

from beancount.core import number
from beancount.core import amount


# FUNDS maps the fund names in the PDFS to their symbols.
FUNDS = {
    'Mid-Cap Index Fund Adm': 'VIMAX',
    'Total Bond Mkt Index Adm': 'VBTLX',
    'Tot Intl Stock Ix Admiral': 'VTIAX',
    'Total Intl Stock Ix Inv': 'VGTSX',
    'Small-Cap Index Fund Adm': 'VSMAX',
    '500 Index Fund Adm': 'VFIAX',
}


def amountPattern(name):
    """Returns a string regex pattern to capture a dollar amount.

    It includes two capture groups for use with getBeancountAmount.
    """
    return (
        '\(?'
         '(?P<' + name + 'sign>[-–] ?)?' # Handle two types of negative signs
         '\$(?P<' + name + '>[0-9,]+\.\d+)'
         '\)?'
    )


def getBeancountAmount(match, amount_pattern_name):
    a = amount.Amount(number.D(match.group(amount_pattern_name)), 'USD')
    if match.group(amount_pattern_name + 'sign'):
        a = -a
    return a


def pdfToText(filename):
    """Returns the text for the given PDF, creating a '.txt' file in the
    process that can be used to fix formatting issues.."""
    out_filename = filename + '.txt'
    if not os.path.exists(out_filename):
        print(f'writing: {out_filename}', file=sys.stderr)
        output = subprocess.check_output(['pdftotext', '-raw', filename, out_filename]).decode()
        if output:
            raise RuntimeError(output)
    with open(out_filename) as w:
        return w.read()


def removeNewlines(string):
    return string.replace("\n", " ")


def findAndConsume(pattern, parser, text):
    """findAndConsume calls parser for each match for string pattern against
    text, and returns the leftover text that was unmatched. The leftover
    is used to show to the user to debug parsing errors.
    """
    results = []
    remove_offset = 0
    for m in re.finditer(pattern, text, flags=re.DOTALL|re.MULTILINE):
        t = parser(m)
        results.append(t)

        text = text[:m.start()-remove_offset] + text[m.end()-remove_offset:]
        remove_offset += m.end() - m.start()

    return text, results


def checkUnconsumed(got_rows, want_rows, remaining_contents, filename):
    if got_rows == want_rows:
        return None
    # Remove empty lines for readability since the row regex doesn't
    # capture the newlines.
    cleaned = os.linesep.join(['\t' + s for s in remaining_contents.splitlines() if s])
    return ValueError(f'{filename}: got {got_rows} rows but expected {want_rows} rows according to dates that are present; some transaction types or sources may not be defined\n\nContents remaining after matching:\n{cleaned}')
    return rows


########
# For beancount printing


def postingLines(account_core, row, commodity, dst_account, sale=False, dst_account_suffix=''):
    if dst_account_suffix:
        dst_account_suffix = ':' + dst_account_suffix

    lines = []
    if row.shares != 0:
        if sale:
            price_string = f'{{}} @ {row.price}'
        else:
            price_string = f'{{{row.price}}}'
        lines.append(f'  Assets:{account_core}:{commodity}   {row.shares} {commodity} {price_string}')

    lines.append( f'  {dst_account}:{account_core}{dst_account_suffix}   {-row.amount}')
    return lines


def cgLine(account_core, commodity):
    return f'  Income:CapitalGains:{account_core}:{commodity}'


#########


MutualFundRow = collections.namedtuple('MutualFundRow', 'date fund txn_type shares price amount filename')


def parseMutualFundPDF(filename):
    contents = pdfToText(filename)

    date_p = r'^\s*(\d{1,2}/\d{1,2}/\d{4})\s+'
    want_rows = len(re.findall(date_p, contents, flags=re.DOTALL|re.MULTILINE))

    def new_row(match):
        date = parser.parse(match.group(1)).date()
        descr_txn_type = removeNewlines(match.group(2).strip())
        shares = decimal.Decimal(match.group("shares").replace(',', ''))
        if match.group("sharessign"):
            shares = -shares
        price = getBeancountAmount(match, 'price')
        amt = getBeancountAmount(match, 'amount')

        fund, txn_type = None, None
        for t in (
                'Dividend Received',
                'Buy',
                'Long-term capital gain',
                'Short-term capital gain',
                'Sell',
                'Conversion To',
                'Conversion From',
                'Transfer'):
            if descr_txn_type.endswith(t):
                fund = descr_txn_type[:-len(t) - 1]
                txn_type = t
                break
        if txn_type is None:
            raise ValueError(f'{filename}: cannot identify transaction type at end of: {descr_txn_type}')

        return MutualFundRow(date, fund, txn_type, shares, price, amt, filename)

    remaining_contents, rows = findAndConsume(
            # Date Fund Transaction type Shares transacted Share price Amount
            # 01/01/2021 Total Bond Mkt Index Adm Dividend Received 0.123 $10.00 $1.23
            date_p +
            r'(.*?)\s+'             # Fund and Transaction Type
            + r'(?P<sharessign>– )?(?P<shares>[0-9,]+\.\d+)\s+' # Number of shares
            + amountPattern('price') + '\s+' # Share price
            + amountPattern('amount') + r'$',   # Amount
            new_row, contents)
    got_rows = len(rows)
    err = checkUnconsumed(len(rows), want_rows, remaining_contents, filename)
    return rows


def printMutalFundBeancountRow(account_core, r):
    date = r.date.strftime('%Y-%m-%d')
    commodity = FUNDS.get(r.fund)
    if commodity is None:
        raise ValueError(f'cannot find commodity for fund {r.fund}: {r}')

    lines = [f'{date} * "{r.txn_type} - {r.fund}"']
    sale = False
    dst_account_prefix = None
    dst_account_suffix = ''

    if r.txn_type in ('Buy',):
        dst_account_prefix = 'Assets'
        dst_account_suffix = 'Cash'
    elif r.txn_type in ('Sell', 'Transfer'):
        dst_account_prefix = 'Assets:'
        dst_account_suffix = 'Cash'
        sale = True
    elif r.txn_type in ('Dividend Received',):
        dst_account_prefix = 'Income:Dividends'
    elif r.txn_type in ('Long-term capital gain',):
        dst_account_prefix = 'Income:CapitalGains'
        dst_account_suffix = 'Long'
    elif r.txn_type in ('Short-term capital gain',):
        dst_account_prefix = 'Income:CapitalGains'
        dst_account_suffix = 'Short'
    else:
        dst_account_prefix = 'FIXME'

    lines.extend(postingLines(account_core, r, commodity, dst_account_prefix, sale=sale, dst_account_suffix=dst_account_suffix))
    # The capital gains account absorbs rounding errors with shares and shares
    # prices, as well taking  gains, so always include it.
    lines.append(cgLine(account_core, commodity))
    print('\n'.join(lines)+'\n')


########


RetirementRow = collections.namedtuple('RetirementRow', MutualFundRow._fields + ('source',))


def multiLinePattern(s):
    return r'\s+'.join(s.split())


def parseRetirementPDF(filename):
    contents = pdfToText(filename)

    date_p = r'^\s*(?P<date>(\d{1,2}/\d{1,2}/\d{4}))\s+'
    want_rows = len(re.findall(date_p, contents, flags=re.DOTALL|re.MULTILINE))

    txn_types = (
        'Fee',
        'Miscellaneous Credits/Adjustment',
        'Source to Source/Fund to Fund Transfer Out',
        'Source to Source/Fund to Fund Transfer In',
        'Plan Contribution',
        'Plan Initiated TransferOut',
        'Plan Initiated TransferIn',
        'Dividends on Equity Investments',
        'Dividends on Equity',
        'Miscellaneous',
        'Fund to Fund Out',
        'Fund to Fund In',
    )
    txn_type_p = r'(?P<type>' + '|'.join(multiLinePattern(t) for t in txn_types) + ')'

    RETIREMENT_SOURCE_TO_ACCOUNT  = {
        r'EMPLOYER MATCHING': 'Match',
        r'BONUS PRE-TAX 401\(K\)': 'BonusPreTax',
        r'BONUS AFTER-TAX 401\(K\)': 'BonusAfterTax',
        r'PRE-TAX 401\(K\)': 'PreTax',
        r'AFTER-TAX 401\(K\)': 'AfterTax',
        r'\d+ ROTH IN PLAN CONVERSION': 'RothInPlanConv',
    }
    source_p = r'(?P<source>' + '|'.join(RETIREMENT_SOURCE_TO_ACCOUNT) + ')'

    def new_row(match):
        source = None
        for pattern, account in RETIREMENT_SOURCE_TO_ACCOUNT.items():
            if re.match(pattern, match.group('source')):
                source = account
                break
        if source is None:
            raise ValueError(f'could not find account for source {source!r}')

        amt = getBeancountAmount(match, 'amount')
        shares = decimal.Decimal(match.group("shares").replace(',', ''))
        if match.group("sharessign"):
            shares = -shares
        txn_type = removeNewlines(match.group('type'))
        if txn_type in (
                'Plan Initiated TransferOut',
                'Source to Source/Fund to Fund Transfer Out',
                'Fund to Fund Out',
                'Fee',
                ):
            # Vanguard doesn't print any sign for these. It's implied.
            amt = -amt
            shares = -shares

        return RetirementRow(
                date=parser.parse(match.group('date')).date(),
                txn_type=txn_type,
                source=source,
                fund=match.group('fund'),
                shares=shares,
                price=getBeancountAmount(match, 'price'),
                amount=amt,
                filename=filename,
        )

    remaining_contents, rows = findAndConsume(
            # Date Transaction Description Source Fund Name Quantity Price
            # 01/01/2021 Fee 2021 ROTH IN PLAN CONVERSION Target Retire 2050 Tr 0.001 $100.00 $0.1
            date_p
            + txn_type_p + r'\s+'
            + source_p + r'\s+'
            + r'(?P<fund>[^.]+)\s+'
            + r'(?P<sharessign>– )?(?P<shares>[0-9,]+\.\d+)\s+'
            + amountPattern('price') + r'\s+'
            + amountPattern('amount') + r'$',
            new_row,
            contents)
    got_rows = len(rows)
    err = checkUnconsumed(len(rows), want_rows, remaining_contents, filename)
    return rows


def printRetirementBeancountRow(account_core, r):
    date = r.date.strftime('%Y-%m-%d')
    commodity = FUNDS.get(r.fund)
    if commodity is None:
        raise ValueError(f'cannot find commodity for fund {r.fund}: {r}')

    lines = [f'{date} * "{r.txn_type} - {r.source} - {r.fund}"']
    dst_account_prefix = None
    sale = False

    if r.txn_type in (
            'Source to Source/Fund to Fund Transfer In',
            'Fund to Fund In',
            'Plan Initiated TransferIn',
            'Plan Contribution',
            'Miscellaneous',
        ):
        dst_account_prefix = 'Assets:Transfers'

    elif r.txn_type in (
            'Plan Initiated TransferOut',
            'Source to Source/Fund to Fund Transfer Out',
            'Fund to Fund Out',
            ):
        dst_account_prefix = 'Assets:Transfers'
        sale = True

    elif r.txn_type in ('Fee',):
        dst_account_prefix = 'Expenses:Fees'
        sale = True

    elif r.txn_type in ('Miscellaneous Credits/Adjustment',):
        dst_account_prefix = 'Income:Credits'

    elif r.txn_type in (
        'Dividends on Equity Investments',
        'Dividends on Equity',
        ):
        dst_account_prefix = 'Income:Dividends'

    lines.extend(postingLines(account_core + ':' + r.source, r, commodity, dst_account_prefix, sale=sale))
    # The capital gains account absorbs rounding errors with shares and shares
    # prices, as well taking  gains, so always include it.
    lines.append(cgLine(account_core, commodity))
    print('\n'.join(lines)+'\n')


########


ACCOUNT_TYPE_PARSERS = {
    'mutual_fund': (MutualFundRow, parseMutualFundPDF, printMutalFundBeancountRow),
    'retirement': (RetirementRow, parseRetirementPDF, printRetirementBeancountRow),
}


def newCSVPrinter(row_class):
    writer = csv.writer(sys.stdout)
    writer.writerow(row_class._fields)
    def csvPrinter(account_core, r):
        writer.writerow(r)
    return csvPrinter


if __name__ == '__main__':
    # To handle amounts with comma thousands separators
    locale.setlocale( locale.LC_ALL, 'en_US.UTF-8' )

    arg_parser = argparse.ArgumentParser(
            description=__doc__,
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog=f"""\
To parse PDFs for a retirement account (like a 401k) and output a Beancount
ledger, using files downloaded to Vanguard-Retirement/ as 1.pdf, 2.pdf, etc.:

% {sys.argv[0]} --account_type retirement --output beancount Vanguard-Retirement/*.pdf
""")
    acct_types = list(ACCOUNT_TYPE_PARSERS)
    def_acct_type = acct_types[0]
    arg_parser.add_argument(
            '--account_type', choices=acct_types,
            dest='account_type', default=def_acct_type,
            help=f'the type of account to process (default: {def_acct_type})')
    arg_parser.add_argument(
            '--output', choices=('csv', 'beancount'), default='csv',
            dest='output',
            help='the type of output to generate (default: csv)')
    arg_parser.add_argument(
            '--account_name', type=str, default='Vanguard:401k',
            dest='account_name',
            help=('build Beancount postings with this account; '
                   'appended to Assets:, Income. etc. (default: "Vanguard:401k")'))
    arg_parser.add_argument(
            'pdfs', metavar="PDF", type=str, nargs='+',
            help='a path to a PDF to parse')
    args = arg_parser.parse_args()

    result = ACCOUNT_TYPE_PARSERS.get(args.account_type)
    if result is None:
        raise ValueError(f'unknown account type {args.account_type!r}')
    row_class, parse_fn, beancount_printer = result

    if args.output == 'csv':
        printer = newCSVPrinter(row_class)
    else:
        printer = beancount_printer

    rows = []
    for path in args.pdfs:
        rows.extend(parse_fn(path))
    # Ensure additions are processed before reductions in a day, to avoid
    # reductions going below zero, which Beancount does not handle.
    rows.sort(key=lambda r: (r.date, -r.amount))

    for r in rows:
        printer(args.account_name, r)
