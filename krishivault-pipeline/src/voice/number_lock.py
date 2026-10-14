"""
The number lock
===============
Every taka figure, quantity and date a farmer hears comes from the decision engine, written into a
Bangla template. Gemini may reword the template so it sounds natural, but it must not change, add or
drop a single number. This module checks that and falls back to the template if anything differs.

Ported from Mati Kohon's dual_gate_validator.ts (reference/mati_kohon_code/), with two changes:
- numbers are compared both ways (nothing added, nothing dropped), and
- numbers written as words ("আশি হাজার") are read as numbers too, so they cannot slip past.
"""

from dataclasses import dataclass, field, asdict
from typing import Callable, Optional

from loguru import logger

from src.voice.bangla_numbers import extract_numbers, nfc

# Promises and asks no farmer message may contain. Loan words (ঋণ, সুদ) are allowed only when the
# engine's own template already uses them (the loan flow); the AI may not bring them in.
FORBIDDEN_TERMS = ["টাকা দিন", "গ্যারান্টি", "নিশ্চিত লাভ", "নিশ্চিত", "অবশ্যই বাড়বে"]
ONLY_IF_IN_TEMPLATE = ["ঋণ", "সুদ", "লোন"]


@dataclass
class NumberCheck:
    passed: bool
    template_numbers: list = field(default_factory=list)
    reworded_numbers: list = field(default_factory=list)
    added: list = field(default_factory=list)      # in the reworded text, not in the template
    missing: list = field(default_factory=list)    # in the template, dropped from the reworded text
    forbidden: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def check_numbers(template: str, reworded: str) -> NumberCheck:
    """Compare the numbers in an AI rewording with the template's numbers."""
    t_nums = extract_numbers(template)
    r_nums = extract_numbers(reworded)
    t_set, r_set = set(t_nums), set(r_nums)
    added = [n for n in dict.fromkeys(r_nums) if n not in t_set]
    missing = [n for n in dict.fromkeys(t_nums) if n not in r_set]
    text, base = nfc(reworded), nfc(template)
    forbidden = [w for w in FORBIDDEN_TERMS if nfc(w) in text and nfc(w) not in base]
    forbidden += [w for w in ONLY_IF_IN_TEMPLATE if nfc(w) in text and nfc(w) not in base]
    return NumberCheck(
        passed=not added and not missing and not forbidden,
        template_numbers=t_nums,
        reworded_numbers=r_nums,
        added=added,
        missing=missing,
        forbidden=forbidden,
    )


def narrate(template: str, rewrite: Optional[Callable[[str], Optional[str]]]) -> dict:
    """
    The text the farmer hears, and how it was decided:
      status "template"          no AI rewording available
      status "gemini_checked"    Gemini's wording kept every number
      status "gemini_rejected"   Gemini changed a number (or used a forbidden word): template used
      status "gemini_failed"     Gemini errored or gave nothing: template used
    """
    if rewrite is None:
        return {"text": template, "status": "template", "check": None}
    try:
        reworded = (rewrite(template) or "").strip()
    except Exception as exc:  # any failure falls back to the template
        logger.warning(f"Rewording failed, using the template: {exc}")
        reworded = ""
    if not reworded:
        return {"text": template, "status": "gemini_failed", "check": None}
    check = check_numbers(template, reworded)
    if check.passed:
        return {"text": reworded, "status": "gemini_checked", "check": check.to_dict()}
    logger.info(f"Number lock rejected the rewording: added={check.added} missing={check.missing} forbidden={check.forbidden}")
    return {"text": template, "status": "gemini_rejected", "check": check.to_dict(), "rejected_text": reworded}
