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
- **Multi-Methodology Support:** Polarized 80/20, Pyramidal 77/15/8, and Threshold 70/20/10 methodologies
- **7-Zone Physiological Model:** Sport-specific intensity zones (cycling FTP, running pace, swimming CSS)
- **Recovery Spacing:** Enforces minimum 2-day gap between high-intensity sessions
- **Balanced Sport Distribution:** Minimum frequency per sport (2 runs, 2 bikes, 1 swim per week)
- **Sensitivity Analysis:** Interactive "what-if" scenario exploration
- **Enhanced Reasoning Traces:** Documents fragility calculations and plan generation decisions
- **120 passing tests** covering fragility, planning, and sensitivity analysis

### Phase 3: CLI Enhancement (✅ Complete)
- **Complete CLI Interface:** Full workflow commands (validate, generate-plan, what-if, analyze-fragility)
- **Rich Display Functions:** Color-coded fragility gauges and plan summaries
- **Interactive "What-If" Analysis:** Explore scenario impacts on fragility and plans

### Phase 4: Web Interface & API (✅ Complete - MVP)
- **FastAPI Backend:** RESTful API with 6 endpoints (validation, plans, fragility, sensitivity, methodologies, strava)
- **React Frontend:** Modern TypeScript SPA with 4 pages (Home, Profile, Validation, Plan)
- **Database Layer:** SQLAlchemy with Alembic migrations for future activity tracking
- **Strava Integration Prep:** OAuth endpoints and activity tracking schemas (Phase 5)
- **Type-Safe API:** Pydantic request/response models with full validation
- **Mobile-Responsive UI:** Tailwind CSS v3 with color-coded zones and phases

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
│   ├── methodology_polarized.json      # Polarized 80/20 methodology
│   ├── methodology_pyramidal_v1.json   # Pyramidal 77/15/8 methodology
│   └── methodology_threshold_70_20_10_v1.json  # Threshold 70/20/10 methodology
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
│   ├── database.py                     # SQLAlchemy models for activity tracking
│   ├── overtraining.py                 # Overtraining detection (Phase 5 prep)
│   ├── cli.py                          # CLI interface
│   └── api/                            # FastAPI web application
│       ├── main.py                     # FastAPI app entry point
│       ├── routes/                     # API endpoint modules
│       │   ├── validation.py
│       │   ├── plans.py
│       │   ├── fragility.py
│       │   ├── sensitivity.py
│       │   ├── methodologies.py
│       │   └── strava.py               # Strava integration (Phase 5)
│       └── models/                     # API request/response models
│           ├── requests.py
│           └── responses.py
├── alembic/                            # Database migrations
│   ├── versions/                       # Migration scripts
│   └── env.py
├── frontend/                           # React TypeScript web UI
│   ├── src/
│   │   ├── pages/                      # Route pages
│   │   │   ├── HomePage.tsx
│   │   │   ├── ProfilePage.tsx
│   │   │   ├── ValidationPage.tsx
│   │   │   └── PlanPage.tsx
│   │   ├── components/                 # Reusable components
│   │   │   └── MethodologyCard.tsx
│   │   ├── api/                        # API client modules
│   │   │   ├── client.ts
│   │   │   ├── methodologies.ts
│   │   │   ├── validation.ts
│   │   │   └── plans.ts
│   │   ├── hooks/                      # React Query hooks
│   │   │   ├── useMethodologies.ts
│   │   │   ├── useValidation.ts
│   │   │   └── usePlanGeneration.ts
│   │   ├── store/                      # State management
│   │   │   └── profileStore.ts
│   │   ├── types/                      # TypeScript types
│   │   │   ├── index.ts
│   │   │   └── profile.ts
│   │   └── utils/                      # Utilities
│   │       ├── validationSchemas.ts
│   │       └── profileHelpers.ts
│   ├── package.json
│   └── vite.config.ts
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

**Backend:**
- Python 3.10 or higher
- pip

**Frontend (optional, for web UI):**
- Node.js 18+ (recommended: 24.13.0)
- npm

