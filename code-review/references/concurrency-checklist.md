# Concurrency and Race Condition Checklist

## Data Race Detection

### Shared State Access
- Multiple goroutines accessing shared variables without synchronization
- Global state or singletons modified concurrently
- Struct fields read in one goroutine while written in another (including string fields — Go string is 2-word header)
- Lazy initialization without proper locking (double-checked locking issues in Go is broken)
- Non-thread-safe collections (plain map) used in concurrent context

### Questions to Ask
- "What happens if two goroutines access this code simultaneously?"
- "Is this field written after construction? If so, is it protected?"
- "Does this getter return a pointer to mutable internal state?"
- "Would Go's race detector flag this?"

---

## Lock Analysis

### Lock Granularity
- Single global lock protecting unrelated operations (overly coarse)
- Lock held during I/O operations (network, disk, database)
- Nested lock acquisition (potential deadlock)
- Read-heavy workload using Mutex instead of RWMutex

### Lock Correctity
- Missing unlock on error paths (use `defer` consistently)
- Unlock in wrong order (deadlock risk with multiple locks)
- RLock used where write access is actually needed
- Copy-on-read vs pointer-return semantics under lock

### Common Anti-patterns
```go
// BAD: returns pointer to locked data
func (m *Manager) Get(id string) *Item {
    m.mu.RLock()
    defer m.mu.RUnlock()
    return m.items[id]  // caller can mutate after lock released
}

// BAD: lock gap — TOCTOU between check and use
func (m *Manager) Do(id string) {
    m.mu.Lock()
    item := m.items[id]
    m.mu.Unlock()
    // another goroutine can delete m.items[id] here
    item.Use()  // potential use-after-delete
}

// GOOD: return value copy
func (m *Manager) Get(id string) (Item, bool) {
    m.mu.RLock()
    defer m.mu.RUnlock()
    item, ok := m.items[id]
    return item, ok  // safe copy
}
```

---

## TOCTOU (Time-of-Check-Time-of-Use)

### Patterns to Flag
- `if exists(key) then use(key)` without atomic operation
- `if authorized then perform` where authorization can change between check and act
- File existence check followed by file operation (symlink attacks)
- Balance check followed by deduction
- Approval check followed by action execution

### Questions to Ask
- "Can the condition change between the check and the action?"
- "Is this operation atomic or can it be interrupted?"
- "What shared state does this code access between check and use?"

---

## Goroutine Lifecycle Management

### Goroutine Leaks
- Goroutines started without WaitGroup or cancellation mechanism
- `go func()` with `context.Background()` — cannot be cancelled by parent
- Channel operations that may block forever (unbuffered channel, no select with timeout)
- Goroutines holding references preventing GC

### Missing Lifecycle Controls
- No `Wait()` method to wait for goroutine completion
- No graceful shutdown — goroutines abandoned on exit
- Async hooks/tasks with no way to cancel on session end
- Fire-and-forget goroutines with no error reporting

### Best Practices
```go
// GOOD: tracked goroutine with WaitGroup
type Manager struct {
    wg sync.WaitGroup
}

func (m *Manager) Start() {
    m.wg.Add(1)
    go func() {
        defer m.wg.Done()
        // work
    }()
}

func (m *Manager) Wait() {
    m.wg.Wait()
}
```

---

## Channel Safety

### Patterns to Flag
- Send on closed channel (panic)
- Close channel multiple times (panic)
- Unbuffered channel with no receiver (goroutine leak)
- Select with no default in hot path (blocking)
- Channel used as signal but no synchronization for payload

### Backpressure
- Publishing to bounded channel without select/default (blocks publisher)
- Unbounded channel growing without limit
- Subscriber too slow causing event loss (acceptable if documented)

---

## Sync Primitives Selection

| Use Case | Primitive | Notes |
|----------|-----------|-------|
| Simple counter | `atomic.Int64` | Faster than Mutex for single value |
| Map with concurrent reads | `sync.RWMutex` | Or `sync.Map` for read-heavy |
| Once initialization | `sync.Once` | Correct double-checked locking |
| Broadcast to multiple waiters | `chan struct{}` + close | Or `sync.Cond` |
| Limit concurrent access | `semaphore.Weighted` | `golang.org/x/sync/semaphore` |
| Single-flight dedup | `singleflight.Group` | Prevent duplicate work |

---

## Database Concurrency

### SQLite-Specific
- WAL mode allows concurrent reads + single writer
- Application-level RWMutex may be redundant if driver is thread-safe
- `SetMaxOpenConns(1)` enforces single writer at connection pool level
- Busy timeout prevents immediate failure on lock contention

### General Patterns
- Missing optimistic locking (`version` column, `updated_at` checks)
- Read-modify-write without transaction isolation
- Counter increments without atomic operations (`UPDATE SET count = count + 1`)
- Unique constraint violations in concurrent inserts

---

## Checklist for Review

- [ ] All struct fields that are written after construction have synchronization
- [ ] Getters return value copies, not pointers to mutable state
- [ ] No TOCTOU between authorization/approval check and action execution
- [ ] All goroutines have lifecycle management (WaitGroup, context, or timeout)
- [ ] Async operations can be cancelled on shutdown
- [ ] Channels have appropriate buffering and backpressure handling
- [ ] No send-on-closed-channel risks
- [ ] Database operations use appropriate isolation level
- [ ] Application-level locks are not redundant with driver-level safety
- [ ] `go vet -race` passes on the codebase
