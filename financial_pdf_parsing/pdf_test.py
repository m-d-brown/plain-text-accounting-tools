import datetime
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


class TestAdjustDateForYearBoundary(unittest.TestCase):
    def testNoAdjustment(self):
        dt = datetime.datetime
        self.assertEqual(
                pdf.AdjustDateForYearBoundary(
                    dt(2021, 11, 1),
                    dt(2021, 12, 1)),
                dt(2021, 11, 1),
                "month earlier")
        self.assertEqual(
                pdf.AdjustDateForYearBoundary(
                    dt(2021, 11, 1),
                    dt(2022, 12, 1)),
                dt(2021, 11, 1),
                "year earlier")
        self.assertEqual(
                pdf.AdjustDateForYearBoundary(
                    dt(2021, 12, 1),
                    dt(2022, 1, 1)),
                dt(2021, 12, 1),
                "month earlier, over year boundary")

    def testNeedsAdjustment(self):
        dt = datetime.datetime
        self.assertEqual(
                pdf.AdjustDateForYearBoundary(
                    dt(2021, 12, 1),
                    dt(2021, 1, 5)),
                dt(2020, 12, 1),
                "year improperly assumed to be 2021")
        self.assertEqual(
                pdf.AdjustDateForYearBoundary(
                    dt(2022, 1, 6),
                    dt(2021, 1, 31)),
                dt(2021, 1, 6),
                "year improperly assumed to be 2022")
        self.assertEqual(
                pdf.AdjustDateForYearBoundary(
                    dt(2023, 1, 6),
                    dt(2021, 1, 31)),
                dt(2021, 1, 6),
                "year improperly assumed to be 2023")
