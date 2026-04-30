---
name: tdd
description: "TDD workflow — write failing test first (RED), implement (GREEN), refactor. Includes Go/Java/Python examples and testing anti-patterns."
when_to_use: "Implementing features, fixing bugs, refactoring code, or any behavior change. TRIGGER: 新功能, fix bug, 重构, TDD, test first, 写测试, 先写测试. 不适用于: 纯样式调整、配置文件变更、一次性脚本"
argument-hint: [description of what to implement]
---

# TDD (Test-Driven Development)

Write the test first. Watch it fail. Write minimal code to pass.

**Core principle:** If you didn't watch the test fail, you don't know if it tests the right thing.

## The Iron Law

```
NO PRODUCTION CODE WITHOUT A FAILING TEST FIRST
```

Write code before the test? Delete it. Start over.

- Don't keep it as "reference"
- Don't "adapt" it while writing tests
- Don't look at it
- Delete means delete

## When to Use

**Always:**
- New features
- Bug fixes
- Refactoring
- Behavior changes

**Exceptions (ask user):**
- Throwaway prototypes
- Generated code
- Configuration files
- No test framework available

Thinking "skip TDD just this once"? Stop. That's rationalization.

## RED — Write a Failing Test

Write one minimal test showing what should happen.

**Requirements:**
- One behavior per test
- Clear name describing expected behavior
- Real code (mocks only if unavoidable)

**Good:**
```go
func TestRetryFailedOperations(t *testing.T) {
    attempts := 0
    op := func() (string, error) {
        attempts++
        if attempts < 3 {
            return "", errors.New("fail")
        }
        return "success", nil
    }
    result, err := RetryOperation(op)
    assert.NoError(t, err)
    assert.Equal(t, "success", result)
    assert.Equal(t, 3, attempts)
}
```
Clear name, tests real behavior, one thing.

**Bad:**
```go
func TestRetry(t *testing.T) {
    mock := &MockOperation{}
    mock.On("Execute").Return("", errors.New("fail")).Twice()
    mock.On("Execute").Return("success", nil).Once()
    RetryOperation(mock)
    mock.AssertNumberOfCalls(t, "Execute", 3)
}
```
Vague name, tests mock not code.

## Verify RED — Watch It Fail

**MANDATORY. Never skip.**

```bash
go test -run TestRetryFailedOperations ./...
```

Confirm:
- Test **fails** (not errors)
- Failure message describes expected behavior
- Fails because feature is missing (not typos)

Test **passes**? You're testing existing behavior. Fix test.
Test **errors**? Fix error, re-run until it fails correctly.

## GREEN — Minimal Code

Write simplest code to pass the test. No extra features, no "improvements".

**Good:** Just enough to pass.
**Bad:** Adding configurable retries, backoff strategies, callbacks — that's YAGNI.

## Verify GREEN — Watch It Pass

**MANDATORY.**

```bash
go test ./...
```

Confirm:
- Target test passes
- **Full suite passes** — catch regressions immediately
- Output clean (no errors, warnings)

Test fails? Fix code, not test.
Other tests fail? Fix now.

## REFACTOR — Clean Up

After green only:
- Remove duplication
- Improve names
- Extract helpers

Keep tests green. Don't add behavior.

## Common Rationalizations

| Excuse | Reality |
|--------|---------|
| "Too simple to test" | Simple code breaks. Test takes 30 seconds. |
| "I'll test after" | Tests passing immediately prove nothing. |
| "Already manually tested" | Ad-hoc ≠ systematic. No record, can't re-run. |
| "Deleting X hours is wasteful" | Sunk cost fallacy. Unverified code is technical debt. |
| "Keep as reference, write tests first" | You'll adapt it. That's testing after. Delete means delete. |
| "Need to explore first" | Fine. Throw away exploration, start with TDD. |
| "Test hard = design unclear" | Listen to test. Hard to test = hard to use. |
| "TDD will slow me down" | TDD faster than debugging. Pragmatic = test-first. |
| "Existing code has no tests" | You're improving it. Add tests for existing behavior. |

## Red Flags — STOP and Start Over

- Code before test
- Test passes immediately
- Can't explain why test failed
- Tests added "later"
- Rationalizing "just this once"
- "Keep as reference" or "adapt existing code"

**All of these mean: Delete code. Start over with TDD.**

## When Stuck

| Problem | Solution |
|---------|----------|
| Don't know how to test | Write wished-for API. Write assertion first. Ask user. |
| Test too complicated | Design too complicated. Simplify interface. |
| Must mock everything | Code too coupled. Use dependency injection. |
| Test setup huge | Extract helpers. Still complex? Simplify design. |

## Bug Fix Workflow

Bug found? Write failing test reproducing it first. Follow TDD cycle. Test proves fix and prevents regression.

Never fix bugs without a test.

## Verification Checklist

Before marking work complete:

- [ ] Every new function/method has a test
- [ ] Watched each test **fail** before implementing
- [ ] Each test failed for expected reason (feature missing, not typo)
- [ ] Wrote minimal code to pass each test
- [ ] All tests pass — no regressions
- [ ] Tests use real code (mocks only if unavoidable)
- [ ] Edge cases and errors covered

Can't check all boxes? You skipped TDD. Start over.

## Testing Anti-Patterns

When adding mocks or test utilities, read [testing-anti-patterns.md](references/testing-anti-patterns.md) to avoid:
- Testing mock behavior instead of real behavior
- Adding test-only methods to production classes
- Mocking without understanding dependencies
- Incomplete mock data structures

## Language Commands

| Language | Run All | Run Single | Build |
| :--- | :--- | :--- | :--- |
| Go | `go test ./...` | `go test -run TestName ./path/...` | `go build ./...` |
| Java (Maven) | `mvn test` | `mvn -Dtest=ClassName#method test` | `mvn compile` |
| Java (Gradle) | `./gradlew test` | `./gradlew test --tests ClassName.method` | `./gradlew build` |
| Python (pytest) | `pytest` | `pytest tests/test_file.py::test_name` | — |
| React/Vitest | `pnpm test` | `pnpm test -- TestName` | `pnpm build` |
| Rust | `cargo test` | `cargo test test_name` | `cargo build` |

## Language Examples

See language-specific reference files for complete TDD walk-throughs:

- [Go TDD Example](references/go-example.md) — Table-driven tests, error handling, interface mocking
- [Java TDD Example](references/java-example.md) — JUnit 5, Mockito, Spring Boot service testing
- [Python TDD Example](references/python-example.md) — pytest, fixtures, parametrize, mocking

## Final Rule

```
Production code → test exists and failed first
Otherwise → not TDD
```
