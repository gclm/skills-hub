# Go TDD Example — User Repository with Error Handling

Scenario: Implement a `UserRepository` that can find users by email, with proper error handling for "not found" and "database error" cases.

## Step 1: RED — Write failing tests first

```go
// user_test.go
package user

import (
    "errors"
    "testing"

    "github.com/stretchr/testify/assert"
    "github.com/stretchr/testify/require"
)

// Table-driven test for FindByEmail
func TestFindByEmail(t *testing.T) {
    tests := []struct {
        name        string
        email       string
        wantUser    *User
        wantErr     error
    }{
        {
            name:     "found",
            email:    "alice@example.com",
            wantUser: &User{ID: 1, Email: "alice@example.com", Name: "Alice"},
            wantErr:  nil,
        },
        {
            name:     "not found",
            email:    "missing@example.com",
            wantUser: nil,
            wantErr:  ErrUserNotFound,
        },
    }

    for _, tt := range tests {
        t.Run(tt.name, func(t *testing.T) {
            repo := NewMockRepository()
            repo.Seed([]*User{{ID: 1, Email: "alice@example.com", Name: "Alice"}})

            got, err := repo.FindByEmail(t.Context(), tt.email)

            if tt.wantErr != nil {
                assert.ErrorIs(t, err, tt.wantErr)
                assert.Nil(t, got)
            } else {
                require.NoError(t, err)
                assert.Equal(t, tt.wantUser.Email, got.Email)
                assert.Equal(t, tt.wantUser.Name, got.Name)
            }
        })
    }
}

// Separate test for database error
func TestFindByEmail_DBError(t *testing.T) {
    repo := NewMockRepository()
    repo.InjectError(errors.New("connection lost"))

    got, err := repo.FindByEmail(t.Context(), "alice@example.com")

    assert.Nil(t, got)
    assert.ErrorContains(t, err, "connection lost")
}
```

Run: `go test -run TestFindByEmail ./...`

Expected: **FAIL** — `User`, `UserRepository`, `ErrUserNotFound` don't exist yet.

## Step 2: GREEN — Minimal implementation

```go
// user.go
package user

import (
    "context"
    "errors"
    "sync"
)

var ErrUserNotFound = errors.New("user not found")

type User struct {
    ID    int64
    Email string
    Name  string
}

type Repository interface {
    FindByEmail(ctx context.Context, email string) (*User, error)
}

type mockRepository struct {
    mu     sync.RWMutex
    users  []*User
    dbErr  error
}

func NewMockRepository() *mockRepository {
    return &mockRepository{}
}

func (r *mockRepository) Seed(users []*User) {
    r.mu.Lock()
    defer r.mu.Unlock()
    r.users = append(r.users, users...)
}

func (r *mockRepository) InjectError(err error) {
    r.dbErr = err
}

func (r *mockRepository) FindByEmail(_ context.Context, email string) (*User, error) {
    if r.dbErr != nil {
        return nil, r.dbErr
    }
    r.mu.RLock()
    defer r.mu.RUnlock()
    for _, u := range r.users {
        if u.Email == email {
            return u, nil
        }
    }
    return nil, ErrUserNotFound
}
```

Run: `go test -run TestFindByEmail ./...`

Expected: **PASS**

## Step 3: REFACTOR — Clean up

After GREEN passes, look for improvements:

1. `FindByEmail` uses linear scan — for a real DB repo this would use a query, but mock is fine.
2. `mockRepository` could use a map for O(1) lookup instead of slice scan:

```go
func (r *mockRepository) FindByEmail(_ context.Context, email string) (*User, error) {
    if r.dbErr != nil {
        return nil, r.dbErr
    }
    r.mu.RLock()
    defer r.mu.RUnlock()
    for _, u := range r.users {
        if u.Email == email {
            return u, nil
        }
    }
    return nil, ErrUserNotFound
}
```

Run: `go test ./...` — all tests still pass after refactor.

## Key Patterns Used

- **Table-driven tests**: Multiple cases in one test function via `[]struct{}`
- **Sentinel errors**: `ErrUserNotFound` as a package-level `var` for `errors.Is()` matching
- **Interface + Mock**: `Repository` interface enables swapping real DB with mock
- **t.Context()**: Go 1.24+ built-in test context (use `context.Background()` for older versions)
- **testify hierarchy**: `require` for fatal assertions (stops test), `assert` for non-fatal
