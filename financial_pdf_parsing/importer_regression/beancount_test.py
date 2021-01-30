from os import path

from beancount.ingest import regression_pytest as regtest

from financial_pdf_parsing import beancount

@regtest.with_importer(beancount.BankOfAmericaCreditCard('Liabilities:BankOfAmerica:CashRewardsCC'))
@regtest.with_testdir(path.join(path.dirname(__file__), 'bank_of_america_credit_card'))
class TestImporter(regtest.ImporterTestBase):
    pass

@regtest.with_importer(beancount.CapitalOneCreditCard('Liabilities:CapitalOne:CC'))
@regtest.with_testdir(path.join(path.dirname(__file__), 'capital_one_credit_card'))
class TestImporter(regtest.ImporterTestBase):
    pass

@regtest.with_importer(beancount.ChaseCC('Liabilities:Chase:CC'))
@regtest.with_testdir(path.join(path.dirname(__file__), 'chase_cc'))
class TestImporter(regtest.ImporterTestBase):
    pass

