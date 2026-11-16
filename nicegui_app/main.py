"""Jalankan Channave Fishery NiceGUI: python -m nicegui_app.main"""
import os

# Izinkan Django ORM dipanggil di dalam async event loop NiceGUI
os.environ.setdefault('DJANGO_ALLOW_ASYNC_UNSAFE', 'true')

from nicegui import ui
from .branding import APP_WINDOW_TITLE

# Bootstrap Django ORM, tidak menjalankan Django HTTP/views.
from . import backend  # noqa: F401
from . import pages  # noqa: F401  (registrasi route)


def env_setting(new_key, legacy_key, default=None):
    """Transisi branding tanpa memutus konfigurasi MinaBooks lama."""
    return os.environ.get(new_key) or os.environ.get(legacy_key) or default


def main():
    secret = env_setting('CHANNAVE_STORAGE_SECRET', 'MINABOOKS_STORAGE_SECRET', '')
    if not secret:
        if os.environ.get('DJANGO_DEBUG', '1') != '1':
            raise RuntimeError('Isi CHANNAVE_STORAGE_SECRET dengan nilai acak panjang di server produksi.')
        secret = 'khusus-pengembangan-lokal-jangan-dipakai-publik'

    # Otomatis pakai 0.0.0.0 jika berjalan di server Render (ada variabel PORT), atau 127.0.0.1 jika lokal
    default_host = '0.0.0.0' if os.environ.get('PORT') else '127.0.0.1'
    default_port = os.environ.get('PORT', '8080')

    ui.run(
        title=APP_WINDOW_TITLE,
        favicon='🐟',
        storage_secret=secret,
        host=env_setting('CHANNAVE_HOST', 'MINABOOKS_HOST', default_host),
        port=int(env_setting('CHANNAVE_PORT', 'MINABOOKS_PORT', default_port)),
        reload=False,
        language='id',
        session_middleware_kwargs={
            'https_only': env_setting('CHANNAVE_HTTPS_ONLY', 'MINABOOKS_HTTPS_ONLY', '0') == '1'
        },
    )


if __name__ == '__main__':
    main()