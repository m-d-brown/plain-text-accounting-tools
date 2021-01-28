import io
import subprocess

# TODO: use internal types for balances so that the core parsing doesn't
#       need to depend on Beancount and so is fully generic?
from beancount.core import amount
from beancount.core import number

NEGATIVE_ONE = number.D("-1")

# TODO: Move this to a Beancount-specific common library.
def InvertAmount(amt):
    return amount.mul(amt, NEGATIVE_ONE)

def PDFToText(filename):
    """Returns the text for the given PDF."""
    return subprocess.check_output(['pdftotext', '-raw', filename, '-']).decode()

def StringIO(filename):
    """Returns a StringIO of the PDF contents for the given file."""
    return io.StringIO(PDFToText(filename))

def ParseAmount(s):
    """Converts a string amount to an amount.Amount, in USD."""
    invert = False
    if s[0] == '(' and s[-1] == ')':
        s = s[1:-1]
        invert = True
    if s.startswith('-$'):
        s = s[2:]
        invert = True
    if s[0] == "$":
        s = s[1:]
    a = amount.Amount(number.D(s), 'USD')
    if invert:
        a = InvertAmount(a)
    return a

def AdjustDateForYearBoundary(to_adjust, latest_date):
    """Handles end-of-year boundaries for dates that are parsed from strings
    that don't include the year. latest_date is the latest date known from
    processing an input. If to_adjust is after latest_date, to_adjust is
    moved back a year.

    For example, an input may have dates 12/31 and 01/01. This crosses the
    year boundary so 01/01 is year X and 12/31 is year X-1.
    """
    if to_adjust < latest_date:
        return to_adjust
    return to_adjust.replace(year=to_adjust.year-1)

