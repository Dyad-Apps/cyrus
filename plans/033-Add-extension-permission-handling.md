# Implementation Plan: Add Extension Permission Handling

**Issue**: [033-Add-extension-permission-handling](/home/daniel/Projects/barf/cyrus/cyrus/issues/033-Add-extension-permission-handling.md)
**Created**: 2026-03-18
**PROMPT**: PROMPT_plan

## Gap Analysis

**Already exists**:
- `extension.ts` with full platform-adaptive keyboard simulation patterns (`tryEnterKey`, `tryKeyboardSim`) for Windows/macOS/Linux
- `execAsync` helper (line 27) — promisified `child_process.exec`
- `os` and `child_process` imports already present
- `BrainConnectionManager` class (compiled in `out/brain-connection.js`) with `onMessage` callback parameter — dispatches parsed JSON to caller-supplied handler
- Existing test file for `BrainConnectionManager` (`out/brain-connection.test.js`) using Jest with fake sockets
- VS Code mock (`out/__mocks__/vscode.js`)

**Needs building**:
1. `handleBrainMessage(msg)` function in `extension.ts` — dispatches `permission_respond` and `prompt_respond` message types
2. `simulateKeyPress(key)` function in `extension.ts` — platform-specific key simulation for `1` and `Escape`
3. Unit tests for both functions
4. Note: `brain-connection.ts` source doesn't exist in `src/` (only compiled JS in `out/`). The BrainConnectionManager is NOT yet integrated into extension.ts's `activate()`. Wiring the onMessage callback is a prerequisite that may belong to Issue 031 completion, but we should add the handler functions regardless.

## Approach

Add `handleBrainMessage()` and `simulateKeyPress()` directly to `extension.ts`, following the existing keyboard simulation patterns already in the file. The functions will be **exported** so they can be tested independently and wired into the BrainConnectionManager's `onMessage` callback when integration happens.

**Why this approach**: The issue specifies modifying `extension.ts` only. The existing `tryEnterKey()` and `tryKeyboardSim()` provide proven platform-specific command templates to follow. Using the same `execAsync` + platform switch pattern ensures consistency. Errors are caught and logged (never thrown) per acceptance criteria.

## Rules to Follow
- `.claude/rules/` — Empty directory; no project-specific rules
- Follow existing code patterns in `extension.ts`: same comment style, same platform detection pattern, same error-handling pattern (catch + log to `out`)

## Skills & Agents to Use
| Task | Skill/Agent | Purpose |
|------|-------------|---------|
| Implementation | Direct coding | Single file change, well-defined |
| Testing | `test-automator` agent | Jest test following brain-connection.test.js patterns |

## Prioritized Tasks

- [ ] 1. Add `simulateKeyPress(key: string)` function to `extension.ts`
  - Platform switch: `os.platform()` → win32/darwin/linux
  - Key `'1'`: SendKeys('1') / keystroke "1" / xdotool key 1
  - Key `'Escape'`: SendKeys('{ESC}') / key code 53 / xdotool key Escape
  - Catch errors, log to `out`, never throw
  - Log success with action taken
  - Timeout: 3000ms per exec

- [ ] 2. Add `handleBrainMessage(msg: any)` function to `extension.ts`
  - Check `msg.type`
  - `'permission_respond'`: log action, call `simulateKeyPress('1')` for allow, `simulateKeyPress('Escape')` for deny
  - `'prompt_respond'`: log text preview, stub for future (paste text + Enter)
  - Unknown types: silently ignore (or log)

- [ ] 3. Export both functions for testability
  - `handleBrainMessage` needs access to `out` (module-level state) — keep as module function

- [ ] 4. Create `src/brain-message-handler.test.ts` (or add to extension test)
  - Mock `child_process.exec` to verify correct commands are called
  - Mock `os.platform()` to test all three platforms
  - Mock `out.appendLine` to verify logging
  - Test each acceptance criterion

- [ ] 5. Add Jest configuration if not present
  - Add `jest.config.js` and test script to `package.json`
  - Add `ts-jest` and `@types/jest` to devDependencies if needed

- [ ] 6. Compile and verify: `npm run compile`

## Acceptance-Driven Tests

| Acceptance Criterion | Required Test | Type |
|---------------------|---------------|------|
| `handleBrainMessage()` recognizes `permission_respond` | Test dispatches to simulateKeyPress on permission_respond type | unit |
| `handleBrainMessage()` recognizes `prompt_respond` | Test logs prompt text on prompt_respond type | unit |
| permission_respond action="allow" simulates `1` | Mock exec, verify correct key command per platform | unit |
| permission_respond action="deny" simulates `Escape` | Mock exec, verify correct Escape command per platform | unit |
| prompt_respond with text pastes and enters (future) | Test logs the text, stub behavior | unit |
| Platform-specific methods (PowerShell/osascript/xdotool) | 3 platform variants tested via os.platform() mock | unit |
| Failures logged but never thrown | Test with exec rejection, verify log + no exception | unit |
| Success logged with action taken | Verify appendLine called with action description | unit |

**No cheating** — cannot claim done without required tests passing.

## Validation (Backpressure)
- Tests: All Jest tests pass (permission handling + key simulation)
- Lint: TypeScript compiles cleanly (`npm run compile`)
- Build: Extension compiles without errors

## Files to Create/Modify
- `cyrus-companion/src/extension.ts` — Add `handleBrainMessage()` and `simulateKeyPress()` functions
- `cyrus-companion/src/permission-handler.test.ts` — New: unit tests for permission handling (or inline in extension if preferred)
- `cyrus-companion/package.json` — Add test script + jest/ts-jest devDependencies if missing
- `cyrus-companion/jest.config.js` — New: Jest configuration (if not exists)

## Implementation Details

### simulateKeyPress signature
```typescript
async function simulateKeyPress(key: string): Promise<void> {
    const platform = os.platform();
    try {
        let command = '';
        // Platform-specific command construction (see issue for exact commands)
        if (command) {
            await execAsync(command, { timeout: 3000 });
            out.appendLine(`[Brain] Simulated key press: ${key}`);
        }
    } catch (err) {
        out.appendLine(`[Brain] Failed to simulate ${key}: ${err}`);
    }
}
```

### handleBrainMessage signature
```typescript
function handleBrainMessage(msg: any): void {
    const type = msg.type;
    if (type === 'permission_respond') {
        // dispatch to simulateKeyPress
    } else if (type === 'prompt_respond') {
        // log + stub for future
    }
}
```

### Placement in extension.ts
- After the existing keyboard simulation section (after line 374, before the Utility section)
- Follows the `// ── Brain message handling ──` comment convention
