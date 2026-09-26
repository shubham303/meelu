from src.site_structure.pipeline.review import VERDICTS

SCHEMA = {
    "type": "object",
    "properties": {
        "verdict": {"type": "string", "enum": [v.value for v in VERDICTS]},
        "reason": {"type": "string"},
    },
    "required": ["verdict", "reason"],
    "additionalProperties": False,
}

INSTRUCTIONS = """You review one proposed internal link on a website and decide whether it should be shown to the site owner.

The owner's brief for this run:
{prompt}

Answer with a verdict: "review_approved" when the link is worth the owner's time as the brief describes, "review_rejected" when it is not. Judge from the source passage, the target page and the suggestion text. A link is not worth it when the pages are unrelated, when the passage does not really discuss what the target is about, when the passage is boilerplate, or when the link would read as spam to a reader. Give a one-sentence reason."""
