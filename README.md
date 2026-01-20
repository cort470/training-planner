# Human-in-the-Loop Training Planner

A decision-support tool for serious amateur triathletes that treats training methodologies as explicit models. The system prioritizes interpretability, human agency, and "Alignment-First" logic.

## 🎯 Core Principles

- **Models, Not Truths:** Training methodologies are documented hypotheses with explicit assumptions
- **Traceability:** Every recommendation traces back to inputs and rules
- **Constructive Refusal:** The system refuses unsafe guidance and provides actionable alternatives
- **Risk Quantification:** Fragility scores make plan robustness explicit and measurable

## ✨ Key Features

### Phase 1: Validation & Safety (✅ Complete)
- **Circuit Breakers:** Deterministic safety evaluation before plan generation
- **Refusal as a Feature:** Stops plan generation when safety or data gaps are detected
- **Reasoning Trace:** Shows the complete logic chain from input to output
- **49 passing tests** covering all validation scenarios

### Phase 2: Plan Generation & Risk Analysis (✅ Complete)
- **Fragility Score Calculation:** Quantifies user-specific risk using weighted penalty formula
- **Adaptive Plan Generation:** Creates 12-week structured training plans that adjust to fragility levels
- **Polarized 80/20 Methodology:** Implements evidence-based intensity distribution
- **Sensitivity Analysis:** Interactive "what-if" scenario exploration
- **Enhanced Reasoning Traces:** Documents fragility calculations and plan generation decisions
- **105 passing tests** covering fragility, planning, and sensitivity analysis

## 📁 Project Structure

```
training-planner/
├── README.md                           # This file
├── requirements.txt                    # Python dependencies
├── .gitignore                          # Git ignore rules
├── docs/
│   ├── prd_v3.txt                      # Product Requirements Document
│   ├── methodology_guide.md            # Guide for creating methodology cards
│   ├── schema_methodology.json         # Methodology JSON schema
│   └── schema_user_profile.json        # User profile JSON schema
├── models/
│   └── methodology_polarized.json      # Reference polarized 80/20 methodology
├── plans/                              # Generated training plans (gitignored)
│   └── .gitkeep
├── user_profiles/                      # User data (gitignored)
│   └── .gitkeep
├── reasoning_logs/                     # Generated traces (gitignored)
│   └── .gitkeep
├── src/
│   ├── __init__.py
│   ├── schemas.py                      # Pydantic models for validation
│   ├── validator.py                    # Circuit breaker logic
│   ├── fragility.py                    # F-Score calculation engine
│   ├── plan_schemas.py                 # Training plan data structures
│   ├── planner.py                      # Training plan generation
│   ├── sensitivity.py                  # "What-if" scenario analysis
│   ├── trace.py                        # Reasoning trace builder
│   └── cli.py                          # CLI interface
└── tests/
    ├── __init__.py
    ├── test_schemas.py                 # Schema validation tests
    ├── test_validator.py               # Circuit breaker tests (28 tests)
    ├── test_fragility.py               # Fragility calculation tests (20 tests)
    ├── test_planner.py                 # Plan generation tests (23 tests)
    ├── test_sensitivity.py             # Sensitivity analysis tests (14 tests)
    ├── test_trace.py                   # Reasoning trace tests (20 tests)
    └── fixtures/
        ├── test_user_valid.json        # Happy path scenario
        ├── test_user_injury.json       # Injury refusal scenario
        ├── test_user_sleep.json        # Sleep threshold violation
        ├── test_user_multiple.json     # Multiple safety gate violations
        ├── test_user_low_fragility.json        # F-Score ~0.3
        ├── test_user_moderate_fragility.json   # F-Score ~0.5
        ├── test_user_high_fragility.json       # F-Score ~0.7
        ├── test_user_12_week_race.json         # Standard 12-week plan
        └── test_user_4_week_race.json          # Short 4-week plan
```

## 🚀 Getting Started

### Prerequisites

- Python 3.10 or higher
- pip

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd training-planner

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Running Tests

```bash
# Run all tests (106 total)
python3 -m pytest

# Run with coverage
python3 -m pytest --cov=src tests/

# Run specific test modules
python3 -m pytest tests/test_validator.py -v        # Validation tests
python3 -m pytest tests/test_fragility.py -v        # Fragility tests
python3 -m pytest tests/test_planner.py -v          # Plan generation tests
python3 -m pytest tests/test_sensitivity.py -v      # Sensitivity analysis tests

# Run with detailed output
python3 -m pytest -v
```

Expected result: **105 passed, 1 skipped**

## 💻 Usage Examples

### 1. Validate a User Profile

```bash
# Validate an existing profile
python3 -m src.cli validate --profile tests/fixtures/test_user_valid.json

# Interactive profile creation and validation
python3 -m src.cli validate
```