### Installation

**Backend Setup:**

```bash
# Clone the repository
git clone <repository-url>
cd training-planner

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Initialize database (optional, for web UI)
alembic upgrade head
```

**Frontend Setup (optional, for web UI):**

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

**Running the Web Application:**

```bash
# Terminal 1: Start backend API
uvicorn src.api.main:app --reload --port 8000

# Terminal 2: Start frontend dev server (from frontend/ directory)
cd frontend && npm run dev
```

Then visit `http://localhost:5173` in your browser.

### Running Tests

```bash
# Run all tests (120 total)
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

Expected result: **120 passed**

## 💻 Usage Examples

### Web UI (Recommended for New Users)

The easiest way to use the training planner is through the web interface:

1. Start the backend: `uvicorn src.api.main:app --reload --port 8000`
2. Start the frontend: `cd frontend && npm run dev`
3. Visit `http://localhost:5173`
4. Select a methodology → Fill profile → View validation → Generate plan

### CLI Usage (Advanced Users)

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

### 2. Analyze Fragility Score

```bash
# Detailed fragility breakdown
python3 -m src.cli analyze-fragility --profile tests/fixtures/test_user_valid.json
```

Shows:
- F-Score with color-coded risk level
- Breakdown by penalty factor
- Actionable recommendations

### 3. Generate Training Plan

```bash
# Generate complete training plan
python3 -m src.cli generate-plan --profile tests/fixtures/test_user_valid.json
```

Creates:
- Validation check
- Fragility score calculation
- 12-week training plan with phases
- 80/20 intensity distribution
- Saves plan JSON and reasoning trace

### 4. Run "What-If" Scenarios

```bash
# Interactive sensitivity analysis
python3 -m src.cli what-if --profile tests/fixtures/test_user_moderate_fragility.json
```

Explore:
- How sleep changes affect fragility
- Impact of stress level modifications
- Volume adjustments
- Plan changes based on assumption changes

### 5. View Methodology Details

```bash
# Show methodology information
python3 -m src.cli methodology --show models/methodology_polarized.json

# List all available methodologies
python3 -m src.cli methodology --list
```

### 6. Programmatic API Usage

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

### 7. Sensitivity Analysis (Programmatic)

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
| `test_planner.py` | 37 | Plan generation, multi-methodology, zone model, recovery spacing |
| `test_schemas.py` | 20 | Pydantic schema validation |
| `test_fragility.py` | 20 | Penalty calculations, score thresholds, recommendations |
| `test_trace.py` | 17 | Reasoning trace generation, markdown export |
| `test_sensitivity.py` | 14 | "What-if" scenarios, immutability, delta calculations |
| `test_validator.py` | 12 | Safety gates, validation logic, refusal scenarios |
| **Total** | **120** | **All core functionality** |

## 🔧 Configuration

The system uses JSON schemas for validation:

- [docs/schema_methodology.json](docs/schema_methodology.json) - Defines training methodology structure
- [docs/schema_user_profile.json](docs/schema_user_profile.json) - Defines athlete profile structure

### Available Methodologies

| Methodology | Intensity Distribution | Best For |
|-------------|----------------------|----------|
| **Polarized 80/20** | 80% low, 20% high | Athletes with limited time, maximizing aerobic gains |
| **Pyramidal 77/15/8** | 77% low, 15% threshold, 8% high | Balanced approach, good stress tolerance |
| **Threshold 70/20/10** | 70% low, 20% threshold, 10% high | Lactate threshold improvement focus |

### Intensity Zones

The system uses a 7-zone physiological model with sport-specific display:

