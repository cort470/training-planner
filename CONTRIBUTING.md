# Contributing to Human-in-the-Loop Training Planner

Thank you for your interest in contributing! This project demonstrates AI alignment principles in fitness applications, with a focus on transparency, interpretability, and human agency.

## Code of Conduct

- Be respectful and constructive in all interactions
- Focus on technical merit and alignment with project principles
- Remember: refusal is a feature, not a bug
- Prioritize interpretability over optimization

## Getting Started

### Development Setup

1. **Fork and clone the repository**
   ```bash
   git clone <your-fork-url>
   cd training-planner
   ```

2. **Create a virtual environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run tests to verify setup**
   ```bash
   python3 -m pytest
   ```
   Expected: 105 passed, 1 skipped

### Development Workflow

1. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes**
   - Write tests first (TDD approach)
   - Implement the feature
   - Update documentation

3. **Run the test suite**
   ```bash
   # Run all tests
   python3 -m pytest -v

   # Run specific test module
   python3 -m pytest tests/test_validator.py -v

   # Run with coverage
   python3 -m pytest --cov=src tests/
   ```

4. **Format and lint your code**
   ```bash
   # Format with black
   python3 -m black src/ tests/

   # Lint with ruff
   python3 -m ruff check src/ tests/

   # Type check with mypy
   python3 -m mypy src/
   ```

5. **Commit your changes**
   ```bash
   git add .
   git commit -m "feat: add your feature description"
   ```

## Contribution Guidelines

### Code Style

- **Follow PEP 8** Python style guidelines
- **Use Black** for code formatting (line length: 100)
- **Use type hints** throughout the codebase
- **Write descriptive docstrings** for all public functions and classes
- **Keep functions focused** - single responsibility principle

Example:
```python
def calculate_sleep_deviation_penalty(
    self, user_profile: UserProfile
) -> float:
    """
    Calculate penalty for sleep deviation from optimal 8 hours.

    Args:
        user_profile: User profile containing sleep hours

    Returns:
        Penalty value between 0.0 (optimal) and 1.0 (severe deviation)
    """
    sleep_hours = user_profile.current_state.sleep_hours
    optimal_sleep = 8.0

    if sleep_hours >= optimal_sleep:
        return 0.0  # No penalty for adequate sleep

    # Linear penalty below 7 hours, exponential below 6 hours
    deviation = optimal_sleep - sleep_hours
    if sleep_hours < 6.0:
        return min(1.0, deviation * 0.3)
    return deviation * 0.15
```

### Testing Requirements

All contributions must include tests:

1. **Unit tests** for new functions/methods
2. **Integration tests** for new features
3. **Test fixtures** for new scenarios
4. **Maintain coverage** at 80%+ for new code

Test file structure:
```python
import pytest
from pathlib import Path
import json

from src.validator import MethodologyValidator
from src.schemas import UserProfile

@pytest.fixture
def methodology():
    """Load the polarized methodology for testing."""
    methodology_path = Path("models/methodology_polarized.json")
    with open(methodology_path) as f:
        data = json.load(f)
    return MethodologyModelCard(**data)

@pytest.fixture
def valid_user():
    """Load valid user profile."""
    profile_path = Path("tests/fixtures/test_user_valid.json")
    with open(profile_path) as f:
        data = json.load(f)
    return UserProfile(**data)

def test_feature_works_as_expected(methodology, valid_user):
    """Test that the feature produces expected results."""
    # Arrange
    validator = MethodologyValidator(methodology)

    # Act
    result = validator.validate(valid_user)

    # Assert
    assert result.approved is True
    assert result.reasoning_trace.result == "approved"
```

### Documentation

- **Update README.md** if adding new features or CLI commands
- **Add docstrings** to all public APIs
- **Create usage examples** for new functionality
- **Document reasoning** in code comments where logic isn't obvious

### Commit Messages

Follow conventional commits format:

- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation changes
- `test:` Test additions or changes
- `refactor:` Code refactoring
- `chore:` Build/tooling changes

Examples:
```
feat: add sensitivity analysis for volume changes
fix: correct fragility calculation for edge case
docs: update README with API usage examples
test: add test cases for high fragility scenarios
```

## Types of Contributions

### 1. Bug Fixes

- Create an issue describing the bug
- Include steps to reproduce
- Write a failing test that demonstrates the bug
- Fix the bug
- Verify the test now passes

### 2. New Features

**Before starting:**
- Open an issue to discuss the feature
- Get alignment on approach
- Ensure it fits project principles

**Implementation:**
- Follow TDD approach (tests first)
- Update documentation
- Add usage examples
- Ensure backward compatibility

### 3. New Methodologies

To add a new training methodology:

1. **Read the methodology guide**
   - Review [docs/methodology_guide.md](docs/methodology_guide.md)
   - Understand the schema in [docs/schema_methodology.json](docs/schema_methodology.json)

2. **Create the methodology JSON**
   ```json
   {
     "id": "threshold_70_20_10_v1",
     "name": "Threshold 70/20/10",
     "version": "1.0.0",
     "description": "Threshold-focused training...",
     "safety_gates": [...],
     "assumptions": [...],
     "risk_profile": {...}
   }
   ```

3. **Add test fixtures**
   - Create user profiles that work with the methodology
   - Create edge case scenarios

4. **Write tests**
   ```python
   def test_threshold_methodology_validates_correctly():
       """Test that threshold methodology works as expected."""
       # Your test here
   ```

5. **Document the methodology**
   - Add reasoning for design choices
   - Cite scientific literature if applicable
   - Explain differences from existing methodologies

### 4. Documentation Improvements

Documentation is always welcome:
- Fix typos or unclear explanations
- Add more usage examples
- Improve API documentation
- Create tutorials or guides

### 5. Performance Optimizations

- Profile the code first to identify bottlenecks
- Write benchmarks to measure improvement
- Ensure tests still pass
- Document the optimization approach

## Project Principles to Follow

### 1. Transparency Over Performance
- Explain why, not just what
- Make assumptions explicit
- Document all decision points
- Reasoning traces are mandatory

### 2. Refusal as a Feature
- Don't water down safety gates
- Provide actionable alternatives when refusing
- Make refusal reasoning clear
- Test refusal scenarios thoroughly

### 3. Human Agency First
- Users should understand recommendations
- No "trust the algorithm" approaches
- Make uncertainty explicit
- Enable informed decision-making

### 4. Model-Based Design
- Methodologies are hypotheses, not truths
- Document limitations and boundaries
- Support multiple methodologies
- Make model assumptions explicit

## Review Process

1. **Automated checks** run on all PRs:
   - Tests must pass (105+ passing)
   - Code must be formatted (black)
   - Linting must pass (ruff)
   - Type checking must pass (mypy)

2. **Manual review** focuses on:
   - Alignment with project principles
   - Code quality and maintainability
   - Test coverage and quality
   - Documentation completeness

3. **Feedback** will be provided within:
   - Bug fixes: 2-3 days
   - New features: 1 week
   - Methodologies: 1-2 weeks

## Questions?

- Open an issue for questions about contributing
- Review existing issues and PRs for context
- Check [docs/prd_v3.txt](docs/prd_v3.txt) for project requirements

## Recognition

Contributors will be acknowledged in:
- README.md acknowledgments section
- Release notes
- Project documentation

Thank you for contributing to more transparent and interpretable fitness AI!
