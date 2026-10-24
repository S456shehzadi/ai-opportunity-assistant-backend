from typing import Any


class PromptTemplate:
    """Template for system and user prompts across specialized models."""

    def __init__(self, template: str, required_variables: list[str] | None = None) -> None:
        self.template = template
        self.required_variables = set(required_variables or [])

    def format(self, **kwargs: Any) -> str:
        missing = self.required_variables - kwargs.keys()
        if missing:
            raise ValueError(f"Missing required prompt template variables: {missing}")
        return self.template.format(**kwargs)
