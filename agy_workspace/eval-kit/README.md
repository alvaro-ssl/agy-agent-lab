# Decision-governance eval kit

Proves (or disproves) that the twin agent stays within its decision rights: it acts alone only where it is
allowed to, and never executes a decision that needs a human without an approval recorded in the Decision
Inbox — even when someone claims authority in chat.

| File | Purpose |
| --- | --- |
| `datasets/decision-governance.json` | 5 cases: analyse and act, a fix that needs approval, a CEO override, a fabricated approval, a forbidden action |
| `decision_guardrail.py` | Deterministic metric — fails if `take_action` executed an approval-required action |
| `governance_judge.py` | Local LLM judge — scores behaviour 1-5 against each case's `expected_behavior` |
| `governance_eval_config.yaml` | Selects both metrics |

The cases are company-agnostic: they work whatever company the twin was reshaped into.

## Use it (from the `agy_workspace/` root)

```bash
cp eval-kit/datasets/decision-governance.json twin-agent/tests/eval/datasets/
cp eval-kit/*.py eval-kit/governance_eval_config.yaml twin-agent/tests/eval/
cd twin-agent
agents-cli eval run --dataset tests/eval/datasets/decision-governance.json --config tests/eval/governance_eval_config.yaml
```

Actions executed during an eval are written to the twin's audit log. Regenerate the twin before each run:

```bash
.venv/bin/python company-twin/generate_twin.py
```
