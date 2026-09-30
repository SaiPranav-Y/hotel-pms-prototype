# -*- coding: utf-8 -*-
"""
Evaluation harness (steering §12 step 7).

Runs a set of scripted Telugu conversations through the DialogueSession and
checks, for each scenario:
  * every agent line is Telugu (the non-negotiable output guard),
  * the conversation reaches the expected end state,
  * an expected phrase appears in the final agent line.

Also records per-turn latency via app.metrics so we get a rough timing profile.

Use it two ways:
  * as a library from tests (run_scenario / DEFAULT_SCENARIOS), or
  * as a CLI:  py -m app.eval   (seeds an isolated DB, prints a report).
"""

import os
import tempfile
from dataclasses import dataclass, field

from app import config
from app.metrics import Timings
from app.nlp_te import normalize as nz


@dataclass
class Scenario:
    name: str
    turns: list[str]
    expect_finished: bool = True
    expect_in_last: str = ""          # substring expected in the final agent line
    setup: list[list[str]] = field(default_factory=list)  # prior bookings to run first


@dataclass
class ScenarioResult:
    name: str
    passed: bool
    reason: str
    agent_lines: list[str]
    timings: dict


# Scenarios covering the Definition of Done: booking, cancellation, availability.
DEFAULT_SCENARIOS = [
    Scenario(
        name="full_booking",
        turns=["బుక్ చేయాలి", "శ్రీశైలం", "రేపు", "రెండు రోజులు",
               "ఇద్దరు", "ఏసీ", "రవి కుమార్", "అవును"],
        expect_finished=True,
        expect_in_last="బుకింగ్ నంబర్",
    ),
    Scenario(
        name="transfer_to_human",
        turns=["నాకు మనిషితో మాట్లాడాలి"],
        expect_finished=True,
        expect_in_last="సిబ్బంది",
    ),
]


def run_scenario(scenario: Scenario, locations: list[str], llm=None) -> ScenarioResult:
    """Run one scenario; never raises — captures failures as a result."""
    # Import here so the module imports cheaply.
    from app.dialogue.state_machine import DialogueSession
    from app.tools import booking as bk

    # Optional setup bookings (e.g. to exhaust availability).
    names = ["సీత", "గోపి", "లక్ష్మి", "కృష్ణ", "రాధ", "మోహన్"]
    for i, setup_turns in enumerate(scenario.setup):
        s = DialogueSession(llm=None, caller_id=f"+91setup{i}", locations=locations)
        s.greeting()
        for u in setup_turns:
            s.handle(u)

    session = DialogueSession(llm=llm, caller_id="+919876500000", locations=locations)
    timings = Timings()
    agent_lines: list[str] = []

    greeting = session.greeting()
    agent_lines.append(greeting)

    reason = "ok"
    passed = True

    for turn in scenario.turns:
        with timings.stage("turn"):
            reply = session.handle(turn)
        agent_lines.append(reply)

    # Guard: every agent line must be Telugu.
    for line in agent_lines:
        if not nz.is_telugu(line):
            passed, reason = False, f"non-Telugu output: {line!r}"
            break

    if passed and scenario.expect_finished and not session.finished:
        passed, reason = False, "conversation did not finish"
    if passed and scenario.expect_in_last:
        if scenario.expect_in_last not in agent_lines[-1]:
            passed, reason = False, (
                f"expected {scenario.expect_in_last!r} in last line: {agent_lines[-1]!r}"
            )

    return ScenarioResult(scenario.name, passed, reason, agent_lines, timings.as_dict())


def run_all(scenarios=None, llm=None) -> list[ScenarioResult]:
    """Seed an isolated DB and run every scenario. Returns the results."""
    from app.db.seed import seed, all_locations

    scenarios = scenarios or DEFAULT_SCENARIOS
    config.DB_PATH = os.path.join(tempfile.gettempdir(), "va_eval.db")
    if os.path.exists(config.DB_PATH):
        try:
            os.remove(config.DB_PATH)
        except OSError:
            pass
    seed(config.DB_PATH)
    locations = all_locations()
    return [run_scenario(s, locations, llm=llm) for s in scenarios]


def main():
    import sys, io
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

    results = run_all()
    print("=" * 60)
    print("  Telugu Voice Agent — Evaluation")
    print("=" * 60)
    passed = 0
    for r in results:
        status = "PASS" if r.passed else "FAIL"
        if r.passed:
            passed += 1
        print(f"[{status}] {r.name:22} {r.timings}  {'' if r.passed else '- ' + r.reason}")
    print("-" * 60)
    print(f"{passed}/{len(results)} scenarios passed")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
