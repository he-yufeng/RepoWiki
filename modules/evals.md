# evals

> Evaluates code documentation retrieval accuracy using fixture repositories and predefined questions.

The evals module contains test fixtures and evaluation logic to measure how well an AI system can retrieve the correct source files when asked questions about code functionality. It includes three sample repositories (grainpipe, relayboard, taskvane) with complete implementations, module documentation files describing their architecture, and question sets with expected answers.

## Files

### `evals/baseline.json`

Stores perfect accuracy scores (1.0) for all repositories as a benchmark

- `overall` (field) - Overall accuracy score across all repositories
- `repos` (field) - Individual repository accuracy scores
- `boosted` (field) - Enhanced accuracy scores using improved retrieval methods

### `evals/fixtures/questions.json`

Contains evaluation questions with expected file answers for each repository

- `repo` (field) - Which repository the question targets
- `question` (field) - The question text asking about code functionality
- `expect_files` (field) - Expected correct source file paths for the answer
- `tier` (field) - Question difficulty level (paraphrase questions use different wording)

### `evals/run_eval.py`

Main evaluation runner that tests retrieval accuracy against fixture questions

- `run_eval` (function) - Executes the evaluation and returns accuracy results
- `EvalReport` (class) - Stores and calculates evaluation metrics
- `CaseResult` (class) - Represents the result of a single question evaluation
- `print_report` (function) - Displays evaluation results comparing against baseline

## Key Concepts

- **Fixture Repositories**: Three complete, working codebases (grainpipe ETL tool, relayboard kanban API, taskvane CLI task manager) that serve as test subjects for the evaluation
- **Retrieval Accuracy**: The primary metric measuring how often the system correctly identifies which source file contains the answer to a given question
- **Question Tiers**: Questions are categorized by difficulty - direct questions use terminology from the code, while paraphrase questions rephrase concepts using different vocabulary
- **Module Documentation**: JSON files that describe each repository's architecture, mapping functional areas to their implementing source files

## Internal Relationships

- `evals/run_eval.py` → `evals/fixtures/questions.json`: run_eval reads questions.json to get the evaluation test cases
- `evals/run_eval.py` → `evals/baseline.json`: print_report compares evaluation results against baseline.json scores
- `evals/fixtures/modules/*.json` → `evals/fixtures/repos/*`: Module documentation files describe the structure and purpose of the fixture repositories
