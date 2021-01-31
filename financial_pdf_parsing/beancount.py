"""beancount provides Beancount importers that rely on the parsers in the
parsers module."""

import datetime
import re
import os

from financial_pdf_parsing import parsers

from beancount.core import data
from beancount.core import flags
from beancount.ingest import importer

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

    def SortedItems(self):
        return data.sorted(self.items)


class AmericanExpressCC(importer.ImporterProtocol):

    def __init__(self, account):
        """account is the string account name to which one side of
        transactions should be recorded. Should be a liability account."""
        self.account = account

    def identify(self, f):
        return re.match(parsers.AMERICAN_EXPRESS_CC_FILE_PATTERN, os.path.basename(f.name))

    def file_account(self, f):
        return self.account

    # TODO: Worth importing these too?
    #def file_name(self, f):
    #def file_date(self, f):

    def extract(self, f):
        balance, closing_date, transactions = parsers.AmericanExpressCC(f.name)
        l = BeancountLedgerItems(f.name)
        l.AddTransactions(self.account, transactions)
        l.AddBalance(self.account, closing_date, balance)
        return l.SortedItems()


class BankOfAmericaBank(importer.ImporterProtocol):

    def __init__(self, account):
        """account is the string account name to which one side of
        transactions should be recorded. Should be a liability account."""
        self.account = account

    def identify(self, f):
        return re.match(parsers.BANK_OF_AMERICA_BANK_FILE_PATTERN, os.path.basename(f.name))

    def file_account(self, f):
        return self.account

    # TODO: Worth importing these too?
    #def file_name(self, f):
    #def file_date(self, f):

    def extract(self, f):
        balance, closing_date, transactions = parsers.BankOfAmericaBank(f.name)
        l = BeancountLedgerItems(f.name)
        l.AddTransactions(self.account, transactions)
        l.AddBalance(self.account, closing_date, balance)
        return l.SortedItems()


class BankOfAmericaCreditCard(importer.ImporterProtocol):

    def __init__(self, account):
        """account is the string account name to which one side of
        transactions should be recorded. Should be a liability account."""
        self.account = account

    def identify(self, f):
        return re.match(parsers.BANK_OF_AMERICA_CREDIT_CARD_FILE_PATTERN, os.path.basename(f.name))

    def file_account(self, f):
        return self.account

    # TODO: Worth importing these too?
    #def file_name(self, f):
    #def file_date(self, f):

    def extract(self, f):
        balance, closing_date, transactions = parsers.BankOfAmericaCreditCard(f.name)
        l = BeancountLedgerItems(f.name)
        l.AddTransactions(self.account, transactions)
        l.AddBalance(self.account, closing_date, balance)
        return l.SortedItems()


class CapitalOneCreditCard(importer.ImporterProtocol):

    def __init__(self, account):
        """account is the string account name to which one side of
        transactions should be recorded. Should be a liability account."""
        self.account = account

    def identify(self, f):
        return re.match(parsers.CAPITAL_ONE_CREDIT_CARD_FILE_PATTERN, os.path.basename(f.name))

    def file_account(self, f):
        return self.account

    # TODO: Worth importing these too?
    #def file_name(self, f):
    #def file_date(self, f):

    def extract(self, f):
        balance, closing_date, transactions = parsers.CapitalOneCreditCard(f.name)
        l = BeancountLedgerItems(f.name)
        l.AddTransactions(self.account, transactions)
        l.AddBalance(self.account, closing_date, balance)
        return l.SortedItems()


class ChaseCC(importer.ImporterProtocol):

    def __init__(self, account):
        """account is the string account name to which one side of
        transactions should be recorded. Should be a liability account."""
        self.account = account

    def identify(self, f):
        return re.match(parsers.CHASE_CC_FILE_PATTERN, os.path.basename(f.name))

    def file_account(self, f):
        return self.account

    # TODO: Worth importing these too?
    #def file_name(self, f):
    #def file_date(self, f):

    def extract(self, f):
        balance, closing_date, transactions = parsers.ChaseCC(f.name)
        l = BeancountLedgerItems(f.name)
        l.AddTransactions(self.account, transactions)
        l.AddBalance(self.account, closing_date, balance)
        return l.SortedItems()
