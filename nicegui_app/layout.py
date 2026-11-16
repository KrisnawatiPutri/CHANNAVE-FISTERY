"""Komponen visual Channave Fishery: NiceGUI murni dari Python.

Tidak menggunakan template HTML, berkas CSS, atau berkas JavaScript aplikasi.
Seluruh alur Django ORM tetap dikerjakan di halaman/worker, bukan komponen UI.
"""
from contextlib import contextmanager
from django.utils import timezone

from nicegui import ui
from .branding import (ACCENT, APP_CATEGORY, APP_NAME, APP_SHORT_NAME,
                       APP_TAGLINE, NEGATIVE, POSITIVE, PRIMARY, SECONDARY)

NAV_GROUPS = [
    ('OVERVIEW', [('/dashboard', 'Dashboard', 'space_dashboard')]),
    ('OPERASIONAL', [
        ('/journal', 'Jurnal Umum', 'receipt_long'),
        ('/adjustments', 'Jurnal Penyesuaian', 'edit_document'),
        ('/products', 'Produk Perikanan', 'set_meal'),
        ('/inventory', 'Kartu Persediaan FIFO', 'inventory_2'),
    ]),
    ('AKUNTANSI & LAPORAN', [
        ('/ledger', 'Buku Besar', 'menu_book'),
        ('/subsidiary', 'Buku Besar Pembantu', 'summarize'),
        ('/trial-balance', 'Neraca Saldo', 'balance'),
        ('/worksheet', 'Neraca Lajur', 'view_column'),
        ('/income', 'Laba Rugi', 'trending_up'),
        ('/balance', 'Neraca', 'account_balance'),
    ]),
    ('SISTEM', [('/settings', 'Pengaturan Usaha', 'tune')]),
]
NAV = [link for _, links in NAV_GROUPS for link in links]

CARD = 'bg-white rounded-2xl border border-slate-200/80 shadow-sm'
INPUT = 'rounded-xl bg-white'
MUTED = 'text-slate-500'


def apply_theme():
    ui.colors(primary=PRIMARY, secondary=SECONDARY, accent=ACCENT,
              positive=POSITIVE, negative=NEGATIVE)


def brand_mark(size='md'):
    """Ikon merek tanpa file aset eksternal."""
    with ui.element('div').classes('h-11 w-11 rounded-2xl bg-gradient-to-br from-teal-400 to-cyan-700 '
                                   'shadow-md shadow-cyan-950/20 flex items-center justify-center shrink-0'):
        ui.icon('set_meal', size=size).classes('text-white')


def _active_link(label, title):
    return label == title or (title == 'Master Persediaan' and label == 'Produk Perikanan') or (
        title in ('Laporan Laba Rugi', 'Laporan Neraca') and label == title.replace('Laporan ', '')
    )


@contextmanager
def shell(title, subtitle='Pencatatan usaha perikanan yang rapi dan terintegrasi'):
    apply_theme()
    drawer = ui.left_drawer(value=True).props('show-if-above bordered').classes(
        'bg-slate-950 text-white w-72')
    with drawer:
        with ui.column().classes('w-full h-full gap-0 px-4 py-6'):
            with ui.row().classes('w-full items-center gap-3 px-2 mb-2'):
                brand_mark('md')
                with ui.column().classes('gap-0'):
                    ui.label(APP_SHORT_NAME).classes('font-extrabold tracking-tight text-xl text-white')
                    ui.label(APP_CATEGORY).classes('text-[10px] tracking-[0.25em] text-teal-300 font-bold')
            ui.label('Kelola stok. Jaga arus kas. Tumbuh bersama.').classes(
                'text-xs text-slate-400 leading-relaxed px-2 mb-5 mt-1')
            with ui.card().classes('w-full rounded-2xl bg-cyan-950/80 border border-cyan-900/70 '
                                   'shadow-none p-3 mb-5'):
                with ui.row().classes('items-center gap-3'):
                    ui.icon('verified', size='md').classes('text-teal-300')
                    with ui.column().classes('gap-0'):
                        ui.label('Sistem terhubung').classes('text-white text-xs font-bold')
                        ui.label('Keuangan & FIFO').classes('text-cyan-200 text-[11px]')
            with ui.column().classes('w-full gap-1 grow'):
                for group, links in NAV_GROUPS:
                    ui.label(group).classes('text-[10px] font-bold tracking-[0.19em] text-slate-500 '
                                             'px-3 pt-4 pb-1')
                    for url, label, icon in links:
                        active = _active_link(label, title)
                        styling = ('bg-teal-500/15 text-white ring-1 ring-teal-400/20' if active else
                                   'text-slate-300 hover:bg-slate-800 hover:text-white')
                        with ui.link(target=url).classes('no-underline w-full rounded-xl '
                                                        'transition-all duration-150 ' + styling):
                            with ui.row().classes('w-full items-center gap-3 px-3 py-2.5'):
                                ui.icon(icon, size='sm').classes('text-teal-300' if active else 'text-slate-400')
                                ui.label(label).classes('text-[13px] font-semibold')
                                if active:
                                    ui.space()
                                    ui.icon('circle', size='8px').classes('text-teal-400')
            with ui.row().classes('w-full items-center gap-2 px-2 pt-5'):
                ui.icon('lock_outline', size='xs').classes('text-teal-300')
                ui.label('Channave Fishery · NiceGUI').classes('text-[11px] text-slate-500')

    with ui.header().classes('bg-white/95 text-slate-800 items-center px-3 md:px-6 '
                             'border-b border-slate-100 shadow-none min-h-16'):
        ui.button(icon='menu', on_click=drawer.toggle).props('flat round dense').classes('text-slate-700')
        with ui.column().classes('gap-0 ml-1'):
            ui.label('WORKSPACE PERIKANAN').classes('text-[10px] font-semibold tracking-[0.2em] text-teal-700')
            ui.label(title).classes('text-sm md:text-base font-extrabold tracking-tight text-slate-900')
        ui.space()
        ui.label(timezone.localdate().strftime('%d/%m/%Y')).classes('hidden md:block text-xs text-slate-500 mr-3')
        ui.button(icon='add_circle_outline', on_click=lambda: ui.navigate.to('/journal/new')).props(
            'flat round dense').classes('text-teal-700').tooltip('Tambah jurnal')
        ui.button(icon='logout', on_click=logout).props('flat round dense').classes(
            'text-slate-600').tooltip('Keluar akun')

    with ui.column().classes('w-full min-h-screen bg-slate-50/80'):
        with ui.column().classes('w-full max-w-screen-2xl mx-auto px-4 md:px-8 py-6 gap-5'):
            with ui.card().classes('w-full border-0 shadow-md shadow-cyan-900/10 rounded-3xl '
                                   'bg-gradient-to-br from-slate-950 via-cyan-950 to-teal-800 text-white '
                                   'p-5 md:p-8 overflow-hidden'):
                with ui.row().classes('w-full items-center justify-between flex-wrap gap-4'):
                    with ui.column().classes('gap-2 max-w-4xl'):
                        with ui.row().classes('items-center gap-2'):
                            ui.icon('waves', size='xs').classes('text-teal-300')
                            ui.label(f'{APP_NAME.upper()} / WORKSPACE').classes(
                                'text-[10px] md:text-xs font-bold tracking-[0.17em] text-teal-200')
                        ui.label(title).classes('text-2xl md:text-4xl font-extrabold tracking-tight')
                        ui.label(subtitle).classes('text-sm text-cyan-100/90 leading-relaxed')
                    with ui.column().classes('items-center gap-1'):
                        ui.icon('sailing', size='3xl').classes('text-teal-300/90')
                        ui.label('FISHERY FINANCE').classes('text-[9px] tracking-widest text-teal-200')
            yield
            with ui.row().classes('w-full justify-between items-center flex-wrap gap-2 pt-3 pb-5'):
                ui.label(APP_NAME).classes('text-xs font-bold text-slate-500')
                ui.label(f'{APP_TAGLINE} · Data tersimpan pada server').classes('text-xs text-slate-400')


