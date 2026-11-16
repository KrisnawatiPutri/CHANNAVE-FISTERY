"""Format angka Indonesia, nilai uang disimpan di database sebagai Decimal."""
from datetime import date
from decimal import Decimal


def number(value, decimals=2):
    if value is None:
        return '–'
    formatted = f'{Decimal(str(value)):,.{decimals}f}'
    return formatted.replace(',', 'X').replace('.', ',').replace('X', '.')


def rupiah(value):
    return f'Rp {number(value)}'


def tanggal(value):
    return value.strftime('%d-%m-%Y') if isinstance(value, date) else str(value or '')


def iso(value):
    return value.isoformat() if value else ''


def maybe_date(value, fallback=None):
    if not value:
        return fallback
    return date.fromisoformat(str(value))
