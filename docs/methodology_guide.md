# Methodology Model Card Creation Guide

This guide explains how to create new training methodology model cards for the Human-in-the-Loop Training Planner.

## Philosophy

A methodology model card is **not** a training plan. It is a **documented set of assumptions and safety rules** that enables the system to:

1. Determine if a methodology is safe for a given athlete
2. Explain WHY it made that determination
3. Provide constructive alternatives when refusing

## Core Components

### 1. Identity and Philosophy

**Purpose:** Establish what the methodology is and its core logic.

```json
{
  "id": "your_methodology_v1",
  "name": "Human Readable Name",
  "version": "1.0.0",
  "philosophy": {
    "one_line_description": "Brief elevator pitch",
    "core_logic": "Detailed physiological rationale",
    "metabolic_focus": ["systems", "being", "targeted"]
  }
}
```

**Best Practices:**
- Use snake_case for `id`
- Keep one_line_description under 100 characters
- Core logic should explain the "why" in plain language
- Metabolic focus uses predefined enum values

### 2. Assumptions

**Purpose:** Make explicit what must be true for this methodology to be safe and effective.

```json
{
  "assumptions": [
    {
      "key": "sleep_hours",
      "expectation": "Consistent sleep ≥7.0 hours per night",
      "reasoning_justification": "Why this matters physiologically",
      "criticality": "high",
      "validation_rule": "user.sleep_hours >= 7.0"
    }
  ]
}
```

**Best Practices:**
- Each assumption must map to a UserProfile field (the `key`)
- Expectation should be human-readable and specific
- Reasoning explains the underlying physiology/biomechanics
- Criticality determines refusal severity
- Validation rule is pseudo-code for implementation

**Common Assumptions:**

| Key | Typical Expectation | Criticality |
|-----|---------------------|-------------|
| sleep_hours | ≥7.0 hours | high |
| injury_status | false | high |
| volume_consistency_weeks | ≥4 weeks | high |
| stress_level | low or moderate | medium |
| recent_illness | false | medium |
| weekly_volume_hours | 6-20 hours | medium |

### 3. Safety Gates

**Purpose:** Define the circuit breakers that trigger refusals.

```json
{
  "safety_gates": {
    "exclusion_criteria": [
      {
        "condition": "injury_status",
        "threshold": "true",
        "severity": "blocking",
        "validation_logic": "IF user.injury_status == true THEN REFUSE",
        "bridge_action": "Specific recommendation for path forward"
      }
    ],
    "refusal_bridge_template": "Template with {placeholders}"
  }
}
```

**Best Practices:**
- **Blocking** severity = hard refusal, no plan generated
- **Warning** severity = plan generated with caveats
- Bridge action must be actionable and specific
- Avoid vague advice like "rest more" - be prescriptive

**Template Variables Available:**
- `{condition}` - The field that triggered the gate
- `{threshold}` - The threshold value
- `{assumption_expectation}` - The violated assumption text
- `{reasoning_justification}` - The reasoning for the assumption
- `{bridge_action}` - The recommended action

### 4. Risk Profile

**Purpose:** Characterize the methodology's inherent fragility.

```json
{
  "risk_profile": {
    "fragility_score": 0.4,
    "sensitivity_factors": [
      "sleep_consistency",
      "stress_load",
      "recovery_between_sessions"
    ],
    "fragility_calculation_weights": {
      "sleep_deviation": 0.15,
      "stress_multiplier": 0.12,
      "volume_variance": 0.10
    }
  }
}
```

**Fragility Score Guidelines:**
- **0.0-0.3:** Robust (tolerates missed sessions, variation)
- **0.4-0.6:** Moderate (requires consistency, some flexibility)
- **0.7-1.0:** Fragile (very sensitive to deviations)

**Best Practices:**
- Base score reflects methodology under ideal conditions
- Sensitivity factors list variables that increase fragility
- Weights are used for user-specific score calculation
- Total weights should sum to ≤1.0

### 5. Failure Modes

**Purpose:** Document how plans typically break down and early warnings.

```json
{
  "failure_modes": [
    {
      "condition": "Specific scenario that causes failure",
      "early_warning_signals": [
        "Observable indicator 1",
        "Observable indicator 2"
      ],
      "mitigation_strategy": "Specific intervention to prevent failure"
    }
  ]
}
```

**Best Practices:**
- Focus on common, preventable failures
- Early warnings should be measurable (HRV, HR, subjective markers)
- Mitigation should be prescriptive and time-bound
- Include both physical and psychological indicators

### 6. References (Optional)

**Purpose:** Ground methodology in evidence.

