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
# Allows for a space after the negative sign, like '- $65.71'.
AMOUNT = r'(?:-|- )?\$?[0-9,]+\.[0-9]{1,2}'

def compileRE(pattern):
    return re.compile(pattern, re.DOTALL|re.MULTILINE)

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

def RemoveNewlines(string):
    # TODO: Handle other newline characters too?
    return string.replace("\n", " ")


################################################################

AMERICAN_EXPRESS_CC_FILE_PATTERN =  r'^\d{4}-\d{2}-\d{2}\.pdf$'

def AmericanExpressCC(filename):
    """Reads the PDF at filename and returns contents.

    Returns (balance, closing_date, [Transaction]).
    """
    contents = PDFToText(filename)

    def _balance(match):
        b = pdf.ParseAmount(match.group(1))
        # TODO: Amount inversion should be done in the Beancount importer.
        # These parsers should return the raw values, which can be
        # interpreted as needed for specific accounts.
        return pdf.InvertAmount(b) # Treat as liability
    balance = reduceSingleMatch(
            r'\bNew Balance ('+AMOUNT+r')\b',
            _balance, contents)

    def _closing(match):
        return parser.parse(match.group(1)).date()
    closing_date = reduceSingleMatch(
            r'\bClosing Date (\d+/\d+/\d+)\b',
            _closing, contents)

    def _transaction(match):
        date = parser.parse(match.group(1)).date()
        date = pdf.AdjustDateForYearBoundary(date, closing_date)
        descr = RemoveNewlines(match.group(2))
        amt = pdf.ParseAmount(match.group(3))
        amt = pdf.InvertAmount(amt) # Treat as liability
        return Transaction(date, descr, amt)
    transactions = parseAll(
            # Example:
            #   01/23/21* PHOTOGPHY PLAN NEW YORK NY
            #   PHOTO.LY/URL
            #   $1.99
            #
            # '\s?' at the start handles ^L form feed characters that
            #  sometimes arise.
            r'^\s?(\d{2}/\d{2}/\d{2})\*? (.*?)\s('+AMOUNT+r')\b',
            _transaction, contents)

    return balance, closing_date, transactions


################################################################

BANK_OF_AMERICA_BANK_FILE_PATTERN =  r'^eStmt_.*\.pdf$'

def BankOfAmericaBank(filename):
    """Reads the PDF at filename and returns contents.

    Returns (account_no, balance, closing_date, [Transaction]).

    Raises ValueError if the file cannot be parsed.
    """
    contents = PDFToText(filename)
    # Ending balance on January 27, 2021 $209.01
    balance_pattern = r'\bEnding balance on ([a-zA-Z]+ \d+,? \d+) ('+AMOUNT+r')\b'

    account_no = reduceSingleMatch(
            # Account number: 0001 0002 0003
            r'Account number: (\d{4} \d{4} \d{4})',
            lambda m: m.group(1), contents)

    def _balance(match):
        return pdf.ParseAmount(match.group(2))
    balance = reduceSingleMatch(balance_pattern, _balance, contents)

    def _closing(match):
        return parser.parse(match.group(1)).date()
    closing_date = reduceSingleMatch(balance_pattern, _closing, contents)

    def _transaction(match):
        date = parser.parse(match.group(1)).date()
        date = pdf.AdjustDateForYearBoundary(date, closing_date)
        descr = RemoveNewlines(match.group(2))
        amt = pdf.ParseAmount(match.group(3))
        return Transaction(date, descr, amt)
    transactions = parseAll(
            # 01/04/21 Bank of America DES:CASHREWARD ID:DOE INDN:0000000123456789000000 CO
            # ID:234567890123 PPD
            # 85.51
            r'\b(\d{2}/\d{2}/\d{2}) (.*?)\s('+AMOUNT+r')\b',
            _transaction, contents)

    return account_no, balance, closing_date, transactions


################################################################

BANK_OF_AMERICA_CREDIT_CARD_FILE_PATTERN =  r'^eStmt_.*\.pdf$'

def BankOfAmericaCreditCard(filename):
    """Reads the PDF at filename and returns contents.

    Returns (account_no, balance, closing_date, [Transaction]).

    Raises ValueError if the file cannot be parsed.
    """
    contents = PDFToText(filename)

    account_no = reduceSingleMatch(
            # Account Number: 1234 5678 9012 3456
            r'Account Number: (\d{4} \d{4} \d{4} \d{4})',
            lambda m: m.group(1), contents)
 
    def _balance(match):
        b = pdf.ParseAmount(match.group(1))
        # TODO: Amount inversion should be done in the Beancount importer.
        # These parsers should return the raw values, which can be
        # interpreted as needed for specific accounts.
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
        descr = match.group(2).replace('\n', ' ')
        amt = pdf.ParseAmount(match.group(3))
        amt = pdf.InvertAmount(amt) # Treat as liability
        return Transaction(date, descr, amt)
    transactions = parseAll(
            # Example:  12/05 12/07 WHOLE FOODS #1234 SF CA 8538 3456 251.49
            r'\b(\d{2}/\d{2}) \d{2}/\d{2} (.*?)\s\d+ \d+ ('+AMOUNT+r')\b',
            _transaction, contents)

    return account_no, balance, closing_date, transactions


################################################################

CAPITAL_ONE_BANK_FILE_PATTERN =  r'^statement\.pdf$'

# num is a string.
CapitalOneBankAccount = collections.namedtuple('CapitalOneBankAccount',
        'num balance closing_date transactions')

