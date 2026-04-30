---
name: tdd
description: "TDD workflow — write failing test first (RED), implement (GREEN), refactor. Includes Go/Java/Python examples and testing anti-patterns."
when_to_use: "Implementing features, fixing bugs, refactoring code, or any behavior change. TRIGGER: 新功能, fix bug, 重构, TDD, test first, 写测试, 先写测试. 不适用于: 纯样式调整、配置文件变更、一次性脚本"
argument-hint: [description of what to implement]
---

# TDD (Test-Driven Development)

Write the test first. Watch it fail. Write minimal code to pass.

**Core principle:** If you didn't watch the test fail, you don't know if it tests the right thing.

**Violating the letter of the rules is violating the spirit of the rules.**

## The Iron Law

```
NO PRODUCTION CODE WITHOUT A FAILING TEST FIRST
```

Write code before the test? Delete it. Start over.

**No exceptions:**
- Don't keep it as "reference"
- Don't "adapt" it while writing tests
- Don't look at it
- Delete means delete

Implement fresh from tests. Period.

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

## Why Order Matters

### "I'll write tests after to verify it works"

Tests written after code pass immediately. Passing immediately proves nothing:
- Might test the wrong thing
- Might test implementation, not behavior
- Might miss edge cases you forgot
- You never saw it catch the bug

Test-first forces you to see the test fail, proving it actually tests something.

### "I already manually tested all the edge cases"

Manual testing is ad-hoc. You think you tested everything but:
- No record of what you tested
- Can't re-run when code changes
- Easy to forget cases under pressure
- "It worked when I tried it" ≠ comprehensive

Automated tests are systematic. They run the same way every time.

### "Deleting X hours of work is wasteful"

Sunk cost fallacy. The time is already gone. Your choice now:
- Delete and rewrite with TDD (X more hours, high confidence)
- Keep it and add tests after (30 min, low confidence, likely bugs)

The "waste" is keeping code you can't trust. Working code without real tests is technical debt.

### "TDD is dogmatic, being pragmatic means adapting"

TDD IS pragmatic:
- Finds bugs before commit (faster than debugging after)
- Prevents regressions (tests catch breaks immediately)
- Documents behavior (tests show how to use code)
- Enables refactoring (change freely, tests catch breaks)

"Pragmatic" shortcuts = debugging in production = slower.

### "Tests after achieve the same goals - it's spirit not ritual"

No. Tests-after answer "What does this do?" Tests-first answer "What should this do?"

Tests-after are biased by your implementation. You test what you built, not what's required. You verify remembered edge cases, not discovered ones.

