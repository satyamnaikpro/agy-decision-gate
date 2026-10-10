"""Unit tests for TypeSafe SDK schemas, question normalization, and client configuration.

These tests run completely offline without an active network connection or LLM runner.
"""

import unittest
from typesafe_sdk import (
    Choice,
    ChoiceAnswer,
    Noul,
    NoulAnswer,
    Score,
    ScoreAnswer,
    TypeSafeClient,
    TypeSafeError,
)
from typesafe_sdk._core.questions import normalize_questions


class TestTypeSafeSchemas(unittest.TestCase):
    def test_noul_question(self):
        """Verify Noul (Boolean probability) question model."""
        q = Noul(instructions="Is this an urgent issue?")
        self.assertEqual(q.type, "noul")
        self.assertEqual(q.instructions, "Is this an urgent issue?")

    def test_choice_question(self):
        """Verify Choice question model with options."""
        q = Choice(
            instructions="Select classification category",
            criteria={
                "billing": "Billing and payment issues",
                "support": "Technical support inquiries",
            },
        )
        self.assertEqual(q.type, "choice")
        self.assertIn("billing", q.criteria)
        self.assertIn("support", q.criteria)

    def test_score_question(self):
        """Verify Score question rubric criteria."""
        q = Score(
            instructions="Rate urgency level",
            criteria=["Low", "Medium", "High"],
        )
        self.assertEqual(q.type, "score")
        self.assertEqual(len(q.criteria), 3)

    def test_question_normalization(self):
        """Verify question normalization into wire format."""
        normalized = normalize_questions({
            "is_urgent": Noul(instructions="Urgent?"),
            "category": Choice(instructions="Category?", criteria={"a": "Opt A", "b": "Opt B"}),
            "severity": Score(instructions="Severity?", criteria=["Low", "High"]),
        })
        self.assertIn("is_urgent", normalized)
        self.assertEqual(normalized["is_urgent"].type, "noul")
        self.assertEqual(normalized["category"].type, "choice")
        self.assertEqual(normalized["severity"].type, "score")

    def test_client_configuration(self):
        """Verify TypeSafeClient parses Ollama base_url and model."""
        client = TypeSafeClient(
            base_url="http://localhost:11434",
            api_key="ollama",
            model="tev1:0.8b",
        )
        self.assertEqual(client._config.base_url, "http://localhost:11434")
        self.assertEqual(client._config.default_model, "tev1:0.8b")
        self.assertEqual(client._config.api_key, "ollama")

    def test_empty_api_key_raises_error(self):
        """Verify client validates non-empty API key."""
        with self.assertRaises(TypeSafeError):
            TypeSafeClient(base_url="http://localhost:11434", api_key="")


if __name__ == "__main__":
    unittest.main()