The validation command will:
- Load the methodology and user profile
- Check all safety gates (injury, sleep, volume, stress, etc.)
- Calculate fragility score if validation passes
- Save reasoning trace to `reasoning_logs/`
- Display clear approval/refusal with detailed reasoning

### 2. View Methodology Details

```bash
# Show methodology information
python3 -m src.cli methodology --show models/methodology_polarized.json
```

### 3. Programmatic API Usage

```python
from pathlib import Path
import json
from src.validator import MethodologyValidator
from src.schemas import UserProfile
from src.fragility import FragilityCalculator
from src.planner import TrainingPlanGenerator

# Load methodology and user profile
validator = MethodologyValidator.from_file(
    Path("models/methodology_polarized.json")
)
with open("tests/fixtures/test_user_valid.json") as f:
    user_profile = UserProfile(**json.load(f))

# Validate
result = validator.validate(user_profile)

if result.approved:
    # Calculate fragility score
    calculator = FragilityCalculator(validator.methodology)
    fragility_result = calculator.calculate(user_profile)
    print(f"Fragility Score: {fragility_result.score:.2f}")
    print(f"Interpretation: {fragility_result.interpretation}")

    # Generate training plan
    generator = TrainingPlanGenerator(validator.methodology, result)
    plan = generator.generate(user_profile)
    print(f"Generated {plan.plan_duration_weeks}-week plan")
    print(f"Total weeks: {len(plan.weeks)}")

    # Save plan
    with open(f"plans/plan_{user_profile.athlete_id}.json", "w") as f:
        json.dump(plan.model_dump(mode="json"), f, indent=2, default=str)
else:
    print(f"Validation refused: {result.reasoning_trace.result}")
    for gate in result.reasoning_trace.safety_gates:
        print(f"  - {gate.condition}: {gate.reasoning}")
```

### 4. Sensitivity Analysis

```python
from src.sensitivity import SensitivityAnalyzer

# Create analyzer with baseline state
analyzer = SensitivityAnalyzer(
    methodology=validator.methodology,
    baseline_profile=user_profile,
    baseline_validation=result,
    baseline_plan=plan,
)

# Modify assumption and analyze impact
scenario_result = analyzer.modify_assumption(
    "current_state.sleep_hours",
    7.5  # Increase from 6.5
)

print(f"Original sleep: {scenario_result.original_value} hrs")
print(f"New sleep: {scenario_result.new_value} hrs")
print(f"Fragility change: {scenario_result.fragility_delta:.3f}")
print(f"Validation changed: {scenario_result.validation_changed}")

if scenario_result.plan_adjustments:
    print(f"HI sessions delta: {scenario_result.plan_adjustments.hi_sessions_per_week_delta}")
```

## 📊 Fragility Score System

The system calculates a **Fragility Score (F-Score)** from 0.0 to 1.0 that quantifies training plan risk:

### Score Formula

```
F-Score = base_fragility + Σ(weight_i × penalty_i)

Penalties calculated for:
1. Sleep deviation (weight: 0.15)
2. Stress multiplier (weight: 0.12)
3. Volume variance (weight: 0.10)
4. Intensity frequency (weight: 0.08)
5. Recovery quality (weight: 0.10)
```

### Interpretation Thresholds

- **0.0-0.4:** Low Risk (green) → 3 HI sessions/week
- **0.4-0.6:** Moderate Risk (yellow) → 2 HI sessions/week
- **0.6-0.8:** High Risk (orange) → 1 HI session/week
- **0.8-1.0:** Critical Risk (red) → Minimal intensity

### Fragility-Based Adjustments

The training plan generator automatically adjusts plans based on F-Score:
- **High-intensity session frequency** scales with fragility
- **Phase distribution** adapts to recovery capacity
- **Volume progression** respects current consistency
- **All decisions documented** in reasoning trace

## 🧪 Test Coverage

The project maintains comprehensive test coverage across all modules:

| Module | Tests | Coverage |
|--------|-------|----------|
| `test_validator.py` | 28 | Safety gates, validation logic, refusal scenarios |
| `test_fragility.py` | 20 | Penalty calculations, score thresholds, recommendations |
| `test_planner.py` | 23 | Plan generation, 80/20 distribution, phase logic |
| `test_sensitivity.py` | 14 | "What-if" scenarios, immutability, delta calculations |
| `test_trace.py` | 20 | Reasoning trace generation, markdown export |
| `test_schemas.py` | 1 | Schema validation |
| **Total** | **106** | **All core functionality** |

## 🔧 Configuration

The system uses JSON schemas for validation:

