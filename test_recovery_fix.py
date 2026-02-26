"""
Test for JSONL session recovery fix: normalized comparison for lossy encoding.

The Claude CLI encodes CWD paths by replacing '/' with '-'. This is lossy
when user_ids contain '_' or '-' (indistinguishable from path separators).

This test verifies that the recovery logic correctly matches directories
even when the encoding is ambiguous.
"""
import os
import json
import tempfile
import shutil
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch

# Minimal test that directly tests the _recover_session_from_jsonl logic
# without requiring the full SDK


def test_normalize_matching():
    """Test that _normalize treats '_' and '-' as equivalent."""
    def _normalize(s: str) -> str:
        return s.replace('_', '-')

    # Core case: user_id with underscores vs encoded with hyphens
    assert _normalize('-data-claude-users-ou_649ee') == _normalize('-data-claude-users-ou-649ee')
    assert _normalize('ou_649ee') == _normalize('ou-649ee')

    # No-op for strings without underscores
    assert _normalize('testuser') == 'testuser'
    assert _normalize('-data-claude-users-testuser') == '-data-claude-users-testuser'


def test_recovery_underscore_hyphen_matching():
    """
    Test that JSONL recovery correctly matches a directory with underscores
    when the encoded dir name has hyphens.

    Scenario:
    - Actual directory: /tmp/base/ou_649ee1e6 (underscores)
    - Claude CLI project dir: -tmp-base-ou-649ee1e6 (all hyphens, lossy encoding)
    - Recovery should match to the actual directory with underscores
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = os.path.join(tmpdir, 'base')
        os.makedirs(base_dir)

        # Create actual user directory with underscores
        user_dir = os.path.join(base_dir, 'ou_649ee1e6')
        os.makedirs(user_dir)

        # Create Claude CLI projects directory
        projects_dir = os.path.join(tmpdir, '.claude', 'projects')

        # The encoded directory name: all '/' replaced with '-'
        # For CWD /tmp/.../base/ou_649ee1e6, the encoded form would have
        # hyphens for '/' but underscores stay. However, the actual Claude CLI
        # seems to also replace underscores, so the encoded form has all hyphens.
        # We simulate the case where the encoded dir uses hyphens where the real
        # path has underscores.
        real_cwd = os.path.normpath(user_dir)
        # Simulate the lossy encoding where underscores became hyphens
        encoded_dir_name = real_cwd.replace('/', '-').replace('_', '-')
        encoded_dir_path = os.path.join(projects_dir, encoded_dir_name)
        os.makedirs(encoded_dir_path)

        # Create a fake JSONL session file
        session_id = 'test-session-123'
        jsonl_file = os.path.join(encoded_dir_path, f'{session_id}.jsonl')
        with open(jsonl_file, 'w') as f:
            f.write(json.dumps({'type': 'test'}) + '\n')

        # Now test the matching logic (extracted from _recover_session_from_jsonl)
        encoded_base = os.path.normpath(base_dir).replace('/', '-')

        found_dir_name = encoded_dir_name
        assert found_dir_name.startswith(encoded_base), \
            f"Expected {found_dir_name} to start with {encoded_base}"

        def _normalize(s: str) -> str:
            return s.replace('_', '-')

        matched_user_id = None
        matched_cwd = None

        for entry in sorted(os.listdir(base_dir)):
            entry_path = os.path.join(base_dir, entry)
            if not os.path.isdir(entry_path):
                continue

            candidate_cwd = os.path.normpath(entry_path)
            candidate_encoded = candidate_cwd.replace('/', '-')

            if found_dir_name == candidate_encoded:
                matched_user_id = entry
                matched_cwd = candidate_cwd
                break
            elif _normalize(found_dir_name) == _normalize(candidate_encoded):
                matched_user_id = entry
                matched_cwd = candidate_cwd
                break

        assert matched_user_id == 'ou_649ee1e6', \
            f"Expected user_id 'ou_649ee1e6', got '{matched_user_id}'"
        assert matched_cwd == real_cwd, \
            f"Expected cwd '{real_cwd}', got '{matched_cwd}'"

        print(f"  [PASS] Matched user_id: {matched_user_id}")
        print(f"  [PASS] Matched cwd: {matched_cwd}")


def test_recovery_exact_match_still_works():
    """Test that exact matching (no underscores in user_id) still works."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = os.path.join(tmpdir, 'base')
        os.makedirs(base_dir)

        user_dir = os.path.join(base_dir, 'testuser')
        os.makedirs(user_dir)

        real_cwd = os.path.normpath(user_dir)
        # Exact encoding (no underscores, so no ambiguity)
        encoded_dir_name = real_cwd.replace('/', '-')

        encoded_base = os.path.normpath(base_dir).replace('/', '-')
        assert encoded_dir_name.startswith(encoded_base)

        def _normalize(s: str) -> str:
            return s.replace('_', '-')

        matched_user_id = None
        matched_cwd = None

        for entry in sorted(os.listdir(base_dir)):
            entry_path = os.path.join(base_dir, entry)
            if not os.path.isdir(entry_path):
                continue

            candidate_cwd = os.path.normpath(entry_path)
            candidate_encoded = candidate_cwd.replace('/', '-')

            if encoded_dir_name == candidate_encoded:
                matched_user_id = entry
                matched_cwd = candidate_cwd
                break
            elif _normalize(encoded_dir_name) == _normalize(candidate_encoded):
                matched_user_id = entry
                matched_cwd = candidate_cwd
                break

        assert matched_user_id == 'testuser', \
            f"Expected user_id 'testuser', got '{matched_user_id}'"
        assert matched_cwd == real_cwd
        print(f"  [PASS] Exact match user_id: {matched_user_id}")


