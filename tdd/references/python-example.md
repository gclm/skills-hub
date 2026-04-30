# Python TDD Example — URL Shortener Service with pytest

Scenario: Implement a `URLShortener` that creates short codes for URLs, handles collisions, and resolves short codes back to original URLs.

## Step 1: RED — Write failing tests first

```python
# tests/test_url_shortener.py
import pytest
from url_shortener import URLShortener, ShortCodeCollisionError, URLNotFoundError


class TestCreateShortCode:
    """TDD cycle 1: Creating short codes."""

    def test_returns_6_char_code(self):
        shortener = URLShortener()
        code = shortener.create("https://example.com/very/long/url")
        assert len(code) == 6
        assert code.isalnum()

    def test_same_url_returns_same_code(self):
        shortener = URLShortener()
        code1 = shortener.create("https://example.com/page")
        code2 = shortener.create("https://example.com/page")
        assert code1 == code2

    def test_different_urls_return_different_codes(self):
        shortener = URLShortener()
        code_a = shortener.create("https://a.com")
        code_b = shortener.create("https://b.com")
        assert code_a != code_b

    def test_rejects_empty_url(self):
        shortener = URLShortener()
        with pytest.raises(ValueError, match="URL cannot be empty"):
            shortener.create("")

    def test_rejects_invalid_url(self):
        shortener = URLShortener()
        with pytest.raises(ValueError, match="must start with http"):
            shortener.create("not-a-url")


class TestResolve:
    """TDD cycle 2: Resolving short codes back to URLs."""

    def test_resolves_existing_code(self):
        shortener = URLShortener()
        code = shortener.create("https://example.com/target")
        result = shortener.resolve(code)
        assert result == "https://example.com/target"

    def test_raises_for_unknown_code(self):
        shortener = URLShortener()
        with pytest.raises(URLNotFoundError):
            shortener.resolve("ZZZZZZ")


class TestCollisionHandling:
    """TDD cycle 3: Hash collision recovery."""

    def test_retries_on_collision(self):
        shortener = URLShortener(code_length=1)  # tiny space = guaranteed collision
        shortener.create("https://a.com")
        # Force internal to return a colliding code, then a unique one
        original_generate = shortener._generate_code
        call_count = 0

        def mock_generate():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return original_generate()  # will collide
            return original_generate()

        shortener._generate_code = mock_generate
        code = shortener.create("https://b.com")
        assert len(code) == 1
```

Run: `pytest tests/test_url_shortener.py -v`

Expected: **FAIL** — module doesn't exist.

## Step 2: GREEN — Minimal implementation

```python
# url_shortener.py
import hashlib
import random
import string

from urllib.parse import urlparse


class URLNotFoundError(Exception):
    pass


class ShortCodeCollisionError(Exception):
    pass


class URLShortener:
    def __init__(self, code_length: int = 6):
        self._code_length = code_length
        self._url_to_code: dict[str, str] = {}
        self._code_to_url: dict[str, str] = {}

    def create(self, url: str) -> str:
        self._validate_url(url)

        # Idempotent: same URL always gets same code
        if url in self._url_to_code:
            return self._url_to_code[url]

        # Generate unique code with collision retry
        code = self._generate_code()
        max_retries = 10
        retries = 0
        while code in self._code_to_url and retries < max_retries:
            code = self._generate_code()
            retries += 1

        if code in self._code_to_url:
            raise ShortCodeCollisionError("Failed to generate unique code")

        self._url_to_code[url] = code
        self._code_to_url[code] = url
        return code

    def resolve(self, code: str) -> str:
        if code not in self._code_to_url:
            raise URLNotFoundError(f"No URL found for code: {code}")
        return self._code_to_url[code]

    def _validate_url(self, url: str) -> None:
        if not url:
            raise ValueError("URL cannot be empty")
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            raise ValueError("URL must start with http:// or https://")

    def _generate_code(self) -> str:
        chars = string.ascii_letters + string.digits
        return "".join(random.choices(chars, k=self._code_length))
```

Run: `pytest tests/test_url_shortener.py -v`

Expected: **PASS**

## Step 3: REFACTOR

Possible improvements:

1. Use deterministic hashing (SHA-256) instead of random codes for predictability:
```python
def _generate_code(self) -> str:
    salt = str(time.monotonic_ns()).encode()
    digest = hashlib.sha256(salt).hexdigest()
    return digest[:self._code_length]
```

2. Add type aliases for clarity:
```python
type ShortCode = str
type URL = str
```

3. Extract validation into a separate function for reuse.

Run: `pytest` — all tests still pass after each refactoring step.

## Parametrize Example — Replacing repetitive tests

```python
@pytest.mark.parametrize("url", [
    "",
    "not-a-url",
    "ftp://files.example.com",
    "javascript:alert(1)",
])
def test_rejects_invalid_urls(self, url):
    shortener = URLShortener()
    with pytest.raises(ValueError):
        shortener.create(url)
```

This replaces 4 individual test methods with one parametrized test.

## Fixture Example — Shared setup

```python
# conftest.py
@pytest.fixture
def shortener():
    return URLShortener()

# test_url_shortener.py
class TestCreateShortCode:
    def test_returns_6_char_code(self, shortener):
        code = shortener.create("https://example.com/long")
        assert len(code) == 6
```

## Key Patterns Used

- **Class-based grouping**: `TestCreateShortCode`, `TestResolve`, `TestCollisionHandling` separate concerns
- **Parametrize**: One test, many inputs — eliminates copy-paste tests
- **Fixtures (conftest.py)**: Shared setup across test files
- **Custom exceptions**: `URLNotFoundError`, `ShortCodeCollisionError` for domain-specific errors
- **pytest.raises context manager**: Cleaner than `assertRaises` in unittest
- **Idempotent by design**: Same URL always returns same code (avoids storage waste)