- [docs/schema_methodology.json](docs/schema_methodology.json) - Defines training methodology structure
- [docs/schema_user_profile.json](docs/schema_user_profile.json) - Defines athlete profile structure

Default methodology: [models/methodology_polarized.json](models/methodology_polarized.json)

## 📝 Key Implementation Files

### Core Modules

1. **[src/schemas.py](src/schemas.py)** (850 lines)
   - Complete Pydantic v2 models for UserProfile and MethodologyModelCard
   - Type-safe validation with descriptive error messages
   - Support for all training parameters (sleep, stress, volume, HRV, etc.)

2. **[src/validator.py](src/validator.py)** (450 lines)
   - Circuit breaker implementation with safety gates
   - Assumption checking and violation detection
   - Constructive refusal with actionable recommendations

3. **[src/fragility.py](src/fragility.py)** (350 lines)
   - Fragility score calculation engine
   - Five penalty calculators (sleep, stress, volume, intensity, recovery)
   - Risk interpretation and recommendations

4. **[src/planner.py](src/planner.py)** (422 lines)
   - Training plan generation with fragility-based adjustments
   - Phase determination (base/build/peak/taper)
   - 80/20 polarized intensity distribution
   - Session scheduling with user preferences

5. **[src/plan_schemas.py](src/plan_schemas.py)** (383 lines)
   - TrainingPlan, TrainingWeek, TrainingSession models
   - Intensity zone and session type enums
   - Plan analysis methods (volume, intensity distribution)

6. **[src/sensitivity.py](src/sensitivity.py)** (291 lines)
   - Interactive "what-if" scenario analysis
   - Immutable baseline comparison
   - Plan adjustment detection and comparison

7. **[src/trace.py](src/trace.py)** (enhanced)
   - Reasoning trace builder with fragility documentation
   - Plan decision recording
   - JSON and Markdown export formats

## 🤝 Contributing

This is a demonstration project focused on AI alignment principles in fitness applications. For methodology additions or improvements:

1. Review [docs/methodology_guide.md](docs/methodology_guide.md)
2. Create methodology JSON following [docs/schema_methodology.json](docs/schema_methodology.json)
3. Add corresponding test cases
4. Submit with reasoning trace examples

## 📚 Documentation

- **Product Requirements:** See [docs/prd_v3.txt](docs/prd_v3.txt) for complete product requirements
- **Methodology Guide:** See [docs/methodology_guide.md](docs/methodology_guide.md) for creating new methodologies
- **Schema References:**
  - [docs/schema_methodology.json](docs/schema_methodology.json) - Methodology structure
  - [docs/schema_user_profile.json](docs/schema_user_profile.json) - User profile structure

## ⚠️ Important Notes

- This tool is **NOT** a replacement for professional coaching
- It is a **transparency layer** for making training assumptions explicit
- Success metric: User understands the "why" behind recommendations
- The system **should** refuse unsafe requests - this is a feature, not a bug
- Fragility scores quantify risk but don't eliminate it - human judgment is essential

## 🎯 Development Status

### ✅ Phase 1: Core Validation (Complete)
- [x] Project structure setup
- [x] Schema definitions (Methodology + UserProfile)
- [x] Reference methodology (Polarized 80/20)
- [x] Pydantic validation models
- [x] Circuit breaker implementation
- [x] Reasoning trace generation
- [x] CLI interface (validate, methodology)
- [x] Comprehensive test suite (49 tests)

### ✅ Phase 2: Plan Generation & Risk Analysis (Complete)
- [x] Fragility score calculation (20 tests)
- [x] Training plan generation logic (23 tests)
- [x] Sensitivity analysis (14 tests)
- [x] Enhanced reasoning traces with fragility documentation
- [x] Test fixtures for all fragility levels
- [x] 80/20 polarized intensity distribution
- [x] Fragility-based HI frequency adjustments

### 🚧 Phase 3: CLI Enhancement (Optional)
- [ ] `generate-plan` command - Full plan generation workflow
- [ ] `what-if` command - Interactive sensitivity analysis
- [ ] `analyze-fragility` command - Standalone fragility analysis
- [ ] Rich display functions for fragility gauge and plan summaries

### 🔮 Phase 4: Future Enhancements
- [ ] Multi-methodology support
- [ ] Historical tracking
- [ ] Web interface (FastAPI)
- [ ] Data export and visualization
- [ ] Plan comparison tools

## 📄 License

[Your chosen license]

## 🙏 Acknowledgments

Built with principles from:
- Anthropic's Constitutional AI research
- Sports science literature on polarized training (Seiler, Stöggl, et al.)
- Human-centered AI design principles
- Pydantic v2 for robust data validation

---

**Current Status:** Phase 1 & 2 complete with 105/106 tests passing. Ready for Phase 3 CLI enhancements or production use via programmatic API.
