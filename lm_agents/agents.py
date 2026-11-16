"""Multi-agent pipeline for Legal Metrology compliance checking.

Agents (each logs its reasoning into a shared trace):
  1. IntakeAgent      - inspects the input and plans which tools to use
  2. ExtractionAgent  - extracts fields (LLM or regex) and REFLECTS: if mandatory
                        fields are missing it retries with the alternate strategy
  3. ValidationAgent  - calls the deterministic rule engine tool
  4. ExplanationAgent - writes a grounded, plain-language report (LLM or template)
  5. ComplianceOrchestrator - runs the agents in order and never crashes
"""
from __future__ import annotations

import json
from datetime import date
from typing import Dict, List, Optional

from .extractor import empty_fields, extract_llm, extract_regex
from .rules import MANDATORY_FIELDS, RuleResult, is_missing, summarize, validate


class Trace:
    def __init__(self) -> None:
        self.steps: List[Dict[str, object]] = []

    def log(self, agent: str, action: str, observation: str) -> None:
        self.steps.append(
            {"step": len(self.steps) + 1, "agent": agent, "action": action,
             "observation": observation}
        )


def _missing(fields: Dict[str, object]) -> List[str]:
    return [k for k in MANDATORY_FIELDS if is_missing(fields.get(k))]


class IntakeAgent:
    name = "IntakeAgent"

    def run(self, state: Dict[str, object], trace: Trace) -> None:
        text = (state.get("text") or "").strip()
        image = state.get("image_bytes")
        llm = state.get("llm")
        if not text and not image:
            raise ValueError("No input provided. Paste listing text or upload a label image.")
        if image and llm is None:
            raise ValueError(
                "Image input needs LLM mode. Set ANTHROPIC_API_KEY (or enter a key in the app), "
                "or paste the label text instead."
            )
        kind = "image+text" if image and text else ("image" if image else "text")
        plan = ["extract"]
        plan.append("llm-first" if llm is not None else "regex-only")
        plan += ["reflect-if-missing", "validate", "explain"]
        state["input_type"] = kind
        trace.log(self.name, "classify input and plan",
                  "Input type: %s. Plan: %s." % (kind, " -> ".join(plan)))


class ExtractionAgent:
    name = "ExtractionAgent"

    def run(self, state: Dict[str, object], trace: Trace) -> None:
        llm = state.get("llm")
        text = state.get("text") or ""
        image = state.get("image_bytes")
        fields: Optional[Dict[str, object]] = None
        strategy = "regex"

        if llm is not None:
            try:
                fields = extract_llm(llm, text, image, state.get("media_type") or "image/png")
                strategy = "llm"
                trace.log(self.name, "tool: extract_llm", "LLM extraction succeeded.")
            except Exception as exc:  # network, auth, bad JSON ...
                trace.log(self.name, "tool: extract_llm",
                          "LLM extraction failed (%s). Falling back to regex." % type(exc).__name__)
                state["llm_failed"] = True
        if fields is None:
            if not text:
                raise ValueError("LLM extraction failed and there is no text to fall back on.")
            fields = extract_regex(text)
            strategy = "regex"
            trace.log(self.name, "tool: extract_regex", "Offline regex extraction completed.")

        # Reflection loop: try the other strategy for fields that are still missing.
        missing = _missing(fields)
        if missing:
            trace.log(self.name, "reflect",
                      "Missing after first pass: %s. Trying alternate strategy." % ", ".join(missing))
            alt: Optional[Dict[str, object]] = None
            if strategy == "regex" and llm is not None and not state.get("llm_failed"):
                try:
                    alt = extract_llm(llm, text, image, state.get("media_type") or "image/png")
                except Exception as exc:
                    trace.log(self.name, "tool: extract_llm (retry)",
                              "Retry failed (%s)." % type(exc).__name__)
            elif strategy == "llm" and text:
                alt = extract_regex(text)
            if alt:
                filled = []
                for key in missing:
                    if not is_missing(alt.get(key)):
                        fields[key] = alt[key]
                        filled.append(key)
                if alt.get("mrp_incl_tax"):
                    fields["mrp_incl_tax"] = True
                trace.log(self.name, "reflect result",
                          "Recovered: %s." % (", ".join(filled) if filled else "nothing new"))
            still = _missing(fields)
            if still:
                trace.log(self.name, "reflect result",
                          "Still missing (treated as absent from the listing): %s." % ", ".join(still))

        state["fields"] = fields
        state["strategy"] = strategy


