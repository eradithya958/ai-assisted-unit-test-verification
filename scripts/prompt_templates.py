"""Fixed Prompt Templates for AI Unit Test Generation.

This prompt is fixed BEFORE running mutation testing to ensure scientific integrity
and prevent mutation leak / data leakage into the prompt.
"""

TEST_GENERATION_SYSTEM_PROMPT = """You are an automated Python test generation assistant.
Your goal is to write high-quality, comprehensive pytest unit tests for the provided Python module based on its implementation and docstring specifications.

Rules:
1. Use `pytest` syntax and conventions.
2. Group tests logically using classes or functions.
3. Test nominal (happy path) cases with realistic inputs.
4. Test boundary values and edge cases specified in docstrings.
5. Test error paths, invalid inputs, and verify expected exceptions using `pytest.raises`.
6. Use `pytest.mark.parametrize` where appropriate for input variations.
7. Return ONLY valid, executable Python code enclosed in ```python codeblocks. Do not include markdown preamble.
"""

def build_test_generation_prompt(module_name: str, source_code: str, spec_text: str = "") -> str:
    """Construct the complete user prompt for a target module."""
    prompt = f"""Generate a complete pytest test suite for the following Python module: `{module_name}`.

### Module Source Code & Docstring Specifications:
```python
{source_code}
```

### Additional Behavioral Specification Notes:
{spec_text if spec_text else "Adhere strictly to the docstrings, types, and constraints defined in the source code."}

Please output the full `test_{module_name}.py` file with all imports and tests.
"""
    return prompt
