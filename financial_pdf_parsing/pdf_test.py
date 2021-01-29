import unittest
from financial_pdf_parsing import pdf

from beancount.core import amount
from beancount.core import number

def usd(x):
    return amount.Amount(number.D(x), 'USD')

class TestParseAmount(unittest.TestCase):
    def testBasic(self):
        self.assertEqual(pdf.ParseAmount("1.23"), usd("1.23"))
        self.assertEqual(pdf.ParseAmount("$1.23"), usd("1.23"))

    def testNegative(self):
        self.assertEqual(pdf.ParseAmount("-$1.23"), usd("-1.23"))

    def testNegativeWithSpace(self):
        self.assertEqual(pdf.ParseAmount("- $1.23"), usd("-1.23"))
