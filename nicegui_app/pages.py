"""Halaman aplikasi Channave Fishery. Seluruh markup UI ditulis via API Python NiceGUI."""
from collections import defaultdict
from datetime import date
from decimal import Decimal
from io import BytesIO

from django.contrib.auth import authenticate, get_user_model
from django.db.models import Sum
from django.utils import timezone
from fastapi import Request
from nicegui import app, ui
from .db import db_call
from .branding import (APP_NAME, APP_SHORT_NAME, APP_CATEGORY, APP_TAGLINE,
                       APP_DESCRIPTION, EXPORT_PREFIX)
from .layout import apply_theme, brand_mark

from .backend import (Account, BusinessProfile, EXPORTS, InventoryLayer, InventoryMovement,
                      JournalEntry, JournalLine, NAME, Party, Product, ZERO,
                      build_linked_workbook, ledger, period_totals,
                      report_balances, stock_card, subsidiary, worksheet)
from .editor import journal_editor, model_editor, movement_editor
from .formatting import iso, maybe_date, number, rupiah, tanggal
from .layout import CARD, data_table, filter_dates, message_empty, nav_button, section, shell, stats


def _load_active_user(uid):
    """Semua akses ORM autentikasi harus berada dalam thread pekerja."""
    return get_user_model().objects.filter(pk=uid, is_active=True).first()


async def current_user():
    """Autentikasi per halaman, aman dari SynchronousOnlyOperation."""
    uid = app.storage.user.get('uid')
    if not uid:
        ui.navigate.to('/login')
        return None
    user = await db_call(_load_active_user, uid)
    if user is None:
        app.storage.user.clear()
        ui.navigate.to('/login')
    return user


def with_user(function):
    """Semua route terlindungi async; hilangkan parameter user dari signature FastAPI."""
    import inspect
    from functools import wraps

    @wraps(function)
    async def wrapper(*args, **kwargs):
        user = await current_user()
        if user is not None:
            result = function(*args, user=user, **kwargs)
            return await result if inspect.isawaitable(result) else result

    params = [param for param in inspect.signature(function).parameters.values()
              if param.name != 'user']
    wrapper.__signature__ = inspect.signature(function).replace(parameters=params)
    return wrapper


def parse_period(start_field, end_field):
    try:
        start = maybe_date(start_field.value) if start_field else None
        end = maybe_date(end_field.value, timezone.localdate())
        if start and end and start > end:
            ui.notify('Tanggal awal harus sebelum atau sama dengan tanggal akhir.', type='warning')
            return None
        return start, end
    except ValueError:
        ui.notify('Format tanggal tidak valid.', type='negative')
        return None


