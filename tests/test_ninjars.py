"""NinjaRS prerequisite, integrity and transactional-publication regressions."""
import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

SCRIPT = Path(__file__).resolve().parents[1] / 'HEPToolInstaller.py'
SPEC = importlib.util.spec_from_file_location('heptools_ninjars_test', SCRIPT)
installer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(installer)


class TestNinjaRS(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.prefix = self.root / 'prefix'
        self.prefix.mkdir()
        self.stage = self.prefix / '.stage'
        self.stage.mkdir()
        self.installed = self.stage / 'install'
        self.destination = self.prefix / 'ninjars'
        self.payload(self.installed, 'new')

    @staticmethod
    def payload(path, marker):
        for directory, names in [('lib', installer._ninjars_lib_files),
                                 ('include', ['ninjars.h', 'mninjars.f90'])]:
            (path / directory).mkdir(parents=True)
            for name in names:
                (path / directory / name).write_text(marker + ':' + name)

    @staticmethod
    def snapshot(path):
        result = {}
        for item in path.rglob('*'):
            if '.stage' in item.relative_to(path).parts:
                continue
            name = str(item.relative_to(path))
            if item.is_symlink():
                result[name] = ('link', os.readlink(item))
            elif item.is_file():
                result[name] = ('file', item.read_bytes())
            elif item.is_dir():
                result[name] = ('dir', None)
        return result

    def previous(self):
        self.payload(self.destination, 'old')
        for directory, names in [('lib', installer._ninjars_lib_files),
                                 ('include', ['ninjars.h', 'mninjars.f90'])]:
            (self.prefix / directory).mkdir()
            for name in names:
                (self.prefix / directory / name).symlink_to('../ninjars/' + directory + '/' + name)
        (self.prefix / 'lib/mninjars.mod').unlink()
        (self.prefix / 'lib/mninjars.mod').symlink_to('../deliberately-dangling.mod')

    def publish(self):
        return installer._publish_ninjars(self.installed, self.destination, self.stage, self.prefix)

    def fail_alias_replace(self):
        original = os.replace
        calls = []

        def replace(source, target):
            if '/new/' in str(source):
                calls.append(target)
                if len(calls) == 3:
                    raise OSError('injected alias replacement failure')
            return original(source, target)
        return mock.patch.object(installer.os, 'replace', side_effect=replace)

    def test_success_publishes_both_alias_groups(self):
        self.previous()
        self.publish()
        for directory, names in [('lib', installer._ninjars_lib_files),
                                 ('include', ['ninjars.h', 'mninjars.f90'])]:
            for name in names:
                alias = self.prefix / directory / name
                self.assertTrue(alias.is_symlink())
                self.assertEqual(alias.read_text(), 'new:' + name)

    def test_alias_failure_restores_tree_and_relative_dangling_links(self):
        self.previous()
        before = self.snapshot(self.prefix)
        with self.fail_alias_replace(), self.assertRaisesRegex(OSError, 'injected'):
            self.publish()
        self.assertEqual(self.snapshot(self.prefix), before)
        self.assertTrue(self.installed.is_dir())

    def test_first_install_failure_removes_created_common_directories(self):
        before = self.snapshot(self.prefix)
        with self.fail_alias_replace(), self.assertRaisesRegex(OSError, 'injected'):
            self.publish()
        self.assertEqual(self.snapshot(self.prefix), before)
        self.assertFalse(self.destination.exists())

    def test_regular_alias_file_is_preserved_and_refused(self):
        self.previous()
        alias = self.prefix / 'lib/libninjars.a'
        alias.unlink()
        alias.write_text('user-owned regular archive')
        before = self.snapshot(self.prefix)
        with self.assertRaisesRegex(OSError, 'user file'):
            self.publish()
        self.assertEqual(self.snapshot(self.prefix), before)

    def test_common_library_directory_may_be_a_symlink(self):
        actual = self.root / 'shared-libraries'
        actual.mkdir()
        (self.prefix / 'lib').symlink_to(actual, target_is_directory=True)
        self.publish()
        alias = actual / 'libninjars.a'
        self.assertEqual(alias.resolve(), self.destination / 'lib/libninjars.a')
        self.assertEqual(alias.read_text(), 'new:libninjars.a')

    def test_unsupported_platform_is_refused_without_mutation(self):
        self.previous()
        before = self.snapshot(self.prefix)
        with mock.patch.object(installer.sys, 'platform', 'darwin'), \
                mock.patch.object(installer, '_prefix', str(self.prefix)), \
                mock.patch.object(installer, 'find_executable', return_value='/tool'), \
                mock.patch.object(installer, 'get_program_output', return_value='rustc 1.98.1'), \
                mock.patch.object(installer, '_tarballs_specified', ['ninjars']):
            problems = installer.check_ninjars_prerequisites()
        self.assertTrue(any('only supported on Linux' in p for p in problems))
        self.assertEqual(self.snapshot(self.prefix), before)

    def test_official_archive_hash_mismatch_stops_before_build(self):
        archive = self.root / 'wrong.tar.gz'
        archive.write_bytes(b'wrong archive')
        tool = dict(installer._HepTools['ninjars'], install_path=str(self.installed),
                    tarball=['local', str(archive)], sha256='0'*64)
        with mock.patch.dict(installer._HepTools, ninjars=tool), \
                mock.patch.object(installer, '_tarballs_specified', []), \
                mock.patch.object(installer.subprocess, 'call') as build:
            self.assertEqual(installer._build_ninjars(str(self.root)), 1)
        build.assert_not_called()
        self.assertIn('sha256 mismatch', (self.installed / 'ninjars_install.log').read_text())

    def test_failed_staged_build_preserves_old_installation(self):
        self.previous()
        before = self.snapshot(self.prefix)
        tool = dict(installer._HepTools['ninjars'], install_path=str(self.destination))
        with mock.patch.dict(installer._HepTools, ninjars=tool), \
                mock.patch.object(installer, '_prefix', str(self.prefix)), \
                mock.patch.object(installer, '_build_ninjars', return_value=42):
            self.assertEqual(installer.install_ninjars(str(self.root)), 42)
        self.assertEqual(tool['install_path'], str(self.destination))
        after = {key: value for key, value in self.snapshot(self.prefix).items()
                 if not key.startswith('.ninjars-install-')}
        self.assertEqual(after, before)


if __name__ == '__main__':
    unittest.main()
