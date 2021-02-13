from os import path

from beancount.ingest import regression_pytest as regtest

from financial_pdf_parsing import beancount

@regtest.with_importer(beancount.AmericanExpressCC('Liabilities:Amex:BlueCash'))
@regtest.with_testdir(path.join(path.dirname(__file__), 'american_express_cc'))
class TestImporterAmexCC(regtest.ImporterTestBase):
    pass

@regtest.with_importer(beancount.BankOfAmericaBank('Liabilities:BankOfAmerica:Checking', '0001 0002 0003'))
@regtest.with_testdir(path.join(path.dirname(__file__), 'bank_of_america_bank'))
class TestImporterBoABank(regtest.ImporterTestBase):
    pass

@regtest.with_importer(beancount.BankOfAmericaCreditCard('Liabilities:BankOfAmerica:CashRewardsCC', '1234 5678 9012 3456'))
@regtest.with_testdir(path.join(path.dirname(__file__), 'bank_of_america_credit_card'))
class TestImporterBoACC(regtest.ImporterTestBase):
    pass

@regtest.with_importer(beancount.CapitalOneBank(
    'Assets:CapitalOne:Checking',
    {'111117777': 'Assets:CapitalOne:Checking',
     '11111119999': 'Assets:CapitalOne:Savings'}))
@regtest.with_testdir(path.join(path.dirname(__file__), 'capital_one_bank'))
class TestImporterCapitalOneBank(regtest.ImporterTestBase):
    pass

@regtest.with_importer(beancount.CapitalOneCreditCard('Liabilities:CapitalOne:CC'))
@regtest.with_testdir(path.join(path.dirname(__file__), 'capital_one_credit_card'))
class TestImporterCapitalOneCC(regtest.ImporterTestBase):
    pass

@regtest.with_importer(beancount.ChaseCC('Liabilities:Chase:CC'))
@regtest.with_testdir(path.join(path.dirname(__file__), 'chase_cc'))
class TestImporterChaseCC(regtest.ImporterTestBase):
    pass

