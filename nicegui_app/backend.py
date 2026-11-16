"""Jembatan ORM Django lama, tanpa menjalankan server/template Django.

Python process harus dijalankan dari root proyek (python -m nicegui_app.main).
"""
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
from django.apps import apps

if not apps.ready:
    django.setup()

from accounting.models import (Account, BusinessProfile, InventoryLayer, InventoryMovement,
                               JournalEntry, JournalLine, Party, Product, ZERO)
from accounting.forms import (AccountForm, JournalEntryForm, JournalLineFormSet,
                              MovementForm, PartyForm, ProductForm, ProfileForm)
from accounting.services import (create_opening_stock, create_stock_movement,
                                 ledger, period_totals, report_balances,
                                 stock_card, subsidiary, worksheet)
from accounting.exports import EXPORTS, NAME, build_linked_workbook

__all__ = ['Account', 'BusinessProfile', 'InventoryLayer', 'InventoryMovement',
           'JournalEntry', 'JournalLine', 'Party', 'Product', 'ZERO',
           'AccountForm', 'JournalEntryForm', 'JournalLineFormSet',
           'MovementForm', 'PartyForm', 'ProductForm', 'ProfileForm',
           'create_opening_stock', 'create_stock_movement', 'ledger', 'period_totals',
           'report_balances', 'stock_card', 'subsidiary', 'worksheet',
           'EXPORTS', 'NAME', 'build_linked_workbook']
