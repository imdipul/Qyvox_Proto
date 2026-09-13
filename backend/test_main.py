"""Focused API and verifier tests that require no live Supabase project."""

from __future__ import annotations

import os
import unittest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch
from uuid import UUID

os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "test-only-service-role-key")
os.environ.setdefault("EXPECTED_CURRENT_YEAR", "2026")

from fastapi.testclient import TestClient  # noqa: E402

import main  # noqa: E402


VALID_SHAPE_PROOF = {
    "pi_a": ["0", "0", "1"],
    "pi_b": [["0", "0"], ["0", "0"], ["1", "0"]],
    "pi_c": ["0", "0", "1"],
    "protocol": "groth16",
    "curve": "bn128",
}


class QyvoxApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        async def authenticated_test_user() -> UUID:
            return UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")

        main.app.dependency_overrides[main._authenticated_user_id] = authenticated_test_user
        cls.client = TestClient(main.app)

    @classmethod
    def tearDownClass(cls) -> None:
        main.app.dependency_overrides.clear()

    def payload(self) -> dict[str, object]:
        return {
            "proof": VALID_SHAPE_PROOF,
            "publicSignals": ["1", "2026"],
        }

    def test_health(self) -> None:
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_status_reports_bounded_dependency_state(self) -> None:
        with patch.object(main, "get_supabase") as supabase:
            supabase.return_value.table.return_value.select.return_value.limit.return_value.execute.return_value.data = []
            response = self.client.get("/status")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["api"], "operational")
        self.assertIn(response.json()["verifier"], {"operational", "unavailable"})
        self.assertEqual(response.json()["database"], "operational")

    def test_body_rejects_private_birth_year(self) -> None:
        payload = self.payload()
        payload["birthYear"] = 2000
        response = self.client.post("/verify", json=payload)
        self.assertEqual(response.status_code, 422)

    def test_server_rejects_stale_public_year_before_verification(self) -> None:
        payload = self.payload()
        payload["publicSignals"] = ["1", "2025"]
        response = self.client.post("/verify", json=payload)
        self.assertEqual(response.status_code, 403)

    def test_false_snark_verdict_is_forbidden(self) -> None:
        with (
            patch.object(main, "_proof_was_consumed", AsyncMock(return_value=False)),
            patch.object(main, "_run_snarkjs_verifier", return_value=False),
        ):
            response = self.client.post("/verify", json=self.payload())
        self.assertEqual(response.status_code, 403)

    def test_valid_proof_records_only_verification_receipt(self) -> None:
        timestamp = datetime(2026, 8, 25, 12, 0, tzinfo=timezone.utc)
        with (
            patch.object(main, "_proof_was_consumed", AsyncMock(return_value=False)),
            patch.object(main, "_run_snarkjs_verifier", return_value=True),
            patch.object(main, "_record_verification", AsyncMock(return_value=timestamp)) as record,
        ):
            response = self.client.post("/verify", json=self.payload())

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["verified"], True)
        trace = response.json()["trace"]
        self.assertEqual(trace["proof_system"], "Groth16")
        self.assertEqual(trace["curve"], "BN254 / bn128")
        self.assertEqual(trace["received_fields"], ["proof", "publicSignals"])
        self.assertEqual(
            trace["stored_fields"],
            ["user_id", "verified_at", "proof_hash"],
        )
        self.assertEqual(
            [step["component"] for step in trace["steps"]],
            ["policy", "replay", "verifier", "database"],
        )
        self.assertTrue(all(step["duration_ms"] >= 0 for step in trace["steps"]))
        self.assertGreaterEqual(trace["total_ms"], 0)
        self.assertEqual(record.await_count, 1)
        stored_arguments = record.await_args.args
        self.assertIsInstance(stored_arguments[0], UUID)
        self.assertRegex(stored_arguments[1], r"^[0-9a-f]{64}$")

    def test_oversized_body_is_rejected_before_json_parsing(self) -> None:
        for path in ("/verify", "/api/v1/verify"):
            with self.subTest(path=path):
                response = self.client.post(
                    path,
                    content="x" * (main.settings.max_request_bytes + 1),
                    headers={"Content-Type": "application/json"},
                )
                self.assertEqual(response.status_code, 413)

    def test_replayed_proof_is_rejected_before_verification(self) -> None:
        with (
            patch.object(main, "_proof_was_consumed", AsyncMock(return_value=True)),
            patch.object(main, "_run_snarkjs_verifier") as verifier,
        ):
            response = self.client.post("/api/v1/verify", json=self.payload())
        self.assertEqual(response.status_code, 409)
        verifier.assert_not_called()

    def test_replay_store_outage_fails_closed(self) -> None:
        with (
            patch.object(
                main,
                "_proof_was_consumed",
                AsyncMock(side_effect=ConnectionError("database unavailable")),
            ),
            patch.object(main, "_run_snarkjs_verifier") as verifier,
        ):
            response = self.client.post("/api/v1/verify", json=self.payload())
        self.assertEqual(response.status_code, 502)
        self.assertEqual(
            response.json()["detail"],
            "Replay protection is temporarily unavailable.",
        )
        verifier.assert_not_called()

    def test_unknown_proof_fields_are_rejected(self) -> None:
        payload = self.payload()
        proof = dict(payload["proof"])
        proof["privateWitness"] = "must never be accepted"
        payload["proof"] = proof
        response = self.client.post("/api/v1/verify", json=payload)
        self.assertEqual(response.status_code, 422)

    def test_off_curve_points_are_an_invalid_proof_not_a_server_error(self) -> None:
        payload = main.VerifyRequest.model_validate(self.payload())
        self.assertFalse(main._run_snarkjs_verifier(payload))


if __name__ == "__main__":
    unittest.main()