def logout():
    from nicegui import app
    app.storage.user.clear()
    ui.navigate.to('/login')


def nav_button(label, url, icon='add'):
    return ui.button(label, icon=icon, on_click=lambda: ui.navigate.to(url)).props(
        'unelevated no-caps').classes('rounded-xl px-4 font-semibold shadow-sm')


def section(title, icon=''):
    with ui.row().classes('w-full items-center gap-2 pt-2'):
        if icon:
            ui.icon(icon, size='sm').classes('text-teal-700')
        return ui.label(title).classes('text-lg md:text-xl font-extrabold tracking-tight text-slate-800')


def message_empty(message):
    with ui.card().classes('w-full items-center justify-center py-12 px-6 gap-2 ' + CARD):
        with ui.element('div').classes('rounded-2xl p-4 bg-teal-50'):
            ui.icon('inbox', size='2xl').classes('text-teal-600')
        ui.label('Belum ada data').classes('text-lg font-bold text-slate-800')
        ui.label(message).classes('text-sm text-slate-500 text-center max-w-lg')


def stats(label, value, icon='assessment'):
    with ui.card().classes('grow min-w-52 p-5 gap-3 transition-all duration-200 '
                           'hover:shadow-lg hover:-translate-y-0.5 ' + CARD):
        with ui.row().classes('w-full items-center justify-between gap-2'):
            ui.label(label).classes('text-sm font-medium text-slate-500')
            with ui.element('div').classes('rounded-xl bg-teal-50 p-2'):
                ui.icon(icon, size='sm').classes('text-teal-700')
        ui.label(str(value)).classes('text-xl md:text-2xl font-extrabold tracking-tight text-slate-900')


def data_table(rows, columns, *, row_key='id', max_rows=18):
    """Tabel yang dapat dicari, diurutkan, dan dipaginasi dari Python."""
    if not rows:
        message_empty('Belum ada data pada periode yang dipilih.')
        return None
    cols = [{'name': key, 'label': label, 'field': key, 'align': 'left', 'sortable': True}
            for key, label in columns]
    with ui.card().classes('w-full gap-0 p-0 overflow-hidden ' + CARD):
        with ui.row().classes('w-full flex-wrap items-center gap-3 justify-between p-4 border-b border-slate-100'):
            with ui.row().classes('items-center gap-2'):
                ui.icon('table_rows', size='sm').classes('text-teal-700')
                ui.label('Data terperinci').classes('text-sm font-bold text-slate-800')
                ui.badge(f'{len(rows)} baris').props('outline color=secondary').classes('ml-1')
            search = ui.input(placeholder='Cari kode, nama, atau nominal ...').props(
                'outlined dense clearable').classes('w-full md:w-72 bg-white rounded-xl')
        table = ui.table(columns=cols, rows=rows, row_key=row_key,
                         pagination={'rowsPerPage': max_rows}).props(
            'flat dense wrap-cells').classes('w-full text-slate-700')
        search.bind_value(table, 'filter')
    return table


def filter_dates(include_start=False, title='Posisi per tanggal'):
    from django.utils import timezone
    with ui.row().classes('items-center gap-3 flex-wrap'):
        start = (ui.input('Dari tanggal', value='').props('type=date outlined dense')
                 .classes(INPUT) if include_start else None)
        end = ui.input(title, value=timezone.localdate().isoformat()).props(
            'type=date outlined dense').classes(INPUT)
    return start, end
