"""Editor NiceGUI yang tetap memakai validasi ModelForm Django asli."""
from decimal import Decimal, InvalidOperation

from django import forms as djforms
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone
from nicegui import ui
from .db import db_call

from .backend import (Account, AccountForm, BusinessProfile, JournalEntry,
                      JournalEntryForm, JournalLineFormSet, MovementForm, Party,
                      PartyForm, Product, ProductForm, ProfileForm,
                      create_opening_stock, create_stock_movement)
from .formatting import iso
from .layout import nav_button, shell


def err_text(errors):
    return ' | '.join(f'{key}: {", ".join(map(str, messages))}'
                      for key, messages in errors.items())[:1400]


def initial_for(form, name, field):
    value = form.initial.get(name, field.initial)
    if callable(value):
        value = value()
    return value


def prepare_choices(form):
    """Evaluasi semua ModelChoiceField dalam thread database, sebelum render UI."""
    return {
        name: {str(obj.pk): str(obj) for obj in field.queryset}
        for name, field in form.fields.items()
        if isinstance(field, djforms.ModelChoiceField)
    }


def build_inputs(form, model_choices=None):
    """Form responsif dua kolom, tetap memakai field dan validasi Django asli."""
    model_choices = model_choices or {}
    inputs = {}
    with ui.element('div').classes('w-full grid grid-cols-1 md:grid-cols-2 gap-x-5 gap-y-4'):
        for name, field in form.fields.items():
            value = initial_for(form, name, field)
            label = field.label or name.replace('_', ' ').title()
            wide = isinstance(field.widget, djforms.Textarea) or name in ('name', 'description', 'address')
            with ui.element('div').classes('w-full ' + ('md:col-span-2' if wide else '')):
                if isinstance(field, djforms.BooleanField):
                    elem = ui.checkbox(label, value=bool(value)).classes('py-2')
                elif isinstance(field, djforms.ModelChoiceField):
                    options = model_choices.get(name, {})
                    if not field.required:
                        options = {'': '– Tidak dipilih –', **options}
                    selected = str(value.pk if hasattr(value, 'pk') else value) if value is not None else ('' if not field.required else None)
                    elem = ui.select(options, label=label, value=selected, with_input=True).classes('w-full')
                    elem.props('outlined dense clearable')
                elif isinstance(field, djforms.ChoiceField):
                    options = dict(field.choices)
                    selected = str(value) if value is not None else None
                    elem = ui.select(options, value=selected, label=label).classes('w-full')
                    elem.props('outlined dense')
                elif isinstance(field, djforms.DateField):
                    elem = ui.input(label, value=iso(value) if hasattr(value, 'isoformat') else str(value or ''))
                    elem.props('type=date outlined dense').classes('w-full')
                elif isinstance(field.widget, djforms.Textarea):
                    elem = ui.textarea(label, value=str(value or '')).classes('w-full').props('outlined dense')
                else:
                    elem = ui.input(label, value='' if value is None else str(value)).classes('w-full')
                    elem.props('outlined dense')
                    if isinstance(field, djforms.DecimalField):
                        elem.props('inputmode=decimal')
                inputs[name] = elem
    return inputs


def read_inputs(inputs):
    result = {}
    for key, elem in inputs.items():
        # Django's CheckboxInput reads true only if key present and truthy.
        if isinstance(elem.value, bool):
            if elem.value:
                result[key] = 'on'
        elif elem.value is not None:
            result[key] = str(elem.value)
        else:
            result[key] = ''
    return result