```json
{
  "references": [
    {
      "citation": "Author, A. (Year). Title. Journal, volume(issue), pages.",
      "url": "https://doi.org/...",
      "relevance": "How this source supports the methodology"
    }
  ]
}
```

## Complete Example Workflow

### Step 1: Define Philosophy
```
What is the core idea?
→ "Threshold-focused training emphasizes work at lactate threshold"

What's the physiological basis?
→ "Improving lactate clearance and threshold power/pace directly 
   impacts race performance in events lasting 1-4 hours"
```

### Step 2: List Assumptions
```
What must be true?
→ Base fitness established (volume_consistency_weeks ≥ 8)
→ No injury (injury_status == false)  
→ Adequate recovery (sleep_hours ≥ 7.5)
→ High training age (years_training ≥ 2)
```

### Step 3: Define Safety Gates
```
What absolutely cannot be violated?
→ BLOCKING: injury_status == true
→ BLOCKING: volume_consistency_weeks < 8
→ WARNING: sleep_hours < 7.5
```

### Step 4: Characterize Risk
```
How fragile is this approach?
→ Fragility: 0.6 (requires consistency, narrow intensity range)
→ Sensitive to: session frequency, intensity accuracy, fatigue
```

### Step 5: Document Failures
```
How does this typically break?
→ Overtraining from excessive threshold work
→ Injury from inadequate recovery
→ Staleness from monotony
```

## Validation Checklist

Before submitting a new methodology:

- [ ] All required fields present (id, name, version, philosophy, assumptions, safety_gates, risk_profile)
- [ ] At least 3 assumptions defined
- [ ] All assumption keys map to UserProfile fields
- [ ] At least 1 blocking safety gate defined
- [ ] Fragility score between 0.0 and 1.0
- [ ] Refusal bridge template includes actionable guidance
- [ ] At least 2 failure modes documented
- [ ] Validation rules are implementable as code
- [ ] JSON validates against schema

## Common Pitfalls

### ❌ Vague Assumptions
```json
"expectation": "Good sleep"  // Too vague
```

### ✅ Specific Assumptions
```json
"expectation": "Consistent sleep ≥7.0 hours per night (7-day average)"
```

### ❌ Unhelpful Bridge Actions
```json
"bridge_action": "Rest more and come back later"  // Not actionable
```

### ✅ Prescriptive Bridge Actions
```json
"bridge_action": "Complete 8 weeks of base building at current volume 
before introducing threshold work. Focus exclusively on Zone 1-2. 
Return when volume_consistency_weeks ≥ 8."
```

### ❌ Generic Reasoning
```json
"reasoning_justification": "Recovery is important"  // Superficial
```

### ✅ Specific Reasoning
```json
"reasoning_justification": "Threshold training creates significant 
metabolic acidosis and depletes glycogen. Without 8+ weeks of base, 
athletes lack the aerobic enzymes and capillary density to clear 
lactate effectively, leading to incomplete recovery and injury risk."
```

## Testing Your Methodology

Create test user profiles that:

1. **Pass all gates** - Should generate plan with expected F-Score
2. **Trigger each safety gate individually** - Should refuse with correct bridge
3. **Hit edge cases** - Boundary conditions for thresholds
4. **Compound violations** - Multiple gates triggered simultaneously

Example test structure:
```json
{
  "test_name": "threshold_happy_path",
  "user_profile": { /* satisfies all assumptions */ },
  "expected_result": "plan_generated",
  "expected_fragility_range": [0.5, 0.7]
}
```

## Methodology Comparison Matrix

Use this to position your methodology:

| Dimension | Low | Medium | High |
|-----------|-----|--------|------|
| **Volume Requirement** | 6-10 hrs/wk | 10-15 hrs/wk | 15-25 hrs/wk |
| **Intensity Focus** | 5-10% | 10-20% | 20-30% |
| **Base Requirement** | 4 weeks | 8 weeks | 12+ weeks |
| **Fragility** | 0.2-0.4 | 0.4-0.6 | 0.6-0.9 |
| **Training Age** | 1+ years | 2+ years | 3+ years |

## Resources

- **UserProfile Schema:** `docs/user_profile.schema.json`
- **Methodology Schema:** `docs/methodology_model_card.schema.json`
- **Reference Implementation:** `models/polarized_80_20_v1.json`
- **Test Fixtures:** `tests/fixtures/`

## Questions?

When in doubt:
1. **Be more specific, not less** - Precision helps athletes
2. **Default to refusal** - Safety over optimization
3. **Make assumptions explicit** - Hidden assumptions = broken trust
4. **Provide alternatives** - Refusal without path forward = abandonment