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

    # TODO: Worth handling these too?
    #def file_name(self, f):
    #def file_date(self, f):

    def extract(self, f, existing_entries=None):
        balance, closing_date, transactions = parsers.AmericanExpressCC(f.name)
        l = BeancountLedgerItems(f.name)
        l.AddTransactions(self.account, transactions)
        l.AddBalance(self.account, closing_date, balance)
        return l.SortedItems()


class BankOfAmericaBank(importer.ImporterProtocol):

    def __init__(self, account, account_no):
        """Creates an importer for a Bank of America bank.

        account is the string account name to which one side of
        transactions should be recorded. Should be a liability account.

        account_no is the string number of the account, formatted like
        '1234 5678 9012 3456'. It's used to ensure only files belonging
        to this account are imported.
        """
        self.account = account
        self.account_no = account_no

    def identify(self, f):
        if not re.match(parsers.BANK_OF_AMERICA_BANK_FILE_PATTERN, os.path.basename(f.name)):
            return False
        try:
            num, _, _, _ = parsers.BankOfAmericaBank(f.name)
        except ValueError:
            return False
        return num == self.account_no

    def file_account(self, f):
        return self.account

    # TODO: Worth handling these too?
    #def file_name(self, f):
    #def file_date(self, f):

    def extract(self, f, existing_entries=None):
        _, balance, closing_date, transactions = parsers.BankOfAmericaBank(f.name)
        l = BeancountLedgerItems(f.name)
        l.AddTransactions(self.account, transactions)
        l.AddBalance(self.account, closing_date, balance)
        return l.SortedItems()


class BankOfAmericaCreditCard(importer.ImporterProtocol):

    def __init__(self, account, account_numbers):
        """Creates an importer for a Bank of America credit card.

        account is the string account name to which one side of
        transactions should be recorded. Should be a liability account.

        account_numbers is a list of the string numbers of the account,
        formatted like '1234 5678 9012 3456'. It's used to ensure only files
        belonging to this account are imported.
        """
        self.account = account
        if isinstance(account_numbers, str):
            account_numbers = [account_numbers]
        self.account_numbers = set(account_numbers)

    def identify(self, f):
        if not re.match(parsers.BANK_OF_AMERICA_CREDIT_CARD_FILE_PATTERN, os.path.basename(f.name)):
            return False
        try:
            num, _, _, _ = parsers.BankOfAmericaCreditCard(f.name)
        except ValueError:
            return False
        return num in self.account_numbers

    def file_account(self, f):
        return self.account

    # TODO: Worth handling these too?
    #def file_name(self, f):
    #def file_date(self, f):

    def extract(self, f, existing_entries=None):
        _, balance, closing_date, transactions = parsers.BankOfAmericaCreditCard(f.name)
        l = BeancountLedgerItems(f.name)
        l.AddTransactions(self.account, transactions)
        l.AddBalance(self.account, closing_date, balance)
        return l.SortedItems()


class CapitalOneBank(importer.ImporterProtocol):

    def __init__(self, file_account, num_to_account,
            identify_pattern=parsers.CAPITAL_ONE_BANK_FILE_PATTERN,
            skip_accounts=None):
        """Initializer.

        file_account is the string account under which to file source PDFs.

        num_account is a dict from account number string to account string.
o
        """
        self.file_account_value = file_account
        self.num_to_account = num_to_account
        self.identify_pattern = identify_pattern
        self.skip_accounts = skip_accounts

    def identify(self, f):
        return re.match(self.identify_pattern, os.path.basename(f.name))

    def file_account(self, f):
        return self.file_account_value

    # TODO: Worth handling these too?
    #def file_name(self, f):
    #def file_date(self, f):

    def extract(self, f, existing_entries=None):
        l = BeancountLedgerItems(f.name)
        accounts = parsers.CapitalOneBank(f.name)
        for acct_row in accounts:
            if self.skip_accounts is not None and acct_row.num in self.skip_accounts:
                continue
            try:
                acct = self.num_to_account[acct_row.num]
            except KeyError as e:
                raise KeyError(f'no account defined for {acct_row.num}: {e}')
            l.AddTransactions(acct, acct_row.transactions)
            l.AddBalance(acct, acct_row.closing_date, acct_row.balance)
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

    # TODO: Worth handling these too?
    #def file_name(self, f):
    #def file_date(self, f):

    def extract(self, f, existing_entries=None):
        balance, closing_date, transactions = parsers.CapitalOneCreditCard(f.name)
        l = BeancountLedgerItems(f.name)
        l.AddTransactions(self.account, transactions)
        l.AddBalance(self.account, closing_date, balance)
        return l.SortedItems()


class ChaseCC(importer.ImporterProtocol):

    def __init__(self, account, rewards_account, rewards_currency):
        """account is the string account name to which one side of
        transactions should be recorded. Should be a liability account.

        rewards_accounts is the account to track rewards, as an Asset account
        in the currency given by rewards_currency.
        """
        self.account = account
        self.rewards_account = rewards_account
        self.rewards_currency = rewards_currency

    def identify(self, f):
        return re.match(parsers.CHASE_CC_FILE_PATTERN, os.path.basename(f.name))

    def file_account(self, f):
        return self.account

    # TODO: Worth handling these too?
    #def file_name(self, f):
    #def file_date(self, f):

    def extract(self, f, existing_entries=None):
        balance, rewards_balance, closing_date, transactions = parsers.ChaseCC(f.name, self.rewards_currency)
        l = BeancountLedgerItems(f.name)
        l.AddTransactions(self.account, transactions)
        l.AddBalance(self.account, closing_date, balance)
        l.AddBalance(self.rewards_account, closing_date, rewards_balance)
        return l.SortedItems()
