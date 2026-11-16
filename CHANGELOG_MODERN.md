# Perubahan Channave Fishery Modern NiceGUI

- Seluruh UI tetap dibangun dengan komponen NiceGUI dari Python (tidak menambah HTML/CSS/JS buatan sendiri).
- Sidebar modern dengan pengelompokan menu; header dan hero baru; dashboard 8 KPI, 4 akses cepat, grafik area interaktif, dan aktivitas jurnal.
- Form input responsif dua kolom; jurnal langsung menampilkan total debet/kredit dan selisih (validasi server lama tetap dipakai).
- Ekspor memiliki 14 sheet: 12 sheet asli + `RINGKASAN` + `PANDUAN`.
- Kontrol formula dan indikator pemeriksaan pembukuan baru, serta nama ekspor `channave_fishery_...xlsx`.
- Rumus Excel antarsheet dan FIFO memproses perubahan nilai pada sel input lama, tanpa memperbarui database aplikasi.
- Perbaikan error async pada versi sebelumnya tetap dipertahankan (`db_call` via worker thread).
- Ditambah workbook DEMO yang menunjukkan tautan antarsheet dan pengujian formula Django.

> Batas: menambah/mengurutkan transaksi, mengubah kode akun/produk, mengubah struktur lot FIFO memerlukan ekspor ulang. Belum dilakukan uji server NiceGUI end-to-end pada lingkungan ini.
