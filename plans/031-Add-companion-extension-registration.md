# Plan: Issue 031 — Add Companion Extension Registration

## Status
IN_PROGRESS

## Gap Analysis

### What Exists
- `cyrus-companion/src/extension.ts` — platform-adaptive IPC server (TCP/Unix), handles incoming brain→ext messages
- `cyrus-companion/package.json` — has `focusCommand` setting, no brain connection settings
- No outbound brain connection, no registration logic
- No test framework for the companion extension

### What Needs Building
- Outbound TCP connection to brain on port 8770 (registration channel)
- Registration message: `{"type":"register","workspace":"...","safe":"...","port":...}`
- Exponential backoff reconnect: 1s → 2s → 4s → ... → 30s (cap), reset on success
- `cyrusCompanion.brainHost` and `cyrusCompanion.brainPort` settings
- Connection status logging to output channel
- Stub handler for incoming brain messages
- Extracted `BrainConnectionManager` class in `brain-connection.ts` for testability
- Jest test suite with VS Code and net mocks

## Prioritized Tasks

- [x] Create plan file
- [ ] Add Jest test framework to `cyrus-companion/package.json` (devDependencies + scripts)
- [ ] Create `src/__mocks__/vscode.ts` — VS Code API mock for tests
- [ ] Create `src/brain-connection.ts` — extractable, testable brain connection class
- [ ] Write `src/brain-connection.test.ts` — TDD tests (write FIRST)
- [ ] Add `brainHost`/`brainPort` settings to `cyrus-companion/package.json` contributes
- [ ] Update `cyrus-companion/src/extension.ts` — integrate `BrainConnectionManager`
- [ ] Run `npm run compile` (TypeScript check)
- [ ] Run `npm test` (Jest tests pass)

## Acceptance-Driven Tests

| Acceptance Criterion | Test | File |
|---|---|---|
| Connects to `brainHost:8770` on activation | `connects to configured host and port` | brain-connection.test.ts |
| Sends `{"type":"register","workspace":"...","safe":"...","port":...}` | `sends registration message on connect` | brain-connection.test.ts |
| Auto-reconnect with backoff 1s, 2s, 4s, max 30s | `reconnect backoff doubles each time` | brain-connection.test.ts |
| Backoff resets to 1s on success | `resets backoff on successful connection` | brain-connection.test.ts |
| Connection status logged | `logs connection events to output channel` | brain-connection.test.ts |
| Persistent connection kept alive | `does not reconnect when destroyed` | brain-connection.test.ts |
| New settings in package.json | `package.json has brainHost and brainPort` | package.json (manual verify) |

## Files to Create/Modify

- **Create**: `cyrus-companion/src/brain-connection.ts`
- **Create**: `cyrus-companion/src/__mocks__/vscode.ts`
- **Create**: `cyrus-companion/src/brain-connection.test.ts`
- **Modify**: `cyrus-companion/package.json` — add jest, test script, brainHost/brainPort settings
- **Modify**: `cyrus-companion/src/extension.ts` — import and use BrainConnectionManager

## Verification Checklist

- [ ] `npm run compile` passes with zero errors
- [ ] `npm test` passes (all tests green)
- [ ] Coverage ≥ 80%
- [ ] `brainHost` default `localhost`, `brainPort` default `8770` in package.json
- [ ] Backoff sequence: 1000ms → 2000ms → 4000ms → ... → 30000ms (capped)
- [ ] Registration message includes workspace, safe, port fields
- [ ] Logs `[Brain] Connected to ...` on connect
- [ ] Logs `[Brain] Reconnecting in Xms` on disconnect

## Open Questions / Discoveries

- The plan file was missing; created fresh from issue analysis.
- No existing test framework in cyrus-companion; adding Jest + ts-jest.
- Extracting brain logic into `BrainConnectionManager` class for testability (not in original issue spec but required for TDD).
