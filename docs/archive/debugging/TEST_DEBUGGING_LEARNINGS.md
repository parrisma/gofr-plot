# Test Debugging Learnings

## Problem Summary

All authentication-related tests (19 failures) were failing with "Token not found in token store" errors despite tokens being created correctly by test fixtures.

## Root Cause

**Stale server processes** from November 17 were still running on ports 8000 and 8001. These old servers:
- Loaded an empty token store at startup
- Never reloaded tokens created by test fixtures during test runs
- Blocked new server processes from starting despite test script attempts
- Used outdated code that didn't match current implementation

## Key Discovery

The `AuthService.verify_token()` method calls `_load_token_store()` on every verification, which should reload tokens from disk. However:

1. Test fixtures created tokens by instantiating their own `AuthService` instances
2. These fixtures wrote tokens to `/tmp/gplot_test_tokens.json`
3. Long-running server processes from days ago had loaded an empty token store
4. The servers never saw the new tokens because they were the wrong processes entirely

## Diagnostic Process

1. Confirmed token store file contained valid tokens
2. Added debug logging to `AuthService._load_token_store()` 
3. Noticed logging never appeared in server logs during test runs
4. Realized server logs showed startup timestamp from November 17
5. Found two ancient Python processes: PIDs 100282 and 100283

## Solution

Enhanced the test runner (`scripts/run_tests.sh`) with:

### 1. Robust Server Cleanup
```bash
stop_servers() {
    # Kill with multiple patterns to catch all variations
    pkill -9 -f "python.*main_mcp.py"
    pkill -9 -f "python.*main_web.py"
    pkill -9 -f "python.*-m.*app.main_mcp"
    pkill -9 -f "python.*-m.*app.main_web"
    
    # Verify all dead
    if ps aux | grep -E "python.*(main_mcp|main_web)" | grep -v grep; then
        # Force kill by PID if patterns missed any
        ...kill by PID...
    fi
}
```

### 2. Token Store Cleanup
- Empty token store at test start: `echo "{}" > /tmp/gplot_test_tokens.json`
- Empty token store after test completion
- Ensures clean state for every test run

### 3. Process Verification
- Wait 2 seconds after kill commands
- Verify processes are actually dead
- Report warnings if cleanup fails
- Prevent cascading failures from stale processes

## Lessons Learned

### **RULE ZERO: NEVER MAKE ASSUMPTIONS**
The biggest mistake was assuming the test runner successfully started fresh servers. Always verify what you think is happening.

### **RULE ONE: ALWAYS VERIFY**
Don't trust that commands succeeded - check the actual state:
- Processes killed? → `ps aux` to verify they're dead
- Servers started? → Check log timestamps and PIDs
- Files written? → Read them back and check contents
- Ports free? → Actually test the connection

### Specific Lessons

1. **Always check for stale processes** - Long-running dev containers can accumulate zombie processes
2. **Verify process cleanup** - Don't trust that `pkill` succeeded without verification
3. **Check process start times** - Server logs showed the real issue (Nov 17 startup)
4. **Clean state between runs** - Empty shared resources (like token stores) before tests
5. **Multiple kill patterns** - Different invocation methods need different patterns
6. **Wait after kills** - Process termination isn't instantaneous

## Prevention

The enhanced test runner now:
- ✅ Kills servers with multiple patterns covering all invocation methods
- ✅ Verifies all processes are dead before proceeding
- ✅ Force-kills by PID if pattern matching fails
- ✅ Empties token store before and after test runs
- ✅ Reports clear warnings if cleanup fails
- ✅ **Checks log file age before starting servers** - Fails fast if logs are >1 hour old, indicating stale processes

## Result

**186/186 tests passing** ✅

All authentication tests now pass cleanly with proper token store visibility between test fixtures and server processes.
