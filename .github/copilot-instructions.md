## Code Style Rules

### General Principles

- **Generic Code style** - code interfaces must be well designed, code must follow SOLID principles for class-based code, functions should be small and single-purpose, and code must be covered by tests. Using `# noqa` is forbidden. Using `from __future__ import annotations` is forbidden.
- **SOLID Principles**: Single Responsibility (each class/function does one thing), Open/Closed (open for extension, closed for modification), Liskov Substitution (subtypes must be substitutable), Interface Segregation (no fat interfaces), Dependency Inversion (depend on abstractions).
- **DRY (Don't Repeat Yourself)**: Extract common logic into reusable functions/classes. Avoid code duplication.
- **KISS (Keep It Simple, Stupid)**: Prefer simple, straightforward solutions over complex ones. Avoid premature optimization.
- **Code Organization**: Group related functionality together. Use clear module/package structure. Avoid circular dependencies.

### Documentation

- **Docstrings**: Use Google-style docstrings for all public classes/functions; docformatter is part of the formatting chain to enforce style. For trivial function signatures, omit parameter descriptions if they add no value.
- **Comments**: Use comments sparingly to explain why code does something non-obvious; avoid restating what the code does, make the code as self-explanatory as possible.
- **Module Docstrings**: Every module should have a docstring describing its purpose and main contents.
- **README**: Keep README.md up to date with setup instructions, usage examples, and project overview.

### Testing

- **Tests**: Tests must be implemented with Pytest and use (existing) fixtures where applicable. Each new feature must have unit tests covering edge cases and error handling. Integration tests should validate interactions between components and e2e execution. Tests must be isolated, idempotent, and stateless. Don't write test function docstrings unless absolutely necessary, the name of the test function must be self-descriptive and must well describe the test case. Using `# pragma: no cover` is forbidden.
- **Test Organization**: Mirror the source code structure in tests. Use `tests/` directory at project root.
- **Test Naming**: Use descriptive names like `test_function_name_with_condition_expected_behavior`.
- **Fixtures**: Use pytest fixtures for common setup/teardown. Scope fixtures appropriately (`function`, `class`, `module`, `session`).
- **Mocking**: Use `pytest-mock` or `unittest.mock` for mocking external dependencies. Mock at the boundary of your code.
- **Parametrization**: Use `@pytest.mark.parametrize` for testing multiple scenarios with the same logic.
- **Coverage**: Aim for high test coverage (>80%), but focus on meaningful tests over coverage metrics.

### Code Formatting & Linting

- **Line length & formatting**: Ruff format is configured for 120 characters (`pyproject.toml`). Let the formatters re-flow code instead of manual wrapping.
- **Ruff**: Use Ruff for linting and formatting. Run before committing code.
- **Import Ordering**: Follow isort standards: stdlib, third-party, first-party. Ruff handles this automatically.
- **Trailing Commas**: Use trailing commas in multi-line data structures for cleaner diffs.
- **String Quotes**: Be consistent with quote style (single or double). Ruff will enforce consistency.

### Type Hints

- **Typing**: Mypy is part of the default lint chain. All code must be typed. Use inbuilt types where possible (for example, `list[str]` instead of `List[str]`). Use as specific types as possible (for example, `dict[str, int]` instead of `Dict[Any, Any]`). Avoid using types like `Any` or `object` unless absolutely necessary. Using `# type: ignore` is forbidden.
- **Return Types**: Always specify return types, including `-> None` for functions that don't return values.
- **Optional Types**: Use `Type | None` syntax (PEP 604) instead of `Optional[Type]`.
- **TypedDict**: Use for dictionaries with known structure instead of `dict[str, Any]`.
- **Protocols**: Use `typing.Protocol` for structural subtyping and duck typing.
- **Generics**: Use generic types for containers and reusable components.

### Data Validation

- **Pydantic**: Use strictly Pydantic version 2. Use Pydantic models for data, parameter and config validation.
- **Field Validation**: Use Pydantic's `field_validator` for custom validation logic.
- **Model Config**: Use `model_config` for configuring model behavior (e.g., `frozen=True` for immutability).
- **Serialization**: Use `.model_dump()` and `.model_dump_json()` for serialization.

### Error Handling

- **Exceptions**: Use built-in exceptions where appropriate. Create custom exceptions for domain-specific errors.
- **Exception Hierarchy**: Inherit from appropriate base exceptions. Group related exceptions.
- **Error Messages**: Provide clear, actionable error messages. Include context and potential solutions.
- **Try/Except**: Keep try blocks small. Catch specific exceptions, not bare `except:`.
- **Resource Cleanup**: Use context managers (`with` statement) for resource management.
- **Logging Errors**: Log exceptions with full context before re-raising or handling.

### Logging

- **Logging**: Use a project-wide setup logging function. Reuse logger objects where applicable.
- **Logger Per Module**: Create logger per module using `logger = logging.getLogger(__name__)`.
- **Log Levels**: Use appropriate levels: DEBUG (detailed diagnostic), INFO (general info), WARNING (warning), ERROR (error occurred), CRITICAL (critical failure).
- **Structured Logging**: Include relevant context in log messages (user ID, request ID, etc.).
- **No Print Statements**: Use logging instead of `print()` for any output that's not user-facing.

### Naming Conventions

- **Variables & Functions**: Use `snake_case` for variables, functions, and methods.
- **Classes**: Use `PascalCase` for class names.
- **Constants**: Use `UPPER_SNAKE_CASE` for module-level constants.
- **Private Members**: Prefix with single underscore `_private_method` for internal use.
- **Descriptive Names**: Use clear, descriptive names. Avoid abbreviations unless widely known.
- **Boolean Names**: Use `is_`, `has_`, `can_` prefixes for boolean variables/functions.

### Dependencies

- **Dependency Management**: Use Poetry for dependency management. Lock dependencies with `poetry.lock`.
- **Version Constraints**: Use appropriate version constraints (^, ~, >=). Pin exact versions only when necessary.
- **Minimal Dependencies**: Avoid adding dependencies for trivial functionality. Prefer stdlib when possible.
- **Security**: Regularly update dependencies. Run security audits with `poetry audit` or similar tools.

### Code Structure

- **Function Length**: Keep functions under 50 lines. Extract complex logic into helper functions.
- **Class Size**: Classes should have a single responsibility. Large classes indicate need for refactoring.
- **Nesting**: Avoid deep nesting (>3 levels). Use early returns and guard clauses.
- **Magic Numbers**: Replace magic numbers with named constants.
- **Configuration**: Externalize configuration. Use environment variables or config files, validated with Pydantic.

### Performance

- **Premature Optimization**: Avoid premature optimization. Profile before optimizing.
- **List Comprehensions**: Use comprehensions for simple transformations, but prefer explicit loops for complex logic.
- **Generators**: Use generators for large datasets to save memory.
- **Caching**: Use `functools.lru_cache` or `functools.cache` for expensive, pure functions.

### Security

- **Input Validation**: Validate all external input using Pydantic or similar.
- **SQL Injection**: Use parameterized queries or ORMs. Never concatenate SQL strings.
- **Secrets**: Never hardcode secrets. Use environment variables or secret management services.
- **Dependencies**: Keep dependencies updated to patch security vulnerabilities.

### Version Control

- **Commits**: Write clear, descriptive commit messages. Use conventional commit format when possible.
- **Branch Strategy**: Use feature branches. Keep main/master stable.
- **Pull Requests**: Use PRs for code review. Include description of changes and testing done.
- **.gitignore**: Keep comprehensive `.gitignore` for Python projects (venv, __pycache__, .pyc, etc.).

## Code Development Workflow

When writing or modifying code, follow these steps in order:

### 1. Analyze & Plan
- **Understand Requirements**: Clarify what needs to be built or changed. Ask questions if requirements are unclear.
- **Search Existing Code**: Check the codebase for similar functionality that can be reused or extended. Use grep/semantic search to find relevant code.
- **Review Existing Patterns**: Identify established patterns, conventions, and architectural decisions in the codebase. Follow them consistently.
- **Check Dependencies**: Review existing dependencies before adding new ones. Prefer stdlib or existing dependencies over adding new packages.
- **Design Interfaces**: Plan function signatures, class structures, and module boundaries before implementation.

### 2. Implement
- **Write Clean Code**: Follow all code style rules, SOLID principles, and naming conventions from this document.
- **Add Type Hints**: Include comprehensive type hints for all functions, methods, and variables.
- **Add Docstrings**: Write Google-style docstrings for all public classes and functions but only if they are complex .
- **Handle Errors**: Implement proper error handling with specific exceptions and helpful error messages.
- **Add Logging**: Include appropriate logging statements at key points (DEBUG for details, INFO for operations, WARNING/ERROR for issues).
- **Avoid Code Smells**: Watch for common code smells:
  - Long functions (>50 lines)
  - Large classes with multiple responsibilities
  - Deep nesting (>3 levels)
  - Duplicate code
  - Magic numbers/strings
  - God objects
  - Tight coupling
  - Feature envy (methods that use more data from other classes than their own)

### 3. Write Tests
- **Create Test File**: Create or update test file mirroring the source structure (e.g., `src/module.py` → `tests/test_module.py`).
- **Write Unit Tests**: Cover all public functions/methods with unit tests. Test edge cases, error conditions, and normal operation.
- **Use Fixtures**: Leverage pytest fixtures for common setup/teardown and test data.
- **Test Error Handling**: Verify that exceptions are raised correctly and error messages are appropriate.
- **Parametrize Tests**: Use `@pytest.mark.parametrize` for testing multiple scenarios with the same logic.
- **Mock Dependencies**: Mock external dependencies (APIs, databases, file I/O) to keep tests isolated and fast.

### 4. Validate Code Quality
- **Run Linters**: Execute Ruff to check for code quality issues: `poetry run ruff check .`
- **Run Formatters**: Format code with Ruff: `poetry run ruff format .`
- **Type Check**: Run Mypy to verify type correctness: `poetry run mypy .`
- **Run Tests**: Execute all tests with coverage: `poetry run pytest --cov`
- **Review Coverage**: Ensure new code has adequate test coverage (>80%). Check coverage report for untested branches.
- **Fix All Issues**: Address all linting errors, type errors, and test failures. Do not proceed with warnings or failures.

### 5. Review & Refactor
- **Self-Review**: Read through the code as if reviewing someone else's work. Check for:
  - Code clarity and readability
  - Proper naming (descriptive, follows conventions)
  - Appropriate abstraction level
  - Missing edge cases
  - Security vulnerabilities (SQL injection, hardcoded secrets, unvalidated input)
- **Refactor**: Improve code structure if needed. Extract complex logic into helper functions. Remove duplication.
- **Update Documentation**: Update README.md, module docstrings, or other documentation if the changes affect public interfaces or usage.
- **Verify Tests Pass**: Re-run tests after any refactoring to ensure nothing broke.

### 6. Final Checks
- **Run Full Test Suite**: Execute all tests one final time: `poetry run pytest`
- **Check Git Status**: Review changed files to ensure no unintended modifications.
- **Verify No Debugging Code**: Remove any debug print statements, commented-out code, or temporary changes.
- **Commit Atomically**: Commit related changes together with a clear, descriptive commit message.