class ValidationAgent:
    name = "ValidationAgent"

    def run(self, state: Dict[str, object], trace: Trace) -> None:
        results = validate(state["fields"], today=state.get("today"))
        status, score = summarize(results)
        state["results"] = results
        state["status"] = status
        state["score"] = score
        failed = [r.rule_id for r in results if r.status == "FAIL"]
        trace.log(self.name, "tool: rule_engine.validate",
                  "%d rules run, failed: %s. Status=%s, score=%d."
                  % (len([r for r in results if r.status != "SKIP"]),
                     ", ".join(failed) if failed else "none", status, score))


def template_explanation(status: str, score: int, failures: List[RuleResult]) -> str:
    if not failures:
        return "All checked declarations are present and valid (score %d/100)." % score
    lines = ["Overall status: %s (score %d/100). %d issue(s) found:" % (status, score, len(failures))]
    for r in failures:
        lines.append("- [%s] %s - %s Fix: %s" % (r.rule_id, r.name, r.message, r.fix))
    return "\n".join(lines)


class ExplanationAgent:
    name = "ExplanationAgent"
    SYSTEM = (
        "You are a Legal Metrology compliance assistant. Write a concise plain-language "
        "summary (max 120 words) for an e-commerce seller using ONLY the findings given. "
        "Do not invent rules, penalties or legal citations."
    )

    def run(self, state: Dict[str, object], trace: Trace) -> None:
        failures = [r for r in state["results"] if r.status == "FAIL"]
        base = template_explanation(state["status"], state["score"], failures)
        llm = state.get("llm")
        summary = ""
        if llm is not None and failures and not state.get("llm_failed"):
            try:
                payload = json.dumps({
                    "status": state["status"],
                    "score": state["score"],
                    "issues": [{"id": r.rule_id, "problem": r.message, "fix": r.fix} for r in failures],
                })
                summary = llm.complete(self.SYSTEM, payload, max_tokens=400).strip()
                trace.log(self.name, "tool: llm.summarize", "LLM summary generated.")
            except Exception as exc:
                trace.log(self.name, "tool: llm.summarize",
                          "LLM summary failed (%s). Using template." % type(exc).__name__)
        else:
            trace.log(self.name, "tool: template", "Template explanation generated.")
        state["explanation"] = (summary + "\n\n" + base).strip() if summary else base


class ComplianceOrchestrator:
    """Runs the agent pipeline. `check()` never raises; errors come back as status 'ERROR'."""

    def __init__(self, llm=None, today: Optional[date] = None) -> None:
        self.llm = llm
        self.today = today
        self.pipeline = [IntakeAgent(), ExtractionAgent(), ValidationAgent(), ExplanationAgent()]

    @property
    def mode(self) -> str:
        return "LLM-assisted (Claude)" if self.llm is not None else "Offline (rule-based)"

    def check(self, text: Optional[str] = None, image_bytes: Optional[bytes] = None,
              media_type: str = "image/png", listing_id: str = "listing") -> Dict[str, object]:
        trace = Trace()
        state: Dict[str, object] = {
            "text": text, "image_bytes": image_bytes, "media_type": media_type,
            "llm": self.llm, "today": self.today,
        }
        try:
            for agent in self.pipeline:
                agent.run(state, trace)
        except Exception as exc:
            trace.log("Orchestrator", "error", str(exc))
            return {
                "listing_id": listing_id, "status": "ERROR", "score": 0,
                "fields": state.get("fields") or empty_fields(), "results": [],
                "explanation": "Could not complete the check: %s" % exc,
                "trace": trace.steps, "mode": self.mode,
            }
        return {
            "listing_id": listing_id,
            "status": state["status"],
            "score": state["score"],
            "fields": state["fields"],
            "results": [r.to_dict() for r in state["results"]],
            "explanation": state["explanation"],
            "trace": trace.steps,
            "mode": self.mode,
        }
