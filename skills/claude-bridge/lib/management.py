#!/usr/bin/env python3
"""Drift-safe, reversible removal of this installation's exact owned files."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import uuid


def checked_files(manifest):
    if manifest.is_symlink() or not manifest.is_file():
        raise ValueError('安装清单缺失或为符号链接。')
    data = json.loads(manifest.read_text())
    records = data.get('installed_files')
    if not isinstance(records, list) or not records:
        raise ValueError('安装清单没有有效文件。')
    files, seen = [], set()
    for entry in records:
        path = Path(entry['path'])
        if not path.is_absolute() or path in seen:
            raise ValueError('安装清单路径无效或重复。')
        seen.add(path)
        for part in (path,) + tuple(path.parents):
            if part.is_symlink():
                # macOS temporary directory aliases are outside user control.
                if str(part) in ('/var', '/tmp') and str(part.resolve()) in ('/private/var', '/private/tmp'):
                    continue
                raise ValueError('检测到路径漂移或符号链接，停止回滚。')
        if not path.exists() or not stat.S_ISREG(path.stat().st_mode):
            raise ValueError('检测到文件漂移，停止回滚。')
        with path.open('rb') as stream:
            digest = hashlib.sha256()
            for chunk in iter(lambda: stream.read(1024 * 1024), b''):
                digest.update(chunk)
        if digest.hexdigest() != entry['sha256']:
            raise ValueError('检测到内容漂移，停止回滚。')
        files.append(path)
    return files


def reject_running_native(files):
    # comm contains executable paths only; never inspect arguments or credentials.
    result = subprocess.run(['/bin/ps', '-axo', 'pid=,comm='], capture_output=True, text=True, timeout=10)
    if result.returncode:
        raise ValueError('无法确认原生 CLI 是否仍在运行，停止回滚。')
    native = {str(p) for p in files if p.name[0:1].isdigit()}
    for line in result.stdout.splitlines():
        fields = line.strip().split(None, 1)
        if len(fields) == 2 and (fields[1] in native or Path(fields[1]).name == 'claude'):
            raise ValueError('Claude CLI 仍在运行；请先结束当前调用。')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--manifest', type=Path, default=Path(__file__).resolve().parents[1] / 'config' / 'installation.json')
    mode = p.add_mutually_exclusive_group(required=True)
    mode.add_argument('--check', action='store_true')
    mode.add_argument('--apply', action='store_true')
    args = p.parse_args()
    try:
        files = checked_files(args.manifest)
        if args.check:
            print(json.dumps({'status': 'checked', 'owned_file_count': len(files), 'changed': False}))
            return 0
        reject_running_native(files)
        folder = args.manifest.parent / ('rollback-' + datetime.datetime.now().strftime('%Y%m%dT%H%M%S') + '-' + uuid.uuid4().hex[:8])
        folder.mkdir(mode=0o700)
        moved = []
        try:
            # Validate everything again before the first move; a new user edit stops all work.
            checked_files(args.manifest)
            for index, path in enumerate(files):
                target = folder / ('%03d-' % index + path.name)
                os.rename(str(path), str(target))
                moved.append((path, target))
        except Exception:
            for original, target in reversed(moved):
                if not original.exists() and not original.is_symlink():
                    os.rename(str(target), str(original))
            raise
        records = [{'original': str(a), 'quarantined': str(b)} for a, b in moved]
        metadata = folder / 'restore.json'
        fd = os.open(str(metadata), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'w') as stream:
            json.dump({'moved_files': records}, stream, ensure_ascii=False, indent=2)
        print(json.dumps({'status': 'rolled_back', 'quarantine': str(folder), 'moved_files': len(moved), 'account_and_history_retained': True}, ensure_ascii=False))
        return 0
    except (ValueError, KeyError, TypeError, OSError, subprocess.TimeoutExpired) as error:
        # Fixed validation messages contain no file contents or account data.
        message = str(error) if isinstance(error, ValueError) and not isinstance(error, json.JSONDecodeError) else '本机文件操作失败；没有批准删除任何用户数据。'
        print(message, file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
