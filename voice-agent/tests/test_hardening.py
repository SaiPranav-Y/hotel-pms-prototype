# -*- coding: utf-8 -*-
"""
Hardening tests (steering §10-11):
  * eval harness runs the DoD scenarios with the Telugu guard,
  * latency Timings behaves,
  * concurrent create_booking never double-books the last room.
"""

import threading
from datetime import timedelta

from app import eval as EV
from app.metrics import Timings
from app.nlp_te import normalize as nz
from app.tools import availability as av
from app.tools import booking as bk

FULL_LOC = "Vruddasramam"


class TestEvalHarness:
    def test_default_scenarios_pass(self, seeded_db):
        results = [
            EV.run_scenario(s, seeded_db["locations"])
            for s in EV.DEFAULT_SCENARIOS
        ]
        assert results
        for r in results:
            assert r.passed, f"{r.name} failed: {r.reason}"
            # Every agent line Telugu (the harness checks it; re-assert here).
            for line in r.agent_lines:
                assert nz.is_telugu(line)
            assert "total" in r.timings

    def test_availability_exhaustion_scenario(self, seeded_db):
        # Book out all AC rooms via setup, then a fresh caller is refused.
        ci = nz.today() + timedelta(days=1)
        co = ci + timedelta(days=1)
        offers = av.check_availability(FULL_LOC, ci, co, 1, "AC")
        cap = next((o.rooms_available for o in offers if o.room_type == "AC"), 0)
        assert cap >= 1

        setup = [["బుక్", "వృద్ధాశ్రమం", "రేపు", "ఒక రోజు", "ఒకరు", "ఏసీ", "అతిథి", "అవును"]
                 for _ in range(cap)]
        sc = EV.Scenario(
            name="no_rooms",
            turns=["బుక్", "వృద్ధాశ్రమం", "రేపు", "ఒక రోజు", "ఒకరు", "ఏసీ", "కొత్త"],
            expect_finished=False,
            expect_in_last="అందుబాటులో లేవు",
            setup=setup,
        )
        r = EV.run_scenario(sc, seeded_db["locations"])
        assert r.passed, r.reason


class TestTimings:
    def test_stage_accumulates(self):
        import time
        t = Timings()
        with t.stage("a"):
            time.sleep(0.01)
        with t.stage("a"):
            time.sleep(0.01)
        assert t.get("a") >= 0.02
        d = t.as_dict()
        assert "a" in d and "total" in d

    def test_summary_is_string(self):
        t = Timings()
        with t.stage("x"):
            pass
        assert "total=" in t.summary()


class TestConcurrency:
    def test_no_double_booking_under_threads(self, seeded_db):
        """
        Fire more concurrent booking attempts than there are AC rooms; the
        transactional create_booking (BEGIN IMMEDIATE + re-check) must let
        exactly `capacity` succeed and reject the rest.
        """
        ci = nz.today() + timedelta(days=1)
        co = ci + timedelta(days=1)
        offers = av.check_availability(FULL_LOC, ci, co, 1, "AC")
        cap = next((o.rooms_available for o in offers if o.room_type == "AC"), 0)
        assert cap >= 1

        attempts = cap + 4
        results = [None] * attempts
        barrier = threading.Barrier(attempts)

        def worker(i):
            barrier.wait()  # maximize contention: everyone starts together
            results[i] = bk.create_booking(
                location=FULL_LOC, room_type="AC", guest_name=f"g{i}",
                phone=f"+9199{i:03d}", check_in=ci, check_out=co,
                guests=1, num_rooms=1,
            )

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(attempts)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        successes = [r for r in results if r and r.success]
        failures = [r for r in results if r and not r.success]
        assert len(successes) == cap, f"expected {cap} successes, got {len(successes)}"
        assert all(f.error == "no_rooms" for f in failures)

        # Booking ids are unique (no id collision under contention).
        ids = [r.booking_id for r in successes]
        assert len(set(ids)) == len(ids)
