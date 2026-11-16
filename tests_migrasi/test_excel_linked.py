"""Uji integrasi sumber data -> Excel -> laporan antarsheet.

Jalankan pada lingkungan Django: python manage.py test tests_migrasi.test_excel_linked
Pengujian ini memeriksa formula dan referensi, bukan memaksa openpyxl menjadi mesin hitung Excel.
"""
from datetime import date
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.test import TestCase
from accounting.models import Account, Product
from accounting.services import create_opening_stock, create_stock_movement
from accounting.exports import build_linked_workbook, NAME


class DynamicExcelIntegrationTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='tester_excel', password='pass-test-xl-2026')
        self.cash = Account.objects.create(code='1120', name='Kas', category='ASSET',
            normal_balance='D', opening_balance=Decimal('20000000'))
        Account.objects.create(code='1150', name='Persediaan', category='ASSET',
            normal_balance='D', opening_balance=Decimal('2000000'))
        Account.objects.create(code='3100', name='Modal', category='EQUITY',
            normal_balance='C', opening_balance=Decimal('22000000'))
        Account.objects.create(code='4110', name='Penjualan', category='REVENUE', normal_balance='C')
        Account.objects.create(code='5110', name='HPP', category='COGS', normal_balance='D')
        self.product = Product.objects.create(code='NILA', name='Nila', sale_price=Decimal('30000'), unit='kg')
        create_opening_stock(self.product, Decimal('100'), Decimal('20000'), date(2026, 10, 1))
        create_stock_movement(product=self.product, date_value=date(2026, 10, 2),
            reference='B-01', kind='IN', quantity=Decimal('30'), unit_price=Decimal('22000'),
            settlement_account=self.cash, description='Pembelian', user=self.user)
        create_stock_movement(product=self.product, date_value=date(2026, 10, 3),
            reference='J-01', kind='OUT', quantity=Decimal('110'), unit_price=Decimal('30000'),
            settlement_account=self.cash, description='Penjualan', user=self.user)

    def test_all_links_and_automatic_recalculation_setting(self):
        wb = build_linked_workbook(date(2026, 10, 3))
        self.assertEqual(wb.sheetnames[:2], ['RINGKASAN', 'PANDUAN'])
        self.assertTrue(set(NAME.values()).issubset(wb.sheetnames))
        self.assertEqual(wb.calculation.calcMode, 'auto')
        self.assertTrue(wb.calculation.fullCalcOnLoad)
        self.assertIn("'LABA RUGI'!", wb['RINGKASAN']['C9'].value)
        self.assertIn("'NERACA'!", wb['RINGKASAN']['F12'].value)
        self.assertIn("'NERACA LAJUR'!", wb['LABA RUGI']['D5'].value)
        self.assertIn("'PRODUK'!", wb['RINGKASAN']['F15'].value)
        self.assertIn('SUM(U7:V7)', wb['INVENTORY CARD']['N7'].value)
        self.assertIn('$I6', wb['INVENTORY CARD']['V7'].value)
        self.assertIn('PERIKSA', wb['RINGKASAN']['C29'].value)

    def test_stock_price_is_input_fifo_and_sales_journal_reference_fifo(self):
        wb = build_linked_workbook(date(2026, 10, 3))
        inventory = wb['INVENTORY CARD']
        original_price = inventory['I6'].value
        self.assertEqual(original_price, 22000)
        inventory['I6'] = 25000  # Ubah input pada Excel, bukan sumber database.
        self.assertIn('$I6', inventory['V7'].value)
        self.assertIn('V7', inventory['N7'].value)
        journal = wb['JURNAL UMUM']
        self.assertTrue(any("'INVENTORY CARD'!N7" in str(cell.value)
                            for row in journal.iter_rows(min_row=5, min_col=8, max_col=9)
                            for cell in row))