def CapitalOneBank(filename):
    """Reads the PDF at filename and returns contents.

    Returns a list of CapitalOneBankAccount.
    """
    contents = PDFToText(filename)

    overall = compileRE(
            r'\w+ \d+ - (?P<closing>\w+ \d+, \d+)\b').search(contents)
    if overall is None:
        raise ValueError(f'could not find closing date')
    closing_date = parser.parse(overall.group('closing')).date()

    section_expr = compileRE(
            r'^.?(?:\w| )+ - (?P<acct_num>\d+)\b'
            r'.*?'
            r'(?:\w+ \d+) Opening Balance '+AMOUNT+r'\b'
            r'(?P<transactions>.*?)\b'
            r'(?:\w+ \d+) Closing Balance (?P<balance>'+AMOUNT+r')\b')

    accounts = []
    for section in section_expr.finditer(contents):
        balance = pdf.ParseAmount(section.group('balance'))

        # Captures the closing_date variable so defined in the loop
        def _transaction(match):
            date = parser.parse(match.group(1)).date()
            date = pdf.AdjustDateForYearBoundary(date, closing_date)
            descr = match.group(2)
            descr = RemoveNewlines(descr)
            amt_sign = match.group(3)
            amt = pdf.ParseAmount(match.group(4))
            if amt_sign == '-':
                amt = pdf.InvertAmount(amt)
            return Transaction(date, descr, amt)
        # Example:
        #   Jan 6 Zelle money sent to GOOD FRIEND Debit - $3.00 $2.00
        #
        # '(?:\n[^\n]+?){,2}?' is to avoid matching too many lines.
        pattern = (r'^(\w+ \d+)\s+([^\n]+?(?:\n[^\n]+?){,2}?)\s+' +
                   r'(?:Debit|Credit) ' +
                   r'(\+|-) ('+AMOUNT+r') '+AMOUNT)
        transactions = parseAll(
                pattern,
                _transaction, section.group('transactions'))

        accounts.append(CapitalOneBankAccount(
            section.group('acct_num'), balance,
            closing_date, transactions))

    return accounts


################################################################

CAPITAL_ONE_CREDIT_CARD_FILE_PATTERN =  r'^Statement_\d+_\d+\.pdf$'

def CapitalOneCreditCard(filename):
    """Reads the PDF at filename and returns contents.

    Returns (balance, closing_date, [Transaction]).
    """
    contents = PDFToText(filename)

    def _balance(match):
        b = pdf.ParseAmount(match.group(1))
        return pdf.InvertAmount(b) # Treat as liability
    balance = reduceSingleMatch(
            r'\bNew Balance = +('+AMOUNT+r')\b',
            _balance, contents)

    def _closing(match):
        return parser.parse(match.group(1)).date()
    closing_date = reduceSingleMatch(
            # Dec. 23, 2020 - Jan. 22, 2021 | 31 days in Billing Cycle 
            r'- ([a-zA-Z0-9,. ]+?) \| \d+ days? in Billing Cycle\b',
            _closing, contents)

    def _transaction(match):
        date = parser.parse(match.group(1)).date()
        date = pdf.AdjustDateForYearBoundary(date, closing_date)
        descr = match.group(2)
        descr = RemoveNewlines(descr)
        amt = pdf.ParseAmount(match.group(3))
        amt = pdf.InvertAmount(amt) # Treat as liability
        return Transaction(date, descr, amt)
    transactions = parseAll(
            # Dec 30 NYTimes*NYTimes 800-698-4637NY $10.00 
            #
            # Or three lines:
            # Mar 2 AMZN Mktp
            # CA*AB1234567AMAZON.CAWA
            # $46.56
            r'\b([a-zA-z]{3} \d{1,2}) (.*?)\s+('+AMOUNT+r')$',
            _transaction, contents)

    return balance, closing_date, transactions


################################################################

CHASE_CC_FILE_PATTERN = r'^\d{8}-statements-\d{4}-\.pdf$'

def ChaseCC(filename, rewards_currency):
    """Reads the PDF at filename and returns contents.

    Returns (balance, rewards_balance, closing_date, [Transaction]).
    """
    contents = PDFToText(filename)

    def _balance(match):
        b = pdf.ParseAmount(match.group(1))
        return pdf.InvertAmount(b) # Treat as liability
    balance = reduceSingleMatch(
            r'\bNew Balance +('+AMOUNT+r')\b',
            _balance, contents)

    def _rewards_balance(match):
        return pdf.ParseAmount(match.group(1), currency=rewards_currency)
    rewards_balance = reduceSingleMatch(
            r'Total points available for\nredemption ([0-9,]+)',
            _rewards_balance, contents)

    def _closing(match):
        return parser.parse(match.group(1)).date()
    closing_date = reduceSingleMatch(
            #   Opening/Closing Date 12/05/20 - 01/04/21
            r'\bOpening/Closing Date [0-9/]+ - ([0-9/]+)\b',
            _closing, contents)

    def _transaction(match):
        date = parser.parse(match.group(1)).date()
        date = pdf.AdjustDateForYearBoundary(date, closing_date)
        descr = RemoveNewlines(match.group(2))
        amt = pdf.ParseAmount(match.group(3))
        amt = pdf.InvertAmount(amt) # Treat as liability
        order_no = match.group(4)
        if order_no:
            descr += '. ' + order_no
        return Transaction(date, descr, amt)
    transactions = parseAll(
            # 01/01 AUTOMATIC PAYMENT - THANK YOU -10.99
            r'\s(\d{2}/\d{2}) (.*?) ('+AMOUNT+r')$(?:(Order Number [1-9-]+))?\b',
            _transaction, contents)

    # TODO: Also handle reward transactions, which have an extra rewards
    #       field at the end
    # 12/20 AMAZON MARKETPLACE AMZN.COM/BILLWA 32.43 3,243

    return balance, rewards_balance, closing_date, transactions