| Zone | Physiological Target | Cycling (FTP) | Running | Swimming (CSS) |
|------|---------------------|---------------|---------|----------------|
| Active Recovery | Blood flow promotion | Z1 <55% | Very easy | Easy drill work |
| Endurance | Aerobic base | Z2 56-75% | Conversational | CSS -10sec/100m |
| Tempo | Moderate sustained | Z3 76-90% | Comfortably hard | CSS -5sec/100m |
| Threshold | Lactate threshold | Z4 91-105% | 60min sustainable | CSS pace |
| VO2max | Maximal aerobic | Z5 106-120% | 3-8min race effort | CSS +5sec/100m |
| Anaerobic | Above threshold | Z6 121-150% | 1-2min max | Near max 100m |
| Sprint | Neuromuscular | Z7 max power | All-out strides | All-out 25m/50m |

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

4. **[src/planner.py](src/planner.py)** (1129 lines)
   - Training plan generation with fragility-based adjustments
   - Phase determination (base/build/peak/taper)
   - Multi-methodology intensity distribution (Polarized, Pyramidal, Threshold)
   - Recovery spacing between high-intensity sessions
   - Balanced sport distribution (minimum per sport)
   - Week-over-week workout progression

5. **[src/plan_schemas.py](src/plan_schemas.py)** (488 lines)
   - TrainingPlan, TrainingWeek, TrainingSession models
   - 7-zone physiological intensity model
   - Sport-specific zone display mappings (cycling FTP, running pace, swimming CSS)
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

### ✅ Phase 3: CLI Enhancement (Complete)
- [x] `generate-plan` command - Full plan generation workflow
- [x] `what-if` command - Interactive sensitivity analysis
- [x] `analyze-fragility` command - Standalone fragility analysis
- [x] Rich display functions for fragility gauge and plan summaries

### ✅ Phase 4: Web Interface & API (Complete - MVP)
- [x] FastAPI backend with 6 API endpoints
- [x] React TypeScript frontend (4 pages)
- [x] SQLAlchemy database layer with Alembic
- [x] Pydantic request/response models
- [x] Mobile-responsive UI with Tailwind CSS v3
- [x] Type-safe API client with TanStack Query
- [x] Form validation with React Hook Form + Zod
- [x] State management with Zustand + localStorage
- [x] Strava integration preparation (OAuth stubs)

### ✅ Phase 4.5: Plan Quality Improvements (Complete)
- [x] 7-zone physiological intensity model (active_recovery, endurance, tempo, threshold, vo2max, anaerobic, sprint)
- [x] Sport-specific zone display (cycling FTP zones, running pace zones, swimming CSS zones)
- [x] Recovery spacing enforcement (minimum 2-day gap between high-intensity sessions)
- [x] Balanced sport distribution (minimum 2 runs, 2 bikes, 1 swim per week)
- [x] Week-over-week workout progression for variety within phases
- [x] Multi-methodology support: Polarized 80/20, Pyramidal 77/15/8, Threshold 70/20/10

### 🔮 Phase 5: Future Enhancements
- [ ] Strava OAuth implementation
- [ ] Activity sync and adherence tracking
- [ ] Overtraining detection from activity data
- [ ] Historical plan tracking
- [ ] Export to PDF/ICS
- [ ] Plan comparison tools
- [ ] Deployment to production (Vercel + Railway)

## 📄 License

[Your chosen license]

## 🙏 Acknowledgments

Built with principles from:
- Anthropic's Constitutional AI research
- Sports science literature on polarized training (Seiler, Stöggl, et al.)
- Human-centered AI design principles
- Pydantic v2 for robust data validation

## 🌐 API Documentation

For detailed API endpoint documentation, see [API_README.md](API_README.md).

**Available Endpoints:**
- `POST /api/validate` - Validate user profile against methodology
- `POST /api/plans` - Generate training plan
- `POST /api/fragility` - Calculate fragility score
- `POST /api/sensitivity` - Run "what-if" analysis
- `GET /api/methodologies` - List available methodologies
- `POST /api/strava/*` - Strava integration (Phase 5)

---

**Current Status:** Phase 1-4.5 complete with 120 tests passing. Multi-methodology support (Polarized, Pyramidal, Threshold), 7-zone physiological model with sport-specific display, and intelligent scheduling (recovery spacing, sport distribution). CLI, API, and web UI ready for use.
