# Performance and Resource Checklist

## Lock Contention

### Hot Path Lock Analysis
- Lock held during I/O (network, disk, database query)
- Single global lock serializing unrelated operations
- Read-heavy operations using Mutex instead of RWMutex
- Lock acquired in loop body instead of outside loop

### Measurement Questions
- "What is the critical section size? Can it be缩小?"
- "How many goroutines contend for this lock?"
- "Is this lock on the hot path (called per request/tool call/tick)?"

### Common Anti-patterns
```go
// BAD: global lock for all DB operations
type Store struct {
    db *sql.DB  // sql.DB is already thread-safe
    mu sync.RWMutex  // redundant for reads, too coarse for writes
}

// BETTER: let driver handle concurrency, or per-table locks
type Store struct {
    db *sql.DB
    // no application-level lock — rely on SQLite WAL + connection pool
}
```

---

## Database Performance

### Query Efficiency
- N+1 queries: loop that makes a query per item instead of batch
- Missing indexes: queries on unindexed columns
- Full table scans: `SELECT *` when only few columns needed
- No pagination: loading entire dataset into memory

### Index Strategy
- Composite index for multi-column WHERE clauses
- Index column order should match query predicate order
- Covering index to avoid table lookups
- Partial index for filtered queries

### PRAGMA Tuning (SQLite)
- `PRAGMA journal_mode=WAL` — concurrent reads + single writer
- `PRAGMA synchronous=NORMAL` — safe under WAL,减少 fsync
- `PRAGMA busy_timeout=5000` — prevent immediate lock failure
- `PRAGMA cache_size=-64000` — 64MB page cache
- `PRAGMA journal_size_limit=67108864` — prevent WAL无限增长

### Connection Pool
- `SetMaxOpenConns(1)` for SQLite single-writer模式
- `SetMaxIdleConns` to reuse connections
- `SetConnMaxLifetime` to prevent stale connections

---

## Memory Allocation

### Hotspot Patterns
- String concatenation in loops — use `strings.Builder` or `strings.Join`
- `fmt.Sprintf` in hot path — consider `strconv` or direct write
- `[]byte` to `string` conversion (copies data) — use `unsafe.String` if truly hot
- Repeated `make` + `append` — pre-allocate with known capacity
- `json.Marshal`/`json.Unmarshal` in loops — reuse encoder/decoder

### Questions to Ask
- "Is this allocation in a hot path (per request, per tool call, per message)?"
- "Can we pre-allocate with known capacity?"
- "Is this string concatenation in a loop?"

### Benchmarking
```go
// Use testing.B for hot paths
func BenchmarkConcat(b *testing.B) {
    for i := 0; i < b.N; i++ {
        var s string
        for j := 0; j < 100; j++ {
            s += "x"  // BAD: O(n²)
        }
    }
}
```

---

## Polling vs Event-Driven

### Polling Anti-patterns
- Fixed-interval ticker polling database for changes (wastes CPU + lock)
- Busy-wait loop with `time.Sleep` instead of channel notification
- Checking shared variable in loop instead of using `sync.Cond` or channel

### Event-Driven Alternatives
- Use `time.Timer` with dynamic duration until next known event
- Use channel notification when state changes
- Use `sync.Cond` for broadcast to multiple waiters
- Use inotify/fsnotify for file system changes

```go
// BAD: 1-second poll
ticker := time.NewTicker(time.Second)
for range ticker.C {
    checkDatabase()
}

// GOOD: timer until next known event
timer := time.NewTimer(time.Until(nextRunAt))
select {
case <-timer.C:
    execute()
case <-stopCh:
    return
}
```

---

## Caching

### Cache Strategy
- Cache without TTL — stale data served indefinitely
- Cache without invalidation — data updated but cache not cleared
- Cache key collisions — insufficient key uniqueness
- Caching user-specific data globally — security/privacy issue
- Unbounded cache — memory grows without limit

### Cache Invalidation
- Time-based TTL
- Event-driven invalidation (on write, invalidate related cache entries)
- Version-based (cache key includes version/hash)
- LRU eviction for bounded caches

### Questions to Ask
- "Is this result cacheable? Should it be?"
- "What's the cache invalidation strategy?"
- "Is there a size limit? What happens when it's full?"
- "Is the same computation done multiple times?"

---

## File I/O

### Patterns to Flag
- Reading entire large file into memory — use streaming
- No file descriptor cleanup (missing `defer f.Close()`)
- Opening same file repeatedly in loop
- No log rotation — files grow without bound
- Sync I/O on hot path blocking the main goroutine

### Log Management
- Log files with no rotation or size limit
- Log writes to disk on every message (no buffering)
- Debug-level logs in production hot path

---

## CPU-Intensive Operations

### Hot Path Analysis
- Regex compilation in loop — compile once, reuse
- JSON parsing in loop — reuse decoder
- Expensive string operations (multiple `strings.Replace` chains)
- Sorting in loop when result could be cached

### Concurrency for CPU Work
- Use `runtime.NumCPU()` to size worker pools
- Use `errgroup.Group` for bounded parallel execution
- Avoid goroutine per item for large batches — use worker pool

---

## Resource Limits

### Unbounded Growth
- Collections that grow without limit (history, cache, log buffer)
- Goroutines started without concurrency limit
- Channel buffer size too small causing drops, or too large causing memory pressure
- File handles opened without limit

### Timeout and Deadlines
- External calls without timeout (HTTP, database, shell commands)
- Context without deadline on long operations
- No overall operation timeout (e.g., Agent loop runs forever)

### Graceful Degradation
- What happens when disk is full?
- What happens when memory is exhausted?
- What happens when network is unavailable?
- Are there circuit breakers for external dependencies?

---

## Checklist for Review

- [ ] No N+1 queries — batch operations where possible
- [ ] Appropriate indexes for query patterns
- [ ] SQLite PRAGMA tuned for workload
- [ ] No polling when event-driven is possible
- [ ] Hot path allocations minimized (Builder, pre-allocation)
- [ ] Regex/JSON compiled once, reused
- [ ] Caches have TTL and size limits
- [ ] Cache invalidation strategy defined
- [ ] File I/O uses streaming for large files
- [ ] Log rotation configured
- [ ] No unbounded collections
- [ ] All external calls have timeouts
- [ ] Goroutine concurrency is bounded
- [ ] Graceful shutdown waits for all resources