def test_recovery_with_subdir():
    """Test normalized prefix matching for sessions with subdirs."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = os.path.join(tmpdir, 'base')
        os.makedirs(base_dir)

        user_dir = os.path.join(base_dir, 'user_abc')
        os.makedirs(user_dir)

        real_cwd = os.path.normpath(user_dir)
        # Simulate encoded dir with a subdir appended, and underscores as hyphens
        # Real CWD: /tmp/.../base/user_abc/myproject
        # Encoded:  -tmp-...-base-user-abc-myproject (all hyphens)
        encoded_dir_name = real_cwd.replace('/', '-').replace('_', '-') + '-myproject'

        encoded_base = os.path.normpath(base_dir).replace('/', '-')
        assert encoded_dir_name.startswith(encoded_base)

        def _normalize(s: str) -> str:
            return s.replace('_', '-')

        matched_user_id = None
        matched_subdir = None
        matched_cwd = None

        for entry in sorted(os.listdir(base_dir)):
            entry_path = os.path.join(base_dir, entry)
            if not os.path.isdir(entry_path):
                continue

            candidate_cwd = os.path.normpath(entry_path)
            candidate_encoded = candidate_cwd.replace('/', '-')

            if encoded_dir_name == candidate_encoded:
                matched_user_id = entry
                matched_cwd = candidate_cwd
                break
            elif _normalize(encoded_dir_name) == _normalize(candidate_encoded):
                matched_user_id = entry
                matched_cwd = candidate_cwd
                break
            elif encoded_dir_name.startswith(candidate_encoded + '-'):
                matched_user_id = entry
                matched_subdir = encoded_dir_name[len(candidate_encoded) + 1:]
                matched_cwd = os.path.normpath(os.path.join(base_dir, entry, matched_subdir))
                break
            elif _normalize(encoded_dir_name).startswith(_normalize(candidate_encoded) + '-'):
                matched_user_id = entry
                norm_prefix_len = len(_normalize(candidate_encoded)) + 1
                matched_subdir = _normalize(encoded_dir_name)[norm_prefix_len:]
                matched_cwd = os.path.normpath(os.path.join(base_dir, entry, matched_subdir))
                break

        assert matched_user_id == 'user_abc', \
            f"Expected user_id 'user_abc', got '{matched_user_id}'"
        assert matched_subdir == 'myproject', \
            f"Expected subdir 'myproject', got '{matched_subdir}'"
        print(f"  [PASS] Subdir match user_id: {matched_user_id}, subdir: {matched_subdir}")


def test_ensure_directory_in_resume():
    """Test that ensure_directory correctly creates missing directories.

    This mirrors the ensure_directory logic from security.py without
    importing it (to avoid claude_agent_sdk dependency in tests).
    """
    def ensure_directory(path, auto_create=True):
        if os.path.exists(path):
            return os.path.isdir(path)
        if auto_create:
            os.makedirs(path, exist_ok=True)
            return True
        return False

    with tempfile.TemporaryDirectory() as tmpdir:
        new_dir = os.path.join(tmpdir, 'new_user_dir')
        assert not os.path.exists(new_dir)

        result = ensure_directory(new_dir, auto_create=True)
        assert result is True
        assert os.path.isdir(new_dir)
        print(f"  [PASS] ensure_directory created: {new_dir}")

        # Already exists
        result = ensure_directory(new_dir, auto_create=True)
        assert result is True
        print(f"  [PASS] ensure_directory idempotent")


if __name__ == '__main__':
    tests = [
        ('Normalize matching', test_normalize_matching),
        ('Recovery: underscore/hyphen matching', test_recovery_underscore_hyphen_matching),
        ('Recovery: exact match still works', test_recovery_exact_match_still_works),
        ('Recovery: subdir with normalized match', test_recovery_with_subdir),
        ('ensure_directory in resume', test_ensure_directory_in_resume),
    ]

    passed = 0
    failed = 0
    for name, test_fn in tests:
        try:
            print(f"[TEST] {name}...")
            test_fn()
            passed += 1
        except Exception as e:
            print(f"  [FAIL] {e}")
            failed += 1

    print(f"\n{'='*50}")
    print(f"Results: {passed} passed, {failed} failed, {passed + failed} total")
    if failed == 0:
        print("All tests passed!")
    else:
        print("SOME TESTS FAILED")
        exit(1)
