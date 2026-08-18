import os
import re
from typing import Any, Optional, Tuple

_PROMPTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "prompts")

# Optional first line in a prompt file to set its temperature, e.g. "# temperature: 0.3"
_TEMPERATURE_LINE_RE = re.compile(r"^#\s*temperature\s*:\s*([0-9]*\.?[0-9]+)\s*$", re.IGNORECASE)


def _read_template(name: str) -> str:
    path = os.path.join(_PROMPTS_DIR, f"{name}.txt")
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError as exc:
        raise FileNotFoundError(f"Prompt template not found: {path}") from exc


def _split_temperature_directive(template: str) -> Tuple[str, Optional[float]]:
    """Strip a leading '# temperature: <value>' directive line, if present, and return it separately."""
    first_line, _, rest = template.partition("\n")
    match = _TEMPERATURE_LINE_RE.match(first_line.strip())
    if match:
        return rest, float(match.group(1))
    return template, None


def load_prompt(name: str, **kwargs: Any) -> str:
    """Load prompts/<name>.txt and fill in its {placeholder} fields (ignores any temperature directive)."""
    template, _ = _split_temperature_directive(_read_template(name))
    return template.format(**kwargs)


def load_prompt_with_temperature(name: str, **kwargs: Any) -> Tuple[str, float]:
    """Like load_prompt, but also resolves the temperature to use for this prompt.

    Precedence: a '# temperature: <value>' directive on the first line of prompts/<name>.txt,
    else the LLM_TEMPERATURE env var, else 0.2.
    """
    template, file_temperature = _split_temperature_directive(_read_template(name))
    prompt = template.format(**kwargs)
    if file_temperature is not None:
        return prompt, file_temperature
    env_temp = os.getenv("LLM_TEMPERATURE")
    return prompt, (float(env_temp) if env_temp else 0.2)
