```markdown
# skills-hub Development Patterns

> Auto-generated skill from repository analysis

## Overview
This skill covers the core development patterns and conventions used in the `skills-hub` TypeScript repository. It provides guidance on file organization, code style, commit practices, and testing approaches, enabling contributors to write consistent and maintainable code.

## Coding Conventions

### File Naming
- Use **camelCase** for file names.
  - Example: `userProfile.ts`, `getSkills.ts`

### Import Style
- Use **relative imports** for modules within the project.
  - Example:
    ```typescript
    import { getUser } from './getUser';
    ```

### Export Style
- Use **named exports** for all exported functions, types, and constants.
  - Example:
    ```typescript
    // In userProfile.ts
    export function getUserProfile(id: string) { ... }
    ```

### Commit Messages
- Follow **conventional commit** format.
- Use the `feat` prefix for new features.
  - Example:
    ```
    feat: add user profile fetching logic
    ```

## Workflows

_No automated workflows detected in this repository._

## Testing Patterns

- Test files are named with the pattern `*.test.*`.
  - Example: `userProfile.test.ts`
- Testing framework is **unknown** (not detected).
- Place test files alongside the modules they test or in a dedicated test directory.

  Example test file:
  ```typescript
  // userProfile.test.ts
  import { getUserProfile } from './userProfile';

  describe('getUserProfile', () => {
    it('returns user data for valid id', () => {
      // test implementation
    });
  });
  ```

## Commands
| Command | Purpose |
|---------|---------|
| /commit-convention | Show commit message guidelines |
| /coding-style      | Show code style and file naming conventions |
| /test-patterns     | Show how to write and organize tests |
```
