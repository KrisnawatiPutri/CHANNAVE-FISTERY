> Catatan: ini adalah rencana migrasi lama. Implementasi dan petunjuk terbaru ada di **README_MODERN_EXCEL.md**.

# Rencana Struktur & Migrasi Channave Fishery ke NiceGUI

## Target

Pengembang menulis **antarmuka dengan Python** (NiceGUI). Django tetap dipakai untuk model, ORM, autentikasi pengguna dan fungsi akuntansi. Tidak ada penulisan ulang FIFO, buku besar, neraca, atau ekspor Excel. Browser tetap memuat HTML/CSS/JS internal NiceGUI.

## Struktur proyek (versi baru)

```text
Channave_Fishery_NiceGUI/
├── nicegui_app/
│   ├── __init__.py
│   ├── main.py         # launcher server NiceGUI
│   ├── backend.py      # bootstrap Django ORM dan impor services
│   ├── layout.py       # sidebar, header, tabel, komponen UI Python
│   ├── editor.py       # formulir akun, produk, jurnal, transaksi stok
│   ├── pages.py        # halaman login, dashboard, laporan, inventory
│   └── formatting.py   # format Rupiah/angka/tanggal Indonesia
├── accounting/
│   ├── models.py       # sama dengan backend sebelumnya
│   ├── forms.py        # validasi lama dipakai ulang
│   ├── services.py     # FIFO, neraca, buku besar, HPP (tidak diubah)
│   ├── exports.py      # Excel rumus aktif (tidak diubah)
│   └── management/     # perintah seed data perikanan
├── config/             # konfigurasi Django ORM
├── manage.py           # migrasi DB, buat superuser, seed
├── requirements.txt
├── requirements_nicegui.txt
└── README_NICEGUI.md
```

## Integrasi bisnis

```
Browser / Android WebView
         |
   NiceGUI (Python)
         |
  Django ORM + ModelForm
         |
models.py + services.py + exports.py
         |
  Database (SQLite saat development)
```

## Tahap migrasi

| Tahap | Detail | Status |
|---|---|---|
| 1 | Audit source ZIP dan repository publik | Selesai sebagian; GitHub tidak dapat dikloning, data dari ZIP lokal |
| 2 | Bootstrap Django ORM ke NiceGUI | Kode disiapkan |
| 3 | Desain shell, login, navigasi, tabel & filter | Kode disiapkan |
| 4 | Migrasi form CRUD produk/akun/kode & pengaturan | Kode disiapkan |
| 5 | Jurnal Umum, Penyesuaian, laporan, FIFO | Kode disiapkan dengan layanan lama |
| 6 | Excel terhubung dan download | Kode disiapkan dengan pembuat workbook asli |
| 7 | Pengujian end-to-end NiceGUI di runtime | Belum, perlu instal Django dan NiceGUI |
| 8 | Validasi dataset historis, transaksi multiuser, Android WebView | Belum |
| 9 | Deploy & switch domain server lama | Belum |

**Status 'kode disiapkan' bukan berarti fitur sudah lolos uji runtime.** Setelah install, langkah penting adalah menjalankan tes backend, menguji halaman di browser, membandingkan laporan dengan versi lama dan menguji proses ekspor.

## Risiko yang wajib ditutup sebelum produksi

1. **Autentikasi:** NiceGUI menyimpan identitas login di storage server berbasis cookie bertanda tangan, berbeda dari Django session. Harus diuji sesi, logout, HTTPS dan pembatasan login.
2. **Konsistensi laporan:** Setiap skenario transaksi dan angka laporan perlu dicocokkan dengan Django lama.
3. **Excel di APK:** Download `blob` melalui WebView dapat memerlukan tambahan penanganan Android native, meskipun berfungsi di browser biasa.
4. **SQL concurrency:** SQLite dan proses sinkron Django membatasi kapasitas server; evaluasi database PostgreSQL dan beban multiuser jika akan dipakai bersama secara online.
5. **Rollback:** Backup database serta project Django asli sebelum migrasi. Jangan aktifkan migrasi pada database produksi sebelum hasil uji cocok.

## Kriteria penerimaan

- Jurnal umum/penyesuaian tidak tersimpan bila tidak balance.
- Mutasi stok IN/OUT menghasilkan HPP FIFO, jurnal otomatis, lapisan yang tepat; stok negatif dan backdate tetap ditolak.
- Data master tidak menerima kode duplikat; penyesuaian akun yang sudah bertransaksi tetap dibatasi.
- Neraca saldo, neraca lajur, laba rugi dan neraca sama persis untuk tanggal sama.
- Workbook `.xlsx` berisi sheet dan formula yang sama dengan versi Django lama.
- URL yang sensitif tidak bisa diakses tanpa login, juga saat refresh dan penggantian tab.
- Semua halaman tetap bisa dipakai di layar HP, dan unduhan Excel diuji di Android WebView.