async def model_editor(model_type, pk=None):
    routes = {
        'accounts': (Account, AccountForm, 'Daftar Akun', '/accounts'),
        'parties': (Party, PartyForm, 'Kode Pembantu', '/parties'),
        'products': (Product, ProductForm, 'Produk Perikanan', '/products'),
        'settings': (BusinessProfile, ProfileForm, 'Pengaturan Usaha', '/settings'),
    }
    model, form_cls, title, back_url = routes[model_type]
    def read_form():
        obj = (BusinessProfile.current() if model_type == 'settings' else
               model.objects.filter(pk=pk).first() if pk else None)
        if pk and obj is None:
            return None
        form = form_cls(instance=obj)
        return obj, form, prepare_choices(form)

    result = await db_call(read_form)
    if result is None:
        ui.notify('Data tidak ditemukan.', type='negative')
        ui.navigate.to(back_url)
        return
    obj, form, choices = result
    with shell(f'{"Ubah" if obj else "Tambah"} {title}'):
        with ui.card().classes('w-full max-w-5xl p-6 gap-5 bg-white rounded-3xl border border-slate-200 shadow-sm'):
            controls = build_inputs(form, choices)
            errors_container = ui.column().classes('w-full gap-1')

            def write_record(payload):
                bound = form_cls(payload, instance=obj)
                if not bound.is_valid():
                    return False, err_text(bound.errors)
                try:
                    with transaction.atomic():
                        saved = bound.save()
                        if model_type == 'products' and obj is None:
                            d = bound.cleaned_data
                            if (d.get('opening_quantity') or Decimal('0')) > 0:
                                create_opening_stock(saved, d['opening_quantity'],
                                                     d['opening_unit_cost'], d['opening_date'])
                except (ValidationError, IntegrityError, ValueError) as exc:
                    return False, str(exc)
                return True, ''

            async def save():
                payload = read_inputs(controls)
                ok, error_text = await db_call(write_record, payload)
                errors_container.clear()
                if not ok:
                    with errors_container:
                        ui.label(error_text).classes('text-red-700 text-sm')
                    return
                ui.notify(f'{title} berhasil disimpan.', type='positive')
                ui.navigate.to(back_url)

            with ui.row().classes('gap-3 mt-3'):
                ui.button('Simpan', icon='save', on_click=save).props('unelevated no-caps').classes('rounded-xl font-bold')
                nav_button('Kembali', back_url, icon='arrow_back')
            if model_type == 'products' and obj is None:
                ui.label('Stok awal hanya dapat dicatat saat pembuatan produk. Pastikan saldo awal akun persediaan sesuai.').classes('text-sm text-slate-500')
            if model_type == 'settings':
                ui.label('Nama usaha dan pemetaan akun memengaruhi seluruh laporan dan Excel.').classes('text-sm text-slate-500')


async def movement_editor(user):
    def read_form():
        form = MovementForm()
        return form, prepare_choices(form)

    form, choices = await db_call(read_form)
    with shell('Transaksi Persediaan', 'Pembelian dan penjualan membentuk jurnal otomatis dengan FIFO'):
        with ui.card().classes('w-full max-w-5xl p-6 gap-5 bg-white rounded-3xl border border-slate-200 shadow-sm'):
            controls = build_inputs(form, choices)
            errors = ui.column().classes('w-full')

            def write_movement(payload):
                bound = MovementForm(payload)
                if not bound.is_valid():
                    return None, err_text(bound.errors)
                data = bound.cleaned_data
                try:
                    movement = create_stock_movement(
                        product=data['product'], date_value=data['date'],
                        reference=data['reference'], kind=data['kind'],
                        quantity=data['quantity'], unit_price=data['unit_price'],
                        settlement_account=data['settlement_account'],
                        description=data['description'], party=data.get('party'), user=user)
                except (ValidationError, IntegrityError, ValueError) as exc:
                    return None, str(exc)
                return movement.product_id, ''

            async def save():
                product_id, error_text = await db_call(write_movement, read_inputs(controls))
                errors.clear()
                if product_id is None:
                    with errors:
                        ui.label(error_text).classes('text-red-700 text-sm')
                    return
                ui.notify('Mutasi dan jurnal otomatis berhasil dicatat.', type='positive')
                ui.navigate.to(f'/inventory?product={product_id}')

            ui.label('Stok tidak boleh negatif dan transaksi tidak boleh mundur tanggal.').classes('text-sm text-slate-500')
            with ui.row().classes('gap-3'):
                ui.button('Simpan Transaksi', icon='save', on_click=save).props('unelevated no-caps').classes('rounded-xl font-bold')
                nav_button('Kembali', '/inventory', icon='arrow_back')


