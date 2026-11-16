# Ringkasan Perubahan Nama & Tampilan

## Dikerjakan

- Nama: MinaBooks → **Channave Fishery** di halaman login, sidebar, header, judul tab, footer, dan seluruh label yang menunjuk nama aplikasi.
- Tema: biru laut, toska, putih; layout responsif, sidebar per kategori, login dua panel, statistik dan grafik dashboard.
- Nama ekspor dari UI NiceGUI: `channave_fishery_<jenis>_<tanggal>.xlsx`.
- Konfigurasi branding: `nicegui_app/branding.py`; setting server `CHANNAVE_*` dengan kompatibilitas `MINABOOKS_*`.
- Perintah seed perikanan memberikan nama **Channave Fishery** hanya pada database baru dengan profil bawaan pertanian.

## Sengaja tidak diubah

- `accounting/models.py`, `accounting/forms.py`, `accounting/services.py`, dan `accounting/exports.py`.
- Seluruh URL route NiceGUI, pemetaan akun, FIFO, jurnal otomatis, dan rumus ekspor Excel.
- Nama bisnis yang sudah disimpan pada database lama.
- Perintah `seed_agriculture.py` yang sudah ada agar perilaku backend historis tetap dapat ditelusuri.

## Pengujian

Pemeriksaan sintaks dan integritas file core dilakukan tanpa instalasi Django/NiceGUI. Pengujian runtime, login, transaksi, grafik, Excel, dan Android WebView masih diperlukan di mesin dengan dependensi terinstal.
