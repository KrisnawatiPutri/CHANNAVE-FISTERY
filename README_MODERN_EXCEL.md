# PANDUAN | CHANNAVE FISHERY MODERN UI + EXCEL DINAMIS

## Apa yang diperbaiki

1. **Dashboard modern**: navigasi desktop/mobile, kartu KPI, tren pendapatan-biaya, akses cepat, tabel dengan pencarian/paginasi dan kontrol periode.
2. **Form responsif**: field disusun dalam grid dua kolom pada desktop dan satu kolom pada ponsel.
3. **Jurnal interaktif**: saat mengisi debet/kredit, total dan selisih langsung terlihat. Server tetap menggunakan validasi Django `BalancedJournalFormSet` untuk memastikan jurnal berpasangan.
4. **Excel terhubung**: seluruh laporan dalam satu file `.xlsx` berbasis rumus. Dua sheet baru, `RINGKASAN` dan `PANDUAN`, menambah ringkasan keuangan dan instruksi pengeditan.
5. **Kontrol konsistensi**: selisih jurnal umum, jurnal penyesuaian, neraca saldo, neraca, dan saldo stok negatif ditampilkan pada RINGKASAN.
6. **Penamaan**: aplikasi, halaman, dan nama file ekspor menggunakan Channave Fishery.

## Struktur utama

```text
Channave_Fishery_Modern_NiceGUI/
├── nicegui_app/
│   ├── main.py               # Server NiceGUI
│   ├── layout.py             # Tema, header, sidebar, komponen UI
│   ├── pages.py              # Dashboard, laporan, transaksi, login
│   ├── editor.py             # Form dengan validasi Django asli
│   ├── db.py                 # ORM Django lewat worker thread (mencegah Error 500 async)
│   └── branding.py           # Identitas Channave Fishery
├── accounting/
│   ├── models.py             # Schema database lama, tidak diubah
│   ├── forms.py              # Validasi lama, tidak diubah
│   ├── services.py           # FIFO dan laporan keuangan lama, tidak diubah
│   └── exports.py            # Excel dengan formula dan ringkasan baru
├── config/                   # Konfigurasi Django ORM
├── contoh_hasil_ekspor/       # Workbook DEMO, bukan data usaha Anda
├── tests_migrasi/            # Unit tests Django dan pemeriksaan async
├── requirements_nicegui.txt
└── manage.py
```

## Instalasi Windows (VS Code)

1. Cadangkan folder versi lama dan `db.sqlite3` jika sudah dipakai.
2. Ekstrak ZIP ini ke folder baru, lalu buka folder proyek (yang berisi `manage.py`) di VS Code.
3. Di terminal PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements_nicegui.txt
python manage.py makemigrations accounting
python manage.py migrate
python manage.py createsuperuser
```

`createsuperuser` cukup sekali untuk database baru. Bila sudah punya database lama, salin **cadangannya** ke folder proyek ini sebelum `makemigrations` dan `migrate`, kemudian **jangan** buat ulang akun maupun jalankan seed demo.

**Opsional hanya untuk database baru kosong:**

```powershell
python manage.py seed_perikanan --demo
```

Buat token penyimpanan sesi yang kuat:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
$env:CHANNAVE_STORAGE_SECRET = "TEMPEL_TOKEN_UNIK_DI_SINI"
python -m nicegui_app.main
```

Buka `http://127.0.0.1:8080/login`. **Jalankan ini, bukan `python manage.py runserver`**, karena halaman UI berada pada NiceGUI port 8080.

Untuk menjalankan ulang setelah instalasi:

```powershell
.\.venv\Scripts\Activate.ps1
$env:CHANNAVE_STORAGE_SECRET = "TOKEN_UNIK_YANG_SAMA"
python -m nicegui_app.main
```

Di server publik, konfigurasi HTTPS, autentikasi, backup, dan database yang sesuai beban harus dikerjakan sebelum produksi. SQLite cocok untuk prototipe dan penggunaan terbatas.

