#!/usr/bin/env python3
"""
Simple performance test for SQLite storage.
This test doesn't require claude-agent-sdk.
"""
import asyncio
import time
import tempfile
import os
import sys
from datetime import datetime
from typing import Optional, List, Dict, Any
from pathlib import Path

# Mock claude_agent_sdk before importing
class MockClaudeSDKClient:
    pass

class MockClaudeAgentOptions:
    pass

mock_sdk = type(sys)('claude_agent_sdk')
mock_sdk.ClaudeSDKClient = MockClaudeSDKClient
mock_sdk.ClaudeAgentOptions = MockClaudeAgentOptions
sys.modules['claude_agent_sdk'] = mock_sdk

# Now we can import the storage
sys.path.insert(0, str(Path(__file__).parent))
from claude_agent_http.storage.sqlite import SQLiteStorage
from claude_agent_http.models import SessionInfo


async def test_storage_performance():
    """Test optimized SQLite storage performance."""

    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        db_path = tmp.name

    try:
        storage = SQLiteStorage(db_path=db_path, ttl=3600)

        print('\n' + '='*60)
        print('SQLite Storage Performance Test (Optimized)')
        print('='*60)

        # Test 1: Create sessions
        print('\n1. Creating 100 sessions...')
        start = time.time()
        session_ids = []
        for i in range(100):
            session_id = f'session_{i}'
            info = SessionInfo(
                session_id=session_id,
                user_id=f'user_{i % 10}',
                subdir=None,
                cwd=f'/home/user_{i % 10}',
                system_prompt='Test prompt',
                mcp_servers={},
                plugins=[],
                model='claude-3-5-sonnet-20241022',
                permission_mode='bypassPermissions',
                allowed_tools=['Bash', 'Read', 'Write'],
                disallowed_tools=[],
                add_dirs=[],
                max_turns=None,
                max_budget_usd=None,
                metadata={'test': True}
            )
            await storage.save(session_id, info)
            session_ids.append(session_id)

        create_time = time.time() - start
        print(f'   ✓ Created 100 sessions')
        print(f'   Time: {create_time:.3f}s | Rate: {100/create_time:.1f} ops/sec')

        # Test 2: Touch (most critical for performance)
        print('\n2. Touching 100 sessions (simulates message activity)...')
        start = time.time()
        for session_id in session_ids:
            await storage.touch(session_id)
        touch_time = time.time() - start
        print(f'   ✓ Touched 100 sessions')
        print(f'   Time: {touch_time:.3f}s | Rate: {100/touch_time:.1f} ops/sec')

        # Test 3: Get sessions
        print('\n3. Getting 100 sessions...')
        start = time.time()
        for session_id in session_ids:
            info = await storage.get(session_id)
            assert info is not None
        get_time = time.time() - start
        print(f'   ✓ Retrieved 100 sessions')
        print(f'   Time: {get_time:.3f}s | Rate: {100/get_time:.1f} ops/sec')

        # Test 4: List sessions
        print('\n4. Listing all sessions...')
        start = time.time()
        all_sessions = await storage.list_sessions()
        list_time = time.time() - start
        print(f'   ✓ Listed {len(all_sessions)} sessions')
        print(f'   Time: {list_time:.3f}s')

        # Test 5: Concurrent touches
        print('\n5. Concurrent touches (50 parallel operations)...')
        start = time.time()
        tasks = []
        for i in range(50):
            session_id = session_ids[i % len(session_ids)]
            tasks.append(storage.touch(session_id))
        await asyncio.gather(*tasks)
        concurrent_time = time.time() - start
        print(f'   ✓ Completed 50 concurrent touches')
        print(f'   Time: {concurrent_time:.3f}s | Rate: {50/concurrent_time:.1f} ops/sec')

        # Test 6: High-frequency touches (simulating real workload)
        print('\n6. High-frequency touches (200 operations on 10 sessions)...')
        start = time.time()
        for i in range(200):
            await storage.touch(session_ids[i % 10])
        freq_time = time.time() - start
        print(f'   ✓ Completed 200 high-frequency touches')
        print(f'   Time: {freq_time:.3f}s | Rate: {200/freq_time:.1f} ops/sec')

        # Summary
        print('\n' + '='*60)
        print('PERFORMANCE SUMMARY')
        print('='*60)
        print(f'  Create:            {100/create_time:>8.1f} ops/sec')
        print(f'  Touch:             {100/touch_time:>8.1f} ops/sec  ⭐ Most critical')
        print(f'  Get:               {100/get_time:>8.1f} ops/sec')
        print(f'  Concurrent:        {50/concurrent_time:>8.1f} ops/sec')
        print(f'  High-frequency:    {200/freq_time:>8.1f} ops/sec')
        print('='*60)
        print('\nOptimizations applied:')
        print('  ✓ Persistent database connection (no reconnect overhead)')
        print('  ✓ WAL mode enabled (better concurrency)')
        print('  ✓ PRAGMA synchronous=NORMAL (reduced fsync)')
        print('  ✓ Increased cache size (40MB)')
        print('  ✓ Memory-based temp storage')
        print('='*60)

        # Cleanup
        await storage.close()

    finally:
        # Remove database files
        if os.path.exists(db_path):
            os.unlink(db_path)
        for ext in ['-wal', '-shm']:
            wal_file = db_path + ext
            if os.path.exists(wal_file):
                os.unlink(wal_file)


if __name__ == '__main__':
    asyncio.run(test_storage_performance())
    print('\n✅ Performance test completed!\n')
