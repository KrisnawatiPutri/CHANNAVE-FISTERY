"""Uji statis batas async UI / Django, tanpa mengimpor Django atau NiceGUI.

Tidak menggantikan tes runtime. Jalankan:
    python -m unittest tests_migrasi.test_async_ui_static -v
"""
import ast
import asyncio
import inspect
from types import SimpleNamespace
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


def parse(name):
    return ast.parse((ROOT / name).read_text(encoding='utf-8'))


class AsyncUIBoundaryStaticTest(unittest.TestCase):
    def test_all_protected_routes_are_async(self):
        module = parse('nicegui_app/pages.py')
        protected = [node for node in module.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                     and any(isinstance(d, ast.Name) and d.id == 'with_user' for d in node.decorator_list)]
        self.assertEqual(len(protected), 24)
        self.assertTrue(all(isinstance(node, ast.AsyncFunctionDef) for node in protected))

    def test_auth_queries_are_awaited(self):
        module = parse('nicegui_app/pages.py')
        auth = next(node for node in module.body if isinstance(node, ast.AsyncFunctionDef)
                    and node.name == 'current_user')
        self.assertTrue(any(isinstance(node, ast.Await) and isinstance(node.value, ast.Call)
                            and isinstance(node.value.func, ast.Name) and node.value.func.id == 'db_call'
                            for node in ast.walk(auth)))

    def test_editors_are_async_and_option_queries_are_prepared(self):
        module = parse('nicegui_app/editor.py')
        functions = {node.name: node for node in module.body
                     if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
        for name in ('model_editor', 'movement_editor', 'journal_editor'):
            self.assertIsInstance(functions[name], ast.AsyncFunctionDef)
        self.assertIn('prepare_choices(form)', (ROOT/'nicegui_app/editor.py').read_text())

    def test_auth_wrapper_runtime_contract_without_dependencies(self):
        """Jalankan hanya fungsi auth yang diekstrak, dengan db_call tiruan."""
        tree = parse('nicegui_app/pages.py')
        names = {'_load_active_user', 'current_user', 'with_user'}
        funcs = [node for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                 and node.name in names]
        calls = []
        async def fake_db_call(function, uid):
            calls.append(uid)
            return SimpleNamespace(pk=uid)
        storage = SimpleNamespace(user={'uid': 7})
        nav = []
        scope = {
            'app': SimpleNamespace(storage=storage),
            'ui': SimpleNamespace(navigate=SimpleNamespace(to=nav.append)),
            'db_call': fake_db_call,
            'get_user_model': lambda: None,
        }
        exec(compile(ast.fix_missing_locations(ast.Module(body=funcs, type_ignores=[])),
                     '<auth snippet>', 'exec'), scope)
        async def page(user):
            return user.pk
        secured = scope['with_user'](page)
        self.assertEqual(str(inspect.signature(secured)), '()')
        self.assertEqual(asyncio.run(secured()), 7)
        self.assertEqual(calls, [7])
        self.assertEqual(nav, [])

    def test_no_unsafe_orm_bypass(self):
        for file in (ROOT/'nicegui_app').glob('*.py'):
            self.assertNotIn('DJANGO_ALLOW_ASYNC_UNSAFE', file.read_text())


if __name__ == '__main__':
    unittest.main()
