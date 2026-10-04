# evals

> Evaluates retrieval-augmented generation (RAG) performance for code documentation by testing if LLMs can correctly identify source files based on natural language questions.

The evals module contains test fixtures (three sample repositories: grainpipe, relayboard, taskvane) with known file structures and predefined questions. It runs evaluations to measure how well documentation systems can retrieve the correct source files when given questions about functionality. The module compares results against a baseline to measure performance improvements.

## Files

### `evals/run_eval.py`

Main evaluation runner that processes questions, checks file retrieval accuracy, and generates performance reports.

- `run_eval` (function) - Executes the evaluation by matching questions to expected files and calculating accuracy metrics
- `EvalReport` (class) - Stores and calculates evaluation results including overall and per-repository scores

### `evals/baseline.json`

Stores reference performance scores (1.0 perfect scores) for comparison against new evaluation runs.

### `evals/fixtures/questions.json`

Contains the evaluation questions with expected file answers for each repository.

### `evals/fixtures/modules/grainpipe.json`

Defines the modular structure of grainpipe repository for documentation generation.

### `evals/fixtures/modules/relayboard.json`

Defines the modular structure of relayboard repository for documentation generation.

### `evals/fixtures/modules/taskvane.json`

Defines the modular structure of taskvane repository for documentation generation.

## Key Concepts

- **Retrieval Evaluation**: Measures how accurately a system can retrieve the correct source files when given natural language questions about code functionality
- **Fixture Repositories**: Three sample codebases (grainpipe, relayboard, taskvane) that serve as test cases with known structures and expected answers
- **Baseline Comparison**: Performance is measured against predefined perfect scores to evaluate improvement over previous versions

## Internal Relationships

- `evals/run_eval.py` → `evals/fixtures/questions.json`: Uses questions.json as input data for evaluation tests
- `evals/run_eval.py` → `evals/baseline.json`: Compares evaluation results against baseline scores for performance measurement
- `evals/fixtures/modules/*.json` → `evals/fixtures/repos/`: Describes the modular structure of the corresponding repository fixtures
