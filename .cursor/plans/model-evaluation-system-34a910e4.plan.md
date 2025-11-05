<!-- 34a910e4-120c-438f-bbf3-9569468127f5 90ba1d54-3e0f-4a3b-b95e-47452668ee91 -->
# Model Evaluation System Implementation Plan

## Overview

Build a complete evaluation framework for the MI health coaching chatbot that includes test case generation, automated metrics, and evaluation reports.

## Components to Create

### 1. Test Case Generation (`evaluation/test_cases.py`)

- Create synthetic test scenarios covering different MI stages:
  - Engaging stage: Initial user greetings, information gathering
  - Focusing stage: Goal identification, priority setting
  - Evoking stage: Change talk elicitation, motivation exploration
  - Planning stage: SMART goal creation, action planning
  - Closing stage: Session wrap-up, follow-up scheduling
- Include edge cases: resistance, low motivation, unclear goals
- Format: List of test conversations with expected behaviors

### 2. Evaluation Metrics Module (`evaluation/metrics.py`)

- General metrics:
  - Response length (should be ≤80 words per prompt)
  - Response time/latency
  - Fluency checks (basic grammar, coherence)
- MI-specific metrics:
  - OARS detection (Open questions, Affirmations, Reflections, Summaries)
  - Question type classification (open-ended vs closed)
  - Permission-seeking detection ("Would you like...", "Can I...")
  - Empathy indicators
  - MI stage classification (which stage the response belongs to)
  - Avoidance of unwanted behaviors (lecturing, diagnosing, persuading)

### 3. Evaluation Runner (`evaluation/evaluator.py`)

- Main evaluation script that:
  - Loads test cases
  - Runs model on each test case
  - Computes all metrics
  - Generates evaluation report
- Supports batch evaluation
- Handles errors gracefully

### 4. Database Conversation Extractor (`evaluation/extract_conversations.py`)

- Optional utility to extract real conversations from database
- Export conversations for manual review or evaluation
- Filter by date, user, session

### 5. Evaluation Report Generator (`evaluation/report_generator.py`)

- Generate HTML/JSON reports with:
  - Overall scores per metric
  - Per-test-case results
  - Visualizations (charts, graphs)
  - Recommendations for improvement

### 6. Configuration File (`evaluation/config.py`)

- Evaluation parameters
- Test case paths
- Metric thresholds
- Report output settings

## File Structure

```
evaluation/
├── __init__.py
├── config.py
├── test_cases.py          # Synthetic test scenarios
├── metrics.py             # Metric calculations
├── evaluator.py           # Main evaluation runner
├── extract_conversations.py  # DB conversation extractor
├── report_generator.py    # Report creation
└── results/               # Output directory
    └── .gitkeep
```

## Implementation Details

### Test Cases Format

Each test case will be a dictionary with:

- `scenario`: Description of the scenario
- `stage`: MI stage (engaging, focusing, evoking, planning, closing)
- `conversation`: List of message exchanges
- `expected_behaviors`: List of expected MI behaviors
- `context`: Additional context information

### Metrics Implementation

- Use regex patterns for OARS detection
- Use keyword matching for permission-seeking
- Simple heuristics for stage classification
- Length checks for response constraints

### Evaluation Output

- JSON report with detailed metrics
- CSV summary for easy analysis
- HTML report with visualizations (optional)
- Console summary during evaluation

## Dependencies

- Add to requirements.txt: `rouge-score`, `nltk` (optional for advanced metrics)

## Testing

- Unit tests for individual metrics
- Integration test for full evaluation pipeline

### To-dos

- [ ] Create evaluation/ directory structure with __init__.py and results/ subdirectory
- [ ] Implement test_cases.py with synthetic MI scenarios covering all 5 stages plus edge cases
- [ ] Create metrics.py with general metrics (length, latency) and MI-specific metrics (OARS detection, stage classification)
- [ ] Build evaluator.py main script that runs test cases, computes metrics, and generates reports
- [ ] Implement report_generator.py to create JSON/CSV/HTML evaluation reports
- [ ] Create extract_conversations.py utility to extract real conversations from database for evaluation
- [ ] Add evaluation dependencies (rouge-score, nltk) to requirements.txt
- [ ] Add evaluation/config.py with configuration parameters and thresholds