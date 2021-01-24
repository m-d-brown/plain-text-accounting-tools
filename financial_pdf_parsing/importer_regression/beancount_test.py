from os import path

from beancount.ingest import regression_pytest as regtest

from financial_pdf_parsing import beancount

@regtest.with_importer(beancount.BankOfAmericaCreditCard('Liabilities:BankOfAmerica:CashRewardsCC'))
@regtest.with_testdir(path.dirname(__file__))
class TestImporter(regtest.ImporterTestBase):
    pass

