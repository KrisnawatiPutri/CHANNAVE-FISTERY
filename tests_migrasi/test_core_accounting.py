"""Tes mesin akuntansi untuk distribusi tanpa UI Django HTML.

Run: python manage.py test tests_migrasi
"""
from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from accounting.models import (Account, BusinessProfile, JournalEntry, Product)
from accounting.services import (create_opening_stock, create_stock_movement,
                                 period_totals, stock_card, worksheet)
from accounting.exports import build_linked_workbook, NAME

D = Decimal


class MigratedCoreTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='uji', password='password-123456-test')
        self.cash = Account.objects.create(code='1120', name='Kas', category='ASSET',
            opening_balance=D('20000000'), normal_balance='D')
        self.stock = Account.objects.create(code='1150', name='Persediaan', category='ASSET',
            opening_balance=D('2000000'), normal_balance='D')
        self.equity = Account.objects.create(code='3100', name='Modal', category='EQUITY',
            normal_balance='C', opening_balance=D('22000000'))
        Account.objects.create(code='4110', name='Penjualan', category='REVENUE', normal_balance='C')
        Account.objects.create(code='5110', name='HPP', category='COGS', normal_balance='D')
        self.product = Product.objects.create(code='NILA', name='Ikan Nila', unit='kg', sale_price=D('30000'))
        create_opening_stock(self.product, D('100'), D('20000'), date(2026, 10, 1))

    def test_fifo_journal_and_balance(self):
        create_stock_movement(product=self.product, date_value=date(2026, 10, 2),
            reference='BELI-01', kind='IN', quantity=D('30'), unit_price=D('22000'),
            settlement_account=self.cash, description='Pembelian', user=self.user)
        out = create_stock_movement(product=self.product, date_value=date(2026, 10, 3),
            reference='JUAL-01', kind='OUT', quantity=D('110'), unit_price=D('30000'),
            settlement_account=self.cash, description='Penjualan', user=self.user)
        self.assertEqual(out.cost_amount, D('2220000'))
        self.assertEqual(stock_card(self.product)['qty'], D('20'))
        self.assertEqual(stock_card(self.product)['value'], D('440000'))
        self.assertEqual(period_totals()['difference'], 0)
        for entry in JournalEntry.objects.all():
            self.assertEqual(entry.total_debit, entry.total_credit)

    def test_stock_negative_rejected(self):
        before = JournalEntry.objects.count()
        with self.assertRaises(ValidationError):
            create_stock_movement(product=self.product, date_value=date(2026, 10, 2),
                reference='JUAL-BERLEBIH', kind='OUT', quantity=D('101'), unit_price=D('30000'),
                settlement_account=self.cash, description='Tidak cukup stok', user=self.user)
        self.assertEqual(JournalEntry.objects.count(), before)

    def test_worksheet_and_excel_still_linked(self):
        report = worksheet(date(2026, 10, 3))
        self.assertEqual(report['check_trial'], 0)
        self.assertEqual(report['check_adjusted'], 0)
        workbook = build_linked_workbook(date(2026, 10, 3))
        for expected in NAME.values():
            self.assertIn(expected, workbook.sheetnames)
        self.assertEqual(workbook['NERACA LAJUR'].title, 'NERACA LAJUR')
