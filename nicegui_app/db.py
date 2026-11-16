"""Panggil Django ORM sinkron dari handler NiceGUI async dengan aman."""

from django.db import close_old_connections
from nicegui import run


async def db_call(function, *args, **kwargs):
    """I/O Django di thread pekerja; UI tetap digambar di event loop.

    Django melarang ORM sinkron langsung dalam coroutine. Connection Django
    juga harus ditutup pada batas kerja karena NiceGUI bukan HTTP request Django.
    """
    def work():
        close_old_connections()
        try:
            return function(*args, **kwargs)
        finally:
            close_old_connections()

    return await run.io_bound(work)