## Alur Excel yang otomatis mengikuti perubahan

```text
AKUN + KODE + JURNAL UMUM + JURNAL PENYESUAIAN
           |                   |
           v                   v
      BUKU BESAR         NERACA LAJUR
           |                   |
           v                   v
      NERACA SALDO     LABA RUGI + NERACA
                               |
INVENTORY CARD -> PRODUK       |
       |                       |
       +-> HPP/FIFO -> JURNAL -+
                               v
                           RINGKASAN
```

**Contoh nyata dari workbook demo:** Ubah harga beli di `INVENTORY CARD!I6` dari **22.000** menjadi **25.000**. Dengan transaksi lainnya tetap sama, HPP penjualan berubah dari **2.220.000** menjadi **2.250.000**, laba dari **1.080.000** menjadi **1.050.000**, stok FIFO akhir dari **440.000** menjadi **500.000**, dan total aset dari **23.080.000** menjadi **23.050.000**. Neraca tetap seimbang. Hasil tersebut diuji menggunakan workbook yang dihasilkan generator dan mesin evaluasi formula spreadsheet.

**Cara mencoba:** Dashboard > Ekspor Excel (lengkap). Buka file `.xlsx` dengan Microsoft Excel. Pada bagian **Formulas > Calculation Options**, pilih **Automatic**. Setelah mengubah jumlah/harga atau nilai jurnal pada sel input biru, cek sheet `RINGKASAN` dan hasilnya pada sheet `PRODUK`, `INVENTORY CARD`, `NERACA LAJUR`, `LABA RUGI`, atau `NERACA`. Jika belum berubah, tekan **Ctrl+Alt+F9**.

**Batas yang harus dipahami:**

- Edit **angka di baris yang sudah diekspor** mengubah perhitungan turunan di workbook. Jangan mengganti sel formula hijau/hitam.
- Menambah, menghapus, mengurutkan, atau mengubah **pemetaan akun/produk/tanggal transaksi** bisa mengubah kelompok detail FIFO/buku besar; lakukan pada aplikasi lalu **ekspor ulang**.
- File Excel hanya menyalin data sampai tanggal ekspor. **Perubahan di Excel TIDAK mengirim data kembali ke aplikasi/database**.
- Excel Desktop dengan kalkulasi otomatis dianjurkan. Penampil XLSX tertentu hanya menampilkan formula atau cache hasil; sebagian aplikasi mobile memiliki keterbatasan penghitungan ulang.
- Total perhitungan bersumber dari data jurnal; gunakan `RINGKASAN` untuk memeriksa selisih jurnal, neraca, dan stok.

## Pengujian

Pemeriksaan sintaks dan batas async dapat dilakukan tanpa server:

```powershell
python -m compileall -q accounting nicegui_app tests_migrasi
python -m unittest tests_migrasi.test_async_ui_static -v
```

Setelah dependensi terinstal, jalankan pengujian database dan Excel:

```powershell
python manage.py test tests_migrasi -v 2
```

**Status validasi paket ini:** sintaks Python lolos; lima tes statis batas async lolos; generator Excel diuji dengan data tiruan dan dilakukan uji perubahan harga melalui evaluasi ulang formula antarsheet. Server NiceGUI/Django belum bisa diuji secara langsung di lingkungan pembuatan karena paket Django/NiceGUI tidak dapat diinstal di sana. Uji login, penyimpanan jurnal, dashboard, dan ekspor di Windows tetap perlu dilakukan sebelum digunakan dengan data asli.

## Perubahan inti vs yang dipertahankan

File yang diubah terutama `nicegui_app/layout.py`, `nicegui_app/pages.py`, `nicegui_app/editor.py`, dan `accounting/exports.py`. Schema `models.py`, validasi `forms.py`, algoritma FIFO/laporan `services.py`, serta jalur koneksi `nicegui_app/db.py` dipertahankan. `tests_migrasi/test_excel_linked.py` adalah pengujian tambahan.