def export_button(kind, end_field=None, start_field=None):
    def make_excel(start, end):
        wb = build_linked_workbook(end, start)
        if kind != 'all':
            wb.active = wb.sheetnames.index(NAME[kind])
        out = BytesIO()
        wb.save(out)
        return out.getvalue()

    def active_user(uid):
        return bool(uid and get_user_model().objects.filter(pk=uid, is_active=True).exists())

    async def do_export():
        uid = app.storage.user.get('uid')
        if not await db_call(active_user, uid):
            ui.notify('Sesi tidak aktif. Silakan login ulang.', type='negative')
            ui.navigate.to('/login')
            return
        period = parse_period(start_field, end_field) if end_field else (None, timezone.localdate())
        if period is None:
            return
        start, end = period
        try:
            binary = await db_call(make_excel, start, end)
            slug = 'lengkap' if kind == 'all' else kind
            ui.download.content(binary, f'{EXPORT_PREFIX}_{slug}_{end:%Y%m%d}.xlsx',
                media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        except Exception as exc:
            ui.notify(f'Gagal membuat Excel: {exc}', type='negative')

    return ui.button('Ekspor Excel', icon='file_download', on_click=do_export).props('outline no-caps').classes('rounded-xl font-semibold')


@ui.page('/', response_timeout=30)
def root():
    uid = app.storage.user.get('uid')
    ui.navigate.to('/dashboard' if uid else '/login')


@ui.page('/login', response_timeout=30)
def login():
    if app.storage.user.get('uid'):
        ui.navigate.to('/dashboard')
        return
    apply_theme()
    with ui.column().classes('w-full min-h-screen items-center justify-center bg-gradient-to-br from-slate-950 via-cyan-950 to-teal-900 p-4 md:p-8'):
        with ui.row().classes(
                'w-full max-w-5xl gap-0 items-stretch bg-white rounded-3xl shadow-2xl overflow-hidden border border-cyan-800/20'):
            # Panel identitas: informasi desain, bukan data keuangan yang dibuat-buat.
            with ui.column().classes(
                    'w-full lg:w-1/2 bg-gradient-to-br from-cyan-900 via-teal-800 to-slate-950 text-white p-7 md:p-12 justify-between gap-8'):
                with ui.column().classes('gap-3'):
                    with ui.row().classes('items-center gap-3'):
                        brand_mark(size='xl')
                        with ui.column().classes('gap-0'):
                            ui.label(APP_SHORT_NAME.upper()).classes('text-2xl font-bold tracking-tight')
                            ui.label(APP_CATEGORY).classes('text-xs font-bold tracking-widest text-teal-200')
                    ui.label('Kelola usaha perikanan dengan lebih tertata.').classes(
                        'text-3xl md:text-4xl font-bold leading-tight mt-6'
                    )
                    ui.label(APP_DESCRIPTION).classes('text-base text-cyan-100')
                with ui.column().classes('gap-3'):
                    with ui.row().classes('items-center gap-2'):
                        ui.icon('receipt_long', size='sm').classes('text-teal-200')
                        ui.label('Jurnal dan laporan keuangan').classes('text-sm text-cyan-50')
                    with ui.row().classes('items-center gap-2'):
                        ui.icon('inventory_2', size='sm').classes('text-teal-200')
                        ui.label('Persediaan dan HPP metode FIFO').classes('text-sm text-cyan-50')
                    with ui.row().classes('items-center gap-2'):
                        ui.icon('file_download', size='sm').classes('text-teal-200')
                        ui.label('Ekspor laporan ke Excel').classes('text-sm text-cyan-50')
            # Panel form asli Django-auth: hanya penampilan NiceGUI yang berubah.
            with ui.column().classes('w-full lg:w-1/2 p-7 md:p-12 justify-center gap-5 bg-white'):
                ui.label('SELAMAT DATANG').classes('text-xs font-bold tracking-widest text-teal-700')
                ui.label(f'Masuk ke {APP_NAME}').classes(
                    'text-2xl md:text-3xl font-bold text-slate-900 leading-tight'
                )
                ui.label('Gunakan akun yang terdaftar untuk mengakses pembukuan usaha.').classes(
                    'text-sm text-slate-500 mb-3'
                )
                name = ui.input('Username').classes('w-full').props(
                    'outlined autocomplete=username')
                password = ui.input('Password', password=True, password_toggle_button=True).classes(
                    'w-full').props('outlined autocomplete=current-password')
                error = ui.label('').classes('text-sm text-red-700')

                async def sign_in():
                    failures = app.storage.user.get('login_failures', 0)
                    if failures >= 10:
                        error.set_text('Terlalu banyak kegagalan login di sesi ini. Hubungi administrator.')
                        return
                    user = await db_call(authenticate, username=(name.value or '').strip(),
                                         password=password.value or '')
                    if user is None or not user.is_active:
                        app.storage.user['login_failures'] = failures + 1
                        error.set_text('Username atau password tidak cocok.')
                        return
                    app.storage.user.clear()
                    app.storage.user['uid'] = user.pk
                    ui.navigate.to('/dashboard')

                ui.button('Masuk ke Dashboard', icon='login', on_click=sign_in).props(
                    'unelevated no-caps').classes('w-full rounded-xl py-2.5 font-bold')
                ui.label('Belum punya akun? Hubungi administrator aplikasi.').classes(
                    'text-xs text-slate-400')
                ui.separator().classes('bg-slate-100')
                ui.label(f'{APP_NAME} · {APP_TAGLINE}').classes('text-xs text-slate-400')


@ui.page('/dashboard', response_timeout=30)
@with_user
async def dashboard(user):
    """Ikhtisar interaktif. Semua query tetap dijalankan melalui db_call."""
    def load(as_of):
        totals = period_totals(as_of)
        received = (InventoryMovement.objects.filter(date__lte=as_of, kind__in=['OPENING', 'IN'])
                    .aggregate(q=Sum('quantity'))['q'] or ZERO)
        shipped = (InventoryMovement.objects.filter(date__lte=as_of, kind='OUT')
                   .aggregate(q=Sum('quantity'))['q'] or ZERO)
        qty = received - shipped
        products = Product.objects.count()
        journals = JournalEntry.objects.filter(date__lte=as_of).count()
        month_offset = as_of.year * 12 + as_of.month - 1
        labels, revs, costs = [], [], []
        for index in range(5, -1, -1):
            y, zero_based = divmod(month_offset - index, 12)
            m = zero_based + 1
            group = (JournalLine.objects
                     .filter(entry__date__year=y, entry__date__month=m,
                             entry__date__lte=as_of)
                     .values('account__category')
                     .annotate(d=Sum('debit'), c=Sum('credit')))
            values = {x['account__category']: (x['d'] or ZERO, x['c'] or ZERO) for x in group}
            income = sum((values.get(k, (ZERO, ZERO))[1] - values.get(k, (ZERO, ZERO))[0]
                          for k in ('REVENUE', 'OTHER_INCOME')), ZERO)
            cost = sum((values.get(k, (ZERO, ZERO))[0] - values.get(k, (ZERO, ZERO))[1]
                        for k in ('COGS', 'EXPENSE', 'OTHER_EXPENSE')), ZERO)
            labels.append(date(y, m, 1).strftime('%b %Y'))
            revs.append(float(income)); costs.append(float(cost))
        entries = list(JournalEntry.objects.filter(date__lte=as_of).order_by('-date', '-id')[:8])
        recent = [{'id': x.pk, 'tanggal': tanggal(x.date), 'bukti': x.reference,
                   'jenis': x.get_kind_display(), 'uraian': x.description,
                   'debet': rupiah(x.total_debit)} for x in entries]
        return totals, qty, products, journals, labels, revs, costs, recent

    def quick_action(label, description, icon, target):
        with ui.link(target=target).classes('no-underline grow min-w-48'):
            with ui.card().classes('h-full p-4 gap-2 rounded-2xl bg-white border border-slate-200 '
                                   'transition duration-200 hover:-translate-y-0.5 hover:shadow-lg shadow-sm'):
                with ui.row().classes('items-center justify-between w-full'):
                    ui.icon(icon, size='lg').classes('text-teal-700 bg-teal-50 rounded-xl p-2')
                    ui.icon('arrow_outward', size='xs').classes('text-slate-400')
                ui.label(label).classes('font-extrabold text-sm text-slate-900')
                ui.label(description).classes('text-xs text-slate-500')

    def draw(data):
        totals, qty, products, journals, labels, revs, costs, recent = data
        margin = float(totals['profit'] / totals['revenue'] * 100) if totals['revenue'] else 0
        container.clear()
        with container:
            with ui.row().classes('w-full gap-3 flex-wrap'):
                stats('Total Pendapatan', rupiah(totals['revenue']), 'payments')
                stats('Total Biaya', rupiah(totals['costs']), 'receipt')
                stats('Laba / Rugi Bersih', rupiah(totals['profit']), 'trending_up')
                stats('Kontrol Neraca', rupiah(totals['difference']), 'verified')
            with ui.row().classes('w-full gap-3 flex-wrap'):
                stats('Produk Tercatat', products, 'set_meal')
                stats('Total Kuantitas Stok', number(qty, 3), 'inventory_2')
                stats('Jumlah Jurnal', journals, 'receipt_long')
                stats('Margin Laba', f'{margin:,.1f}%', 'percent')

            section('Akses Cepat', 'bolt')
            with ui.row().classes('w-full gap-3 flex-wrap'):
                quick_action('Jurnal Baru', 'Catat debet dan kredit', 'post_add', '/journal/new')
                quick_action('Transaksi Stok', 'Pembelian atau penjualan', 'inventory', '/inventory/new')
                quick_action('Produk Baru', 'Tambah hasil perikanan', 'add_box', '/products/new')
                quick_action('Laporan Keuangan', 'Periksa laba dan neraca', 'analytics', '/income')

            with ui.row().classes('w-full gap-4 items-stretch flex-wrap'):
                with ui.card().classes('grow min-w-72 p-5 gap-3 ' + CARD):
                    with ui.row().classes('items-center justify-between w-full'):
                        with ui.column().classes('gap-0'):
                            ui.label('Tren Finansial').classes('font-extrabold text-slate-900 text-lg')
                            ui.label('Pendapatan dan biaya · 6 bulan terakhir').classes('text-xs text-slate-500')
                        ui.icon('show_chart', size='lg').classes('text-teal-700')
                    ui.echart({
                        'color': ['#0D9488', '#F59E0B'],
                        'grid': {'left': 70, 'right': 18, 'top': 55, 'bottom': 43},
                        'tooltip': {'trigger': 'axis'},
                        'legend': {'data': ['Pendapatan', 'Biaya'], 'top': 10, 'right': 8},
                        'xAxis': {'type': 'category', 'boundaryGap': False, 'data': labels,
                                  'axisLine': {'lineStyle': {'color': '#CBD5E1'}}},
                        'yAxis': {'type': 'value', 'splitLine': {'lineStyle': {'color': '#F1F5F9'}}},
                        'series': [
                            {'name': 'Pendapatan', 'type': 'line', 'smooth': True,
                             'symbolSize': 8, 'lineStyle': {'width': 3}, 'areaStyle': {'opacity': .09}, 'data': revs},
                            {'name': 'Biaya', 'type': 'line', 'smooth': True,
                             'symbolSize': 8, 'lineStyle': {'width': 3}, 'areaStyle': {'opacity': .07}, 'data': costs},
                        ],
                    }).classes('w-full h-72 md:h-80')
                with ui.card().classes('w-full md:w-72 p-5 gap-3 ' + CARD):
                    ui.icon('file_download', size='xl').classes('text-teal-700 bg-teal-50 p-3 rounded-2xl')
                    ui.label('Laporan Excel Terhubung').classes('font-extrabold text-slate-900 text-lg')
                    ui.label('Ubah nominal di lembar input. Rumus pada neraca, laba rugi, '
                             'persediaan, dan ringkasan mengikuti perubahan saat Excel menghitung ulang.').classes(
                             'text-sm text-slate-600 leading-relaxed')
                    ui.separator()
                    with ui.row().classes('items-center gap-2'):
                        ui.icon('check_circle', size='sm').classes('text-teal-600')
                        ui.label('Rumus antar-sheet aktif').classes('text-xs text-slate-600')
                    with ui.row().classes('items-center gap-2'):
                        ui.icon('info_outline', size='sm').classes('text-amber-600')
                        ui.label('Transaksi baru: ekspor ulang').classes('text-xs text-slate-600')
                    ui.button('Lihat Neraca', icon='arrow_forward',
                              on_click=lambda: ui.navigate.to('/balance')).props('outline no-caps')

            section('Aktivitas Jurnal Terbaru', 'history')
            data_table(recent, [('tanggal', 'Tanggal'), ('bukti', 'Nomor Bukti'),
                                ('jenis', 'Jenis'), ('uraian', 'Uraian'), ('debet', 'Nilai')])

    initial_data = await db_call(load, timezone.localdate())
    with shell('Dashboard', f'Selamat datang, {user.get_username()}. Pantau bisnis dalam satu tampilan.'):
        with ui.card().classes('w-full p-4 border border-teal-100 shadow-none bg-teal-50 rounded-2xl'):
            with ui.row().classes('w-full items-center justify-between gap-3 flex-wrap'):
                with ui.row().classes('items-center gap-3'):
                    ui.icon('insights', size='lg').classes('text-teal-700')
                    with ui.column().classes('gap-0'):
                        ui.label('Ringkasan Kinerja Usaha').classes('font-bold text-slate-900')
                        ui.label('Pilih posisi tanggal untuk memperbarui semua angka.').classes('text-xs text-slate-600')
                _, end = filter_dates()
                export_button('all', end)
                refresh_btn = ui.button('Perbarui', icon='refresh').props('unelevated no-caps').classes('rounded-xl')
        container = ui.column().classes('w-full gap-4')

        async def refresh():
            period = parse_period(None, end)
            if period:
                refresh_btn.disable()
                try:
                    draw(await db_call(load, period[1]))
                    ui.notify('Dashboard sudah diperbarui.', type='positive')
                except Exception as exc:
                    ui.notify(f'Gagal memuat ringkasan: {exc}', type='negative')
                finally:
                    refresh_btn.enable()

        refresh_btn.on('click', refresh)
        draw(initial_data)


@ui.page('/accounts', response_timeout=30)
@with_user
async def accounts_page(user):
    def load():
        accounts = list(Account.objects.all())
        rows = [{'id': x.pk, 'kode': x.code, 'nama': x.name,
                 'kelompok': x.get_category_display(), 'saldo_normal': x.normal_balance,
                 'saldo_awal': rupiah(x.opening_balance), 'aktif': 'Ya' if x.is_active else 'Tidak'}
                for x in accounts]
        return rows, {str(x.pk): str(x) for x in accounts}

    rows, options = await db_call(load)
    with shell('Daftar Akun', 'Master akun, tetap tersembunyi di navigasi utama'):
        nav_button('Tambah Akun', '/accounts/new')
        data_table(rows, [('kode','Kode'),('nama','Nama'),('kelompok','Kelompok'),
                          ('saldo_normal','Normal'),('saldo_awal','Saldo Awal'),('aktif','Aktif')])
        chooser = ui.select(options,
                            label='Pilih akun untuk diedit', with_input=True).classes('w-full max-w-lg')
        ui.button('Edit Akun', on_click=lambda: ui.navigate.to(f'/accounts/{chooser.value}/edit') if chooser.value else None)
        export_button('accounts')


@ui.page('/accounts/new', response_timeout=30)
@with_user
async def account_new(user):
    await model_editor('accounts')


@ui.page('/accounts/{item_id}/edit', response_timeout=30)
@with_user
async def account_edit(item_id: int, user):
    await model_editor('accounts', item_id)


@ui.page('/parties', response_timeout=30)
@with_user
async def parties_page(user):
    def load():
        parties = list(Party.objects.all())
        rows = [{'id': p.pk, 'kode': p.code, 'nama': p.name,
                 'jenis': p.get_kind_display(), 'saldo_awal': rupiah(p.opening_balance),
                 'telepon': p.phone} for p in parties]
        return rows, {str(p.pk): str(p) for p in parties}

    rows, options = await db_call(load)
    with shell('Kode Pembantu', 'Relasi pelanggan dan pemasok'):
        nav_button('Tambah Relasi', '/parties/new')
        data_table(rows, [('kode','Kode'),('nama','Nama'),('jenis','Jenis'),
                          ('saldo_awal','Saldo Awal'),('telepon','Telepon')])
        chooser = ui.select(options,
                            label='Pilih relasi untuk diedit', with_input=True).classes('w-full max-w-lg')
        ui.button('Edit Relasi', on_click=lambda: ui.navigate.to(f'/parties/{chooser.value}/edit') if chooser.value else None)
        export_button('parties')


@ui.page('/parties/new', response_timeout=30)
@with_user
async def party_new(user):
    await model_editor('parties')


@ui.page('/parties/{item_id}/edit', response_timeout=30)
@with_user
async def party_edit(item_id: int, user):
    await model_editor('parties', item_id)


async def journal_listing(adjustment=False):
    title = 'Jurnal Penyesuaian' if adjustment else 'Jurnal Umum'

    def load(lower, upper):
        qs = JournalEntry.objects.filter(date__lte=upper).order_by('-date', '-id')
        qs = qs.filter(kind='ADJUSTMENT') if adjustment else qs.exclude(kind='ADJUSTMENT')
        if lower:
            qs = qs.filter(date__gte=lower)
        return [{'id': e.pk, 'tanggal': tanggal(e.date), 'bukti': e.reference,
                 'jenis': e.get_kind_display(), 'keterangan': e.description,
                 'debet': rupiah(e.total_debit), 'kredit': rupiah(e.total_credit)}
                for e in qs[:1000]]

    def draw(rows):
        with container:
            container.clear()
            data_table(rows, [('tanggal','Tanggal'),('bukti','Bukti'),('jenis','Jenis'),
                              ('keterangan','Keterangan'),('debet','Debet'),('kredit','Kredit')])
            chooser = ui.select({str(r['id']): r['bukti'] for r in rows},
                                label='Lihat rincian jurnal', with_input=True).classes('w-full max-w-md')
            ui.button('Lihat Jurnal', on_click=lambda: ui.navigate.to(f'/journal/{chooser.value}') if chooser.value else None)

    initial_rows = await db_call(load, None, timezone.localdate())
    with shell(title, 'Pencatatan berpasangan dan jurnal persediaan otomatis'):
        with ui.row().classes('flex-wrap gap-3 items-center'):
            nav_button('Tambah Jurnal', '/adjustments/new' if adjustment else '/journal/new')
            start, end = filter_dates(include_start=True)
            export_button('adjustment' if adjustment else 'journal', end, start)
        container = ui.column().classes('w-full gap-3')

        async def refresh():
            period = parse_period(start, end)
            if period:
                draw(await db_call(load, *period))

        ui.button('Tampilkan', icon='search', on_click=refresh)
        draw(initial_rows)


@ui.page('/journal', response_timeout=30)
@with_user
async def journal_page(user):
    await journal_listing(False)


@ui.page('/adjustments', response_timeout=30)
@with_user
async def adjustment_page(user):
    await journal_listing(True)


@ui.page('/journal/new', response_timeout=30)
@with_user
async def journal_new(user):
    await journal_editor(JournalEntry.Kind.GENERAL, user)


@ui.page('/adjustments/new', response_timeout=30)
@with_user
async def adjustment_new(user):
    await journal_editor(JournalEntry.Kind.ADJUSTMENT, user)


@ui.page('/journal/{item_id}', response_timeout=30)
@with_user
async def journal_detail(item_id: int, user):
    def load():
        entry = JournalEntry.objects.filter(pk=item_id).first()
        if entry is None:
            return None
        lines = list(entry.lines.select_related('account', 'party').all())
        rows = [{'id': x.pk, 'akun': str(x.account),
                 'relasi': str(x.party) if x.party else '–', 'ket': x.description,
                 'debet': rupiah(x.debit), 'kredit': rupiah(x.credit)} for x in lines]
        return (entry.reference, tanggal(entry.date), entry.get_kind_display(),
                entry.description, rows, rupiah(entry.total_debit),
                rupiah(entry.total_credit), entry.kind)

    result = await db_call(load)
    if result is None:
        ui.navigate.to('/journal')
        return
    ref, entry_date, kind_display, description, rows, debet, kredit, kind = result
    with shell(f'Jurnal {ref}', f'{entry_date} | {kind_display}'):
        ui.label(description).classes('text-slate-600')
        data_table(rows, [('akun','Akun'),('relasi','Relasi'),('ket','Keterangan'),
                          ('debet','Debet'),('kredit','Kredit')])
        with ui.row().classes('flex-wrap gap-3'):
            stats('Total Debet', debet)
            stats('Total Kredit', kredit)
        nav_button('Kembali', '/adjustments' if kind == 'ADJUSTMENT' else '/journal', 'arrow_back')


@ui.page('/ledger', response_timeout=30)
@with_user
async def ledger_page(user):
    def load(account_pk, start, end):
        account = Account.objects.filter(pk=account_pk, is_header=False).first() if account_pk else None
        if account is None:
            return None
        report = ledger(account, start, end)
        records = [{'id': i, 'tanggal': tanggal(r['date']), 'bukti': r['reference'],
                    'keterangan': r['description'], 'relasi': str(r['party'] or '–'),
                    'debet': rupiah(r['debit']), 'kredit': rupiah(r['credit']),
                    'saldo': rupiah(r['balance'])} for i, r in enumerate(report['records'])]
        return report['opening'], report['closing'], records

    def draw(result):
        with container:
            container.clear()
            if result is None:
                message_empty('Pilih akun untuk melihat buku besar.')
                return
            opening, closing, rows = result
            with ui.row().classes('gap-3 w-full flex-wrap'):
                stats('Saldo Awal', rupiah(opening))
                stats('Saldo Akhir', rupiah(closing))
            data_table(rows, [('tanggal','Tanggal'),('bukti','Bukti'),('keterangan','Keterangan'),
                              ('relasi','Relasi'),('debet','Debet'),('kredit','Kredit'),('saldo','Saldo')])

    options = await db_call(lambda: {str(a.pk): str(a) for a in Account.objects.filter(is_header=False)})
    with shell('Buku Besar', 'Saldo berjalan setiap akun dari jurnal tersimpan'):
        select = ui.select(options,
                           label='Pilih akun', with_input=True).classes('w-full max-w-2xl').props('outlined')
        start, end = filter_dates(include_start=True)
        export_button('ledger', end, start)
        container = ui.column().classes('w-full gap-3')

        async def refresh():
            period = parse_period(start, end)
            if period:
                draw(await db_call(load, select.value, *period))

        ui.button('Tampilkan', icon='search', on_click=refresh)
        draw(None)


@ui.page('/subsidiary', response_timeout=30)
@with_user
async def subsidiary_page(user):
    def load(party_pk, start, end):
        party = Party.objects.filter(pk=party_pk).first() if party_pk else None
        if not party:
            return None
        report = subsidiary(party, start, end)
        rows = [{'id': i, 'tanggal': tanggal(r['date']), 'bukti': r['reference'],
                 'uraian': r['description'], 'debet': rupiah(r['debit']),
                 'kredit': rupiah(r['credit']), 'saldo': rupiah(r['balance'])}
                for i, r in enumerate(report['records'])]
        return report['opening'], report['closing'], rows

    def draw(result):
        with container:
            container.clear()
            if result is None:
                message_empty('Pilih relasi untuk melihat buku besar pembantu.')
                return
            opening, closing, rows = result
            with ui.row().classes('gap-3 flex-wrap w-full'):
                stats('Saldo Awal', rupiah(opening))
                stats('Saldo Akhir', rupiah(closing))
            data_table(rows, [('tanggal','Tanggal'),('bukti','Bukti'),('uraian','Keterangan'),
                              ('debet','Debet'),('kredit','Kredit'),('saldo','Saldo')])

    options = await db_call(lambda: {str(p.pk): str(p) for p in Party.objects.all()})
    with shell('Buku Besar Pembantu', 'Mutasi dan saldo menurut pelanggan / pemasok'):
        select = ui.select(options,
                           label='Pilih relasi', with_input=True).classes('w-full max-w-2xl').props('outlined')
        start, end = filter_dates(include_start=True)
        export_button('subsidiary', end, start)
        container = ui.column().classes('w-full gap-3')

        async def refresh():
            period = parse_period(start, end)
            if period:
                draw(await db_call(load, select.value, *period))

        ui.button('Tampilkan', icon='search', on_click=refresh)
        draw(None)


async def dated_report(title, kind, loader, renderer):
    initial = await db_call(loader, timezone.localdate())
    with shell(title):
        _, end = filter_dates()
        export_button(kind, end)
        container = ui.column().classes('w-full gap-3')

        def draw(data):
            with container:
                container.clear()
                renderer(data)

        async def refresh():
            period = parse_period(None, end)
            if period:
                draw(await db_call(loader, period[1]))

        ui.button('Tampilkan', icon='search', on_click=refresh)
        draw(initial)


def show_trial(report):
    debet = sum((r['debit'] for r in report), ZERO)
    kredit = sum((r['credit'] for r in report), ZERO)
    with ui.row().classes('gap-3 flex-wrap w-full'):
        stats('Total Debet', rupiah(debet))
        stats('Total Kredit', rupiah(kredit))
        stats('Selisih', rupiah(debet-kredit))
    rows = [{'id': r['account'].pk, 'kode': r['account'].code,
             'akun': r['account'].name, 'debet': rupiah(r['debit']),
             'kredit': rupiah(r['credit'])} for r in report]
    data_table(rows, [('kode','Kode'),('akun','Akun'),('debet','Debet'),('kredit','Kredit')])


@ui.page('/trial-balance', response_timeout=30)
@with_user
async def trial_page(user):
    await dated_report('Neraca Saldo', 'trial', report_balances, show_trial)


def show_worksheet(report):
    columns = [('kode','Kode'),('nama','Akun'),('trial_d','NS D'),('trial_c','NS K'),
               ('adj_d','Adj D'),('adj_c','Adj K'),('adjusted_d','Disesuaikan D'),
               ('adjusted_c','Disesuaikan K'),('income_d','LR D'),('income_c','LR K'),
               ('balance_d','Neraca D'),('balance_c','Neraca K')]
    records = []
    for row in report['rows']:
        records.append({'id': row['account'].pk, 'kode': row['account'].code,
                        'nama': row['account'].name,
                        **{key: number(row[key]) for key, _ in columns[2:]}})
    data_table(records, columns, max_rows=20)
    with ui.row().classes('flex-wrap gap-3'):
        stats('Laba Berjalan', rupiah(report['profit']))
        stats('Selisih Neraca Saldo', rupiah(report['check_trial']))
        stats('Selisih Saldo Disesuaikan', rupiah(report['check_adjusted']))
    ui.label('Geser tabel secara horizontal untuk melihat seluruh kolom.').classes('text-sm text-slate-500')


@ui.page('/worksheet', response_timeout=30)
@with_user
async def worksheet_page(user):
    await dated_report('Neraca Lajur', 'worksheet', worksheet, show_worksheet)


def show_income(totals):
    groups = [('REVENUE','Pendapatan'),('COGS','Harga Pokok Penjualan'),
              ('EXPENSE','Beban Operasional'),('OTHER_INCOME','Pendapatan Lain-lain'),
              ('OTHER_EXPENSE','Beban Lain-lain')]
    records = []
    for key,label in groups:
        for row in totals['groups'].get(key, []):
            amount = -row['net'] if key in ('REVENUE','OTHER_INCOME') else row['net']
            records.append({'id':row['account'].pk, 'kelompok':label,
                            'kode':row['account'].code,'nama':row['account'].name,
                            'nilai':rupiah(amount)})
    data_table(records, [('kelompok','Kelompok'),('kode','Kode'),('nama','Akun'),('nilai','Nilai')])
    with ui.row().classes('flex-wrap gap-3'):
        stats('Pendapatan', rupiah(totals['revenue']))
        stats('Total Biaya', rupiah(totals['costs']))
        stats('Laba / Rugi Bersih', rupiah(totals['profit']))


@ui.page('/income', response_timeout=30)
@with_user
async def income_page(user):
    await dated_report('Laporan Laba Rugi', 'income', period_totals, show_income)


def show_balance(totals):
    records = []
    for key, label in [('ASSET','Aset'),('LIABILITY','Kewajiban'),('EQUITY','Ekuitas')]:
        for r in totals['groups'].get(key, []):
            amount = r['net'] if key == 'ASSET' else -r['net']
            records.append({'id':r['account'].pk,'kelompok':label,'kode':r['account'].code,
                            'nama':r['account'].name,'jumlah':rupiah(amount)})
    data_table(records, [('kelompok','Kelompok'),('kode','Kode'),('nama','Akun'),('jumlah','Jumlah')])
    with ui.row().classes('flex-wrap gap-3'):
        stats('Total Aset', rupiah(totals['assets']))
        stats('Kewajiban', rupiah(totals['liabilities']))
        stats('Ekuitas + Laba Berjalan', rupiah(totals['equity_with_profit']))
        stats('Selisih Neraca', rupiah(totals['difference']))


@ui.page('/balance', response_timeout=30)
@with_user
async def balance_page(user):
    await dated_report('Laporan Neraca', 'balance', period_totals, show_balance)


@ui.page('/products', response_timeout=30)
@with_user
async def products_page(user):
    def load():
        products = list(Product.objects.all())
        records = []
        for product in products:
            card = stock_card(product)
            records.append({'id': product.pk, 'kode': product.code, 'nama': product.name,
                            'satuan': product.unit, 'harga_jual': rupiah(product.sale_price),
                            'stok': number(card['qty'], 3), 'nilai': rupiah(card['value'])})
        return records, {str(p.pk): str(p) for p in products}

    records, options = await db_call(load)
    with shell('Master Persediaan', 'Data hasil perikanan dan saldo stok FIFO'):
        with ui.row().classes('flex-wrap gap-3'):
            nav_button('Tambah Produk', '/products/new')
            export_button('products')
        data_table(records, [('kode','Kode'),('nama','Produk'),('satuan','Satuan'),
                             ('harga_jual','Harga Jual'),('stok','Stok'),('nilai','Nilai FIFO')])
        chooser = ui.select(options,
                            label='Produk yang ingin diedit', with_input=True).classes('w-full max-w-lg')
        ui.button('Edit Produk', on_click=lambda: ui.navigate.to(f'/products/{chooser.value}/edit') if chooser.value else None)


@ui.page('/products/new', response_timeout=30)
@with_user
async def product_new(user):
    await model_editor('products')


@ui.page('/products/{item_id}/edit', response_timeout=30)
@with_user
async def product_edit(item_id: int, user):
    await model_editor('products', item_id)


@ui.page('/inventory', response_timeout=30)
@with_user
async def inventory_page(request: Request, user):
    def load(product_pk, end):
        p = Product.objects.filter(pk=product_pk).first() if product_pk else None
        if p is None:
            return None
        card = stock_card(p, end=end)
        records = []
        for r in card['records']:
            m = r['movement']
            records.append({'id':m.pk,'tanggal':tanggal(m.date),
                            'bukti':m.reference,'uraian':m.description,
                            'masuk':number(r['in_qty'],3), 'biaya_masuk':rupiah(r['in_value']),
                            'keluar':number(r['out_qty'],3),'hpp':rupiah(r['out_value']),
                            'saldo':number(r['qty'],3),'nilai':rupiah(r['value']),
                            'biaya_unit':rupiah(r['unit_cost'])})
        return p.unit, card['qty'], card['value'], records

    def draw(result):
        with container:
            container.clear()
            if result is None:
                message_empty('Pilih produk untuk menampilkan kartu persediaan.')
                return
            unit, qty, value, records = result
            with ui.row().classes('w-full gap-3 flex-wrap'):
                stats('Sisa Stok', f'{number(qty,3)} {unit}')
                stats('Nilai FIFO', rupiah(value))
            data_table(records, [('tanggal','Tanggal'),('bukti','Bukti'),('uraian','Uraian'),
                                 ('masuk','Masuk'),('biaya_masuk','Nilai Masuk'),
                                 ('keluar','Keluar'),('hpp','HPP Keluar'),
                                 ('saldo','Saldo Unit'),('biaya_unit','Saldo/Unit'),('nilai','Nilai Saldo')])
            ui.label('Nilai saldo/unit adalah nilai sisa dibagi unit sisa, bukan metode biaya rata-rata.').classes('text-sm text-slate-500')

    options = await db_call(lambda: {str(p.pk): str(p) for p in Product.objects.all()})
    selected_product = request.query_params.get('product')
    initial = await db_call(load, selected_product, timezone.localdate()) if selected_product else None
    with shell('Kartu Persediaan FIFO', 'Masuk, keluar, dan nilai sisa persediaan berdasarkan lapisan biaya FIFO'):
        with ui.row().classes('flex-wrap gap-3 items-center'):
            nav_button('Transaksi Stok', '/inventory/new')
            select = ui.select(options,
                               value=selected_product if selected_product in options else None,
                               label='Pilih produk', with_input=True).classes('w-full max-w-md').props('outlined')
            _, end = filter_dates()
            export_button('inventory', end)
        container = ui.column().classes('w-full gap-3')

        async def refresh():
            period = parse_period(None, end)
            if period:
                draw(await db_call(load, select.value, period[1]))

        ui.button('Tampilkan', icon='search', on_click=refresh)
        draw(initial)


@ui.page('/inventory/new', response_timeout=30)
@with_user
async def movement_new(user):
    await movement_editor(user)


@ui.page('/settings', response_timeout=30)
@with_user
async def settings_page(user):
    await model_editor('settings')
    with ui.row().classes('gap-3 mx-8'):
        nav_button('Daftar Akun', '/accounts', 'list_alt')
        nav_button('Kode Pembantu', '/parties', 'people')