async def journal_editor(kind, user):
    """Formset lama digunakan langsung untuk mencegah hilangnya validasi jurnal."""
    is_adjustment = kind == JournalEntry.Kind.ADJUSTMENT
    title = 'Tambah Jurnal Penyesuaian' if is_adjustment else 'Tambah Jurnal Umum'
    back = '/adjustments' if is_adjustment else '/journal'
    def load_initial():
        entry = JournalEntry(kind=kind)
        top_form = JournalEntryForm(instance=entry)
        top_form.fields.pop('kind', None)
        valid_accounts = {str(a.id): str(a) for a in Account.objects.filter(is_active=True, is_header=False)}
        parties = {'': '– Tidak ada –', **{str(p.id): str(p) for p in Party.objects.all()}}
        return entry, top_form, valid_accounts, parties, prepare_choices(top_form)

    entry, top_form, valid_accounts, parties, choices = await db_call(load_initial)
    controls = []
    with shell(title, 'Jurnal debet-kredit wajib seimbang dan minimal dua akun'):
        with ui.card().classes('w-full p-6 gap-5 bg-white rounded-3xl border border-slate-200 shadow-sm'):
            top_controls = build_inputs(top_form, choices)
            ui.separator()
            ui.label('Rincian akun').classes('font-extrabold text-slate-900 text-lg')
            holder = ui.column().classes('w-full gap-3')
            errors = ui.column().classes('w-full')
            balance_notice = ui.label('Debet Rp 0 | Kredit Rp 0 | Isi minimal dua baris').classes(
                'w-full rounded-xl bg-teal-50 border border-teal-100 p-3 text-sm font-bold text-teal-900')

            def update_totals():
                def amount(input_element):
                    try:
                        return Decimal(str(input_element.value or 0))
                    except (InvalidOperation, TypeError, ValueError):
                        return Decimal(0)
                debit_total = sum((amount(r['debit']) for r in controls), Decimal(0))
                credit_total = sum((amount(r['credit']) for r in controls), Decimal(0))
                difference = debit_total - credit_total
                state = 'SEIMBANG' if debit_total > 0 and difference == 0 else 'BELUM SEIMBANG'
                balance_notice.set_text(
                    f'Debet Rp {debit_total:,.2f}  |  Kredit Rp {credit_total:,.2f}  |  '
                    f'Selisih Rp {difference:,.2f}  ·  {state}'
                )

            def add_line():
                if len(controls) >= 30:
                    ui.notify('Maksimal 30 baris jurnal.', type='warning')
                    return
                with holder:
                    with ui.card().classes('w-full p-4 bg-slate-50 rounded-2xl border border-slate-200 shadow-none') as card:
                        with ui.row().classes('gap-2 items-center flex-wrap w-full'):
                            account = ui.select(valid_accounts, label='Akun', with_input=True).classes('w-full md:w-64').props('outlined dense')
                            party = ui.select(parties, label='Relasi', value='', with_input=True).classes('w-full md:w-52').props('outlined dense')
                            debit = ui.input('Debet', value='0', on_change=lambda _: update_totals()).props('outlined dense inputmode=decimal').classes('w-full md:w-36')
                            credit = ui.input('Kredit', value='0', on_change=lambda _: update_totals()).props('outlined dense inputmode=decimal').classes('w-full md:w-36')
                        description = ui.input('Keterangan baris (opsional)', value='').props('outlined dense').classes('w-full')
                        row = {'card': card, 'account': account, 'party': party,
                               'debit': debit, 'credit': credit, 'description': description}
                        ui.button('Hapus baris', icon='delete_outline', color='negative',
                                  on_click=lambda r=row: remove_line(r)).props('flat dense')
                        controls.append(row)
                        update_totals()

            def remove_line(row):
                if len(controls) <= 2:
                    ui.notify('Minimal 2 baris untuk jurnal.', type='warning')
                    return
                controls.remove(row)
                row['card'].delete()
                update_totals()

            add_line()
            add_line()
            ui.button('Tambah Baris', icon='add_circle_outline', on_click=add_line).props('outline no-caps').classes('rounded-xl')

            def write_journal(fields):
                bound_entry = JournalEntryForm(fields, instance=entry)
                bound_entry.fields.pop('kind', None)
                lines = JournalLineFormSet(fields, instance=entry, prefix='lines')
                entry_valid = bound_entry.is_valid()
                lines_valid = lines.is_valid()
                if not entry_valid or not lines_valid:
                    messages = []
                    if not entry_valid:
                        messages.append(err_text(bound_entry.errors))
                    if not lines_valid:
                        messages += [err_text(e) for e in lines.errors if e]
                        messages += list(map(str, lines.non_form_errors()))
                    return None, messages
                try:
                    with transaction.atomic():
                        saved = bound_entry.save(commit=False)
                        saved.kind = kind  # Jenis jurnal dipaksa di server
                        saved.created_by = user
                        saved.save()
                        lines.instance = saved
                        lines.save()
                except (ValidationError, IntegrityError, ValueError) as exc:
                    return None, [str(exc)]
                return saved.pk, []

            async def save():
                fields = read_inputs(top_controls)
                # Formset dipakai persis seperti POST Django untuk validasi asli.
                fields.update({'lines-TOTAL_FORMS': str(len(controls)),
                               'lines-INITIAL_FORMS': '0',
                               'lines-MIN_NUM_FORMS': '2',
                               'lines-MAX_NUM_FORMS': '30'})
                for index, row in enumerate(controls):
                    for key in ('account', 'party', 'description', 'debit', 'credit'):
                        value = row[key].value
                        fields[f'lines-{index}-{key}'] = '' if value is None else str(value)
                journal_pk, error_messages = await db_call(write_journal, fields)
                errors.clear()
                if journal_pk is None:
                    with errors:
                        for msg in error_messages:
                            ui.label(msg).classes('text-red-700 text-sm')
                    return
                ui.notify('Jurnal berpasangan berhasil dicatat.', type='positive')
                ui.navigate.to(f'/journal/{journal_pk}')

            with ui.row().classes('gap-3'):
                ui.button('Posting Jurnal', icon='save', on_click=save).props('unelevated no-caps').classes('rounded-xl font-bold')
                nav_button('Kembali', back, icon='arrow_back')
