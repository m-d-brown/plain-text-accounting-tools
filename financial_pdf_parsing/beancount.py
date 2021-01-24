import re
import os

from financial_pdf_parsing import bank_of_america_credit_card

from beancount.core import data
from beancount.core import flags
from beancount.ingest import importer

class BankOfAmericaCreditCard(importer.ImporterProtocol):

    def __init__(self, account):
        """account is the string account name to which one side of
        transactions should be recorded. Should be a liability account."""
        self.account = account

    def identify(self, f):
        return re.match(bank_of_america_credit_card.FILE_PATTERN, os.path.basename(f.name))

    def file_account(self, f):
        return self.account

    # TODO: Worth importing these too?
    #def file_name(self, f):
    #def file_date(self, f):

    def extract(self, f):
        transactions = bank_of_america_credit_card.Read(f.name, self.account)
        return data.sorted(transactions)
