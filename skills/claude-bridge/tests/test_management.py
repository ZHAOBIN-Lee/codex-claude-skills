from contextlib import redirect_stderr, redirect_stdout
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock

MANAGER = Path(__file__).resolve().parents[1] / 'lib' / 'management.py'
SPEC = importlib.util.spec_from_file_location('workflow_management_under_test', MANAGER)
management = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(management)


class RollbackTests(unittest.TestCase):
    def fixture(self, root):
        owned = root / 'owned.txt'
        owned.write_text('installed\n')
        manifest = root / 'installation.json'
        manifest.write_text(json.dumps({'installed_files': [{
            'path': str(owned), 'sha256': hashlib.sha256(owned.read_bytes()).hexdigest()
        }]}))
        return owned, manifest

    def run_manager(self, manifest, *args, inventory='1 /sbin/launchd\n',
                    ps_returncode=0, ps_error=None):
        # Only the whole-machine process inventory is synthetic. Hash checks,
        # symlink checks, quarantine renames and restore metadata stay real.
        argv = [str(MANAGER), '--manifest', str(manifest), *args]
        stdout, stderr = io.StringIO(), io.StringIO()

        def fake_ps(command, **kwargs):
            self.assertEqual(command, ['/bin/ps', '-axo', 'pid=,comm='])
            self.assertEqual(kwargs, {'capture_output': True, 'text': True, 'timeout': 10})
            if ps_error is not None:
                raise ps_error
            return subprocess.CompletedProcess(command, ps_returncode, inventory, '')

        with mock.patch.object(management.sys, 'argv', argv), \
                mock.patch.object(management.subprocess, 'run', side_effect=fake_ps) as ps, \
                redirect_stdout(stdout), redirect_stderr(stderr):
            returncode = management.main()
        result = subprocess.CompletedProcess(argv, returncode, stdout.getvalue(), stderr.getvalue())
        result.ps_calls = ps.call_count
        return result

    def test_check_never_changes_installed_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            owned, manifest = self.fixture(root)
            r = self.run_manager(manifest, '--check')
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertEqual(owned.read_text(), 'installed\n')
            self.assertEqual(r.ps_calls, 0)
            self.assertFalse(list(root.glob('rollback-*')))

    def test_rollback_quarantines_only_manifest_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            owned, manifest = self.fixture(root)
            other = root / 'user.txt'
            other.write_text('keep me')
            original_sha256 = hashlib.sha256(owned.read_bytes()).hexdigest()
            r = self.run_manager(manifest, '--apply')
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertFalse(owned.exists())
            self.assertEqual(other.read_text(), 'keep me')
            self.assertEqual(r.ps_calls, 1)
            result = json.loads(r.stdout)
            self.assertEqual(result['status'], 'rolled_back')
            folder = Path(result['quarantine'])
            self.assertEqual(folder.parent, root)
            records = json.loads((folder / 'restore.json').read_text())['moved_files']
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0]['original'], str(owned))
            quarantined = Path(records[0]['quarantined'])
            self.assertEqual(quarantined.parent, folder)
            self.assertEqual(hashlib.sha256(quarantined.read_bytes()).hexdigest(), original_sha256)
            self.assertEqual(set(folder.iterdir()), {quarantined, folder / 'restore.json'})

    def test_running_desktop_native_blocks_and_preserves_all_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            owned, manifest = self.fixture(root)
            other = root / 'user.txt'
            other.write_text('keep me')
            before = {path: path.read_bytes() for path in (owned, manifest, other)}
            inventory = ('1 /sbin/launchd\n'
                         '245 /Users/example/Library/Application Support/Claude/claude-code/'
                         '2.1.286/native/claude.app/Contents/MacOS/claude\n')
            r = self.run_manager(manifest, '--apply', inventory=inventory)
            self.assertEqual(r.returncode, 2)
            self.assertIn('Claude CLI 仍在运行', r.stderr)
            self.assertEqual(r.ps_calls, 1)
            self.assertEqual({path: path.read_bytes() for path in before}, before)
            self.assertFalse(list(root.glob('rollback-*')))

    def test_failed_process_inventory_blocks_and_preserves_all_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            owned, manifest = self.fixture(root)
            before = {path: path.read_bytes() for path in (owned, manifest)}
            r = self.run_manager(manifest, '--apply', ps_returncode=1)
            self.assertEqual(r.returncode, 2)
            self.assertIn('无法确认原生 CLI', r.stderr)
            self.assertEqual(r.ps_calls, 1)
            self.assertEqual({path: path.read_bytes() for path in before}, before)
            self.assertFalse(list(root.glob('rollback-*')))

    def test_timed_out_process_inventory_blocks_and_preserves_all_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            owned, manifest = self.fixture(root)
            before = {path: path.read_bytes() for path in (owned, manifest)}
            r = self.run_manager(manifest, '--apply',
                                 ps_error=subprocess.TimeoutExpired(['/bin/ps'], 10))
            self.assertEqual(r.returncode, 2)
            self.assertEqual(r.ps_calls, 1)
            self.assertEqual({path: path.read_bytes() for path in before}, before)
            self.assertFalse(list(root.glob('rollback-*')))

    def test_drift_stops_whole_rollback(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            owned, manifest = self.fixture(root)
            owned.write_text('new user edit\n')
            r = self.run_manager(manifest, '--apply')
            self.assertNotEqual(r.returncode, 0)
            self.assertIn('漂移', r.stdout + r.stderr)
            self.assertEqual(owned.read_text(), 'new user edit\n')

    def test_symlink_is_not_followed_or_removed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            owned, manifest = self.fixture(root)
            target = root / 'user-target.txt'
            target.write_text('installed\n')
            owned.unlink()
            owned.symlink_to(target)
            r = self.run_manager(manifest, '--apply')
            self.assertNotEqual(r.returncode, 0)
            self.assertTrue(owned.is_symlink())
            self.assertEqual(target.read_text(), 'installed\n')

    def test_one_drifted_file_preserves_every_owned_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            owned, manifest = self.fixture(root)
            second = root / 'second.txt'
            second.write_text('original')
            data = json.loads(manifest.read_text())
            data['installed_files'].append({'path': str(second),
                'sha256': hashlib.sha256(second.read_bytes()).hexdigest()})
            manifest.write_text(json.dumps(data))
            second.write_text('user edit')
            r = self.run_manager(manifest, '--apply')
            self.assertNotEqual(r.returncode, 0)
            self.assertTrue(owned.exists())
            self.assertEqual(second.read_text(), 'user edit')


if __name__ == '__main__':
    unittest.main()
