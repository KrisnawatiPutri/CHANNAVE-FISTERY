# Perbaikan Error 500 SynchronousOnlyOperation

**Tanggal:** 16 November 2026  
**Produk:** Channave Fishery (NiceGUI Python Only)

## Mengapa halaman /dashboard error?

NiceGUI menjalankan page handler sebagai coroutine. Pada versi sebelumnya, `nicegui_app/pages.py` menjalankan `get_user_model().objects.filter(...)` langsung dari `current_user()`. Django melarang ORM sinkron ketika dipanggil di dalam event loop asinkron, sehingga menampilkan HTTP 500 `SynchronousOnlyOperation`.

Selain autentikasi, pemanggilan queryset serupa ditemukan saat render awal dashboard, jurnal, laporan, daftar akun, data produk, dan form Django yang memakai `ModelChoiceField`.

## Perubahan source code

1. `nicegui_app/pages.py`: `with_user()` menjadi async; `current_user()` memuat pengguna melalui `await db_call(...)`.
2. Seluruh handler halaman yang dilindungi autentikasi menjadi async.
3. Pembacaan data dan pilihan dropdown dilakukan menggunakan `db_call` melalui worker thread sebelum dibuat widget UI.
4. `nicegui_app/editor.py`: editor model, persediaan, dan jurnal menjadi async dan mengevaluasi pilihan form di worker thread.
5. **Tidak mengubah** `accounting/models.py`, `accounting/forms.py`, `accounting/services.py`, atau `accounting/exports.py` maupun skema database.

Tidak menggunakan `DJANGO_ALLOW_ASYNC_UNSAFE` karena membuka kemungkinan transaksi rusak atau akses ORM tidak aman.

## Cara memperbaiki proyek yang sudah ada di Windows

1. Matikan server NiceGUI di terminal VS Code menggunakan `Ctrl + C`.
2. Salin proyek atau minimal database `db.sqlite3` untuk cadangan. Jangan menghapus database lama.
3. Dari paket perbaikan, salin berkas berikut ke proyek yang sedang digunakan, **gantikan versi lamanya**:
   - `nicegui_app/pages.py`
   - `nicegui_app/editor.py`
4. **Jangan** menyalin folder proyek utuh di atas instalasi yang memuat database atau `.env` tanpa mencadangkannya.
5. Aktifkan virtual environment dan jalankan server:

   ```powershell
   .\.venv\Scripts\Activate.ps1
   python -m nicegui_app.main
   ```

6. Buka `http://127.0.0.1:8080/login`, login, lalu buka `/dashboard`.
7. Uji menu jurnal, produk, persediaan, dan ekspor Excel secara berurutan di data uji.

Jika paket ini digunakan sebagai proyek baru, ikuti `README_CHANNAVE.md` untuk memasang dependensi dan menyiapkan database.

## Pemeriksaan

- Semua berkas `.py` lolos pemeriksaan sintaks Python (`compileall`).
- 24 route terproteksi menggunakan async wrapper.
- Berkas akuntansi inti tidak berubah dibanding versi sebelumnya.
- Tes statis `tests_migrasi/test_async_ui_static.py` ditambahkan.
- **Tes langsung browser, migrasi DB, login, dan transaksi belum dapat dijalankan di lingkungan penyusunan paket karena Django dan NiceGUI tidak terpasang serta akses pemasangan dependensi terhambat koneksi.** Jika error masih muncul, lihat traceback lengkap terminal untuk menemukan fungsi berikutnya yang memanggil ORM secara sinkron.