Tests-first force edge case discovery before implementing. Tests-after verify you remembered everything (you didn't).

30 minutes of tests after ≠ TDD. You get coverage, lose proof tests work.

## RED — Write a Failing Test

Write one minimal test showing what should happen.

<Good>
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
Clear name, tests real behavior, one thing
</Good>

<Bad>
```go
func TestRetry(t *testing.T) {
    mock := &MockOperation{}
    mock.On("Execute").Return("", errors.New("fail")).Twice()
    mock.On("Execute").Return("success", nil).Once()
    RetryOperation(mock)
    mock.AssertNumberOfCalls(t, "Execute", 3)
}
```
Vague name, tests mock not code
</Bad>

**Requirements:**
- One behavior per test — "and" in name? Split it.
- Clear name describing expected behavior
- Real code (mocks only if unavoidable)

## Verify RED — Watch It Fail

**MANDATORY. Never skip.**

```bash
go test -run TestRetryFailedOperations ./...
```

Confirm:
- Test **fails** (not errors)
- Failure message describes expected behavior
- Fails because feature is missing (not typos)

**Test passes?** You're testing existing behavior. Fix test.
**Test errors?** Fix error, re-run until it fails correctly.

## GREEN — Minimal Code

Write simplest code to pass the test. No extra features, no "improvements".

<Good>
```go
func RetryOperation[T any](fn func() (T, error)) (T, error) {
    var lastErr error
    for i := 0; i < 3; i++ {
        result, err := fn()
        if err == nil {
            return result, nil
        }
        lastErr = err
    }
    var zero T
    return zero, lastErr
}
```
Just enough to pass
</Good>

<Bad>
```go
func RetryOperation[T any](
    fn func() (T, error),
    options ...RetryOption,         // YAGNI
) (T, error) {
    cfg := defaultConfig()
    for _, opt := range options {   // YAGNI
        opt(cfg)
    }
    // configurable retries, backoff, callbacks...
}
```
Over-engineered
</Bad>

Don't add features, refactor other code, or "improve" beyond the test.

## Verify GREEN — Watch It Pass

**MANDATORY.**

```bash
go test ./...
```

Confirm:
- Target test passes
- **Full suite passes** — catch regressions immediately
- Output clean (no errors, warnings)

**Test fails?** Fix code, not test.
**Other tests fail?** Fix now.

## REFACTOR — Clean Up

After green only:
- Remove duplication
- Improve names
- Extract helpers

Keep tests green. Don't add behavior.

## The Cycle Repeats

Next failing test for next feature.

## Bug Fix Workflow

Bug found? Write failing test reproducing it first.

**Bug:** Empty email accepted

**RED**
```go
func TestRejectsEmptyEmail(t *testing.T) {
    result, err := SubmitForm(FormData{Email: ""})
    require.NoError(t, err)
    assert.Equal(t, "Email required", result.Error)
}
```

**Verify RED**
```
FAIL: expected "Email required", got ""
```

**GREEN**
```go
func SubmitForm(data FormData) (Result, error) {
    if strings.TrimSpace(data.Email) == "" {
        return Result{Error: "Email required"}, nil
    }
    // ...
}
```

**Verify GREEN**
```
PASS
```

**REFACTOR**
Extract validation for multiple fields if needed.

Never fix bugs without a test. The test proves the fix and prevents regression.

## Common Rationalizations

| Excuse | Reality |
|--------|---------|
| "Too simple to test" | Simple code breaks. Test takes 30 seconds. |
| "I'll test after" | Tests passing immediately prove nothing. |
| "Tests after achieve same goals" | Tests-after = "what does this do?" Tests-first = "what should this do?" |
| "Already manually tested" | Ad-hoc ≠ systematic. No record, can't re-run. |
| "Deleting X hours is wasteful" | Sunk cost fallacy. Keeping unverified code is technical debt. |
| "Keep as reference, write tests first" | You'll adapt it. That's testing after. Delete means delete. |
| "Need to explore first" | Fine. Throw away exploration, start with TDD. |
| "Test hard = design unclear" | Listen to test. Hard to test = hard to use. |
| "TDD will slow me down" | TDD faster than debugging. Pragmatic = test-first. |
| "Manual test faster" | Manual doesn't prove edge cases. You'll re-test every change. |
| "Existing code has no tests" | You're improving it. Add tests for existing behavior. |
| "This is different because..." | No it's not. Delete code. Start over with TDD. |

## Red Flags — STOP and Start Over

- Code before test
- Test after implementation
- Test passes immediately
- Can't explain why test failed
- Tests added "later"
- Rationalizing "just this once"
- "I already manually tested it"
- "Tests after achieve the same purpose"
- "It's about spirit not ritual"
- "Keep as reference" or "adapt existing code"
- "Already spent X hours, deleting is wasteful"
- "TDD is dogmatic, I'm being pragmatic"
- "This is different because..."

**All of these mean: Delete code. Start over with TDD.**

## When Stuck

| Problem | Solution |
|---------|----------|
| Don't know how to test | Write wished-for API. Write assertion first. Ask user. |
| Test too complicated | Design too complicated. Simplify interface. |
| Must mock everything | Code too coupled. Use dependency injection. |
| Test setup huge | Extract helpers. Still complex? Simplify design. |

## Testing Anti-Patterns

**Core principle: Test what the code does, not what the mocks do.**

When adding mocks or test utilities, read [testing-anti-patterns.md](references/testing-anti-patterns.md).

**The Iron Rules of Mocking:**
1. NEVER test mock behavior
2. NEVER add test-only methods to production classes
3. NEVER mock without understanding dependencies
4. NEVER create incomplete mock data — mirror real API completely

**Red flags in tests:**
- Assertion checks for `*-mock` test IDs
- Methods only called in test files
- Mock setup is >50% of test
- Test fails when you remove mock
- Can't explain why mock is needed
- Mocking "just to be safe"

**When mocks become too complex**, consider integration tests with real components — often simpler than elaborate mocking.

**If you're testing mock behavior, you violated TDD.** You added mocks without watching the test fail against real code first.

Fix: Test real behavior or question why you're mocking at all.

## Verification Checklist

Before marking work complete:

- [ ] Every new function/method has a test
- [ ] Watched each test **fail** before implementing
- [ ] Each test failed for expected reason (feature missing, not typo)
- [ ] Wrote minimal code to pass each test
- [ ] All tests pass — no regressions
- [ ] Output clean (no errors, warnings)
- [ ] Tests use real code (mocks only if unavoidable)
- [ ] Edge cases and errors covered
- [ ] No dead test code (commented-out assertions, skipped tests)

Can't check all boxes? You skipped TDD. Start over.

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
- [Testing Anti-Patterns](references/testing-anti-patterns.md) — Mock 误用、测试专用方法、不完整 Mock 数据

## Final Rule

```
Production code → test exists and failed first
Otherwise → not TDD
```

No exceptions without user's explicit permission.
