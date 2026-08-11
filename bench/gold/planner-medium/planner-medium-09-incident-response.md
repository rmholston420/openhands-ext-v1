# planner-medium-09-incident-response

## Task summary
Plan the response to a production incident where the API is returning 500 errors on 30% of `/orders` requests. Include diagnosis, mitigation, root-cause fix, and postmortem steps.

## Reference plan (gold)

```json
{
  "steps": [
    {"id": "s1", "desc": "Acknowledge the incident in the on-call channel, declare severity level based on user impact (30% error rate on core endpoint = SEV-2 or SEV-1), page relevant engineers.", "deps": []},
    {"id": "s2", "desc": "Check dashboards and traces: error rate curve start time, error signatures (specific exception types), request patterns (all users vs subset, specific input patterns).", "deps": ["s1"]},
    {"id": "s3", "desc": "Correlate the error onset with recent deploys, config changes, or infrastructure events in the last hour to identify likely trigger.", "deps": ["s2"]},
    {"id": "s4", "desc": "Apply immediate mitigation: rollback the most-recent deploy if correlated, or feature-flag off the failing code path, or route traffic away from a degraded backend.", "deps": ["s3"]},
    {"id": "s5", "desc": "Verify mitigation via dashboards: error rate returns to baseline within 5-10 minutes; if not, escalate and try alternative mitigations.", "deps": ["s4"]},
    {"id": "s6", "desc": "Perform root-cause analysis on the identified code path or config: reproduce in staging, identify the underlying bug or race condition.", "deps": ["s5"]},
    {"id": "s7", "desc": "Land a permanent fix with regression test coverage, deploy through the normal release process, remove the temporary mitigation.", "deps": ["s6"]},
    {"id": "s8", "desc": "Write a postmortem documenting timeline, impact, root cause, contributing factors, mitigation actions, and follow-up items (monitoring gaps, playbook improvements).", "deps": ["s7"]}
  ]
}
```

## Scoring rubric (0-100)

| Band | Criteria |
|---|---|
| 90-100 | 5-8 steps covering: ack + sev decision → diagnose → correlate → mitigate → verify → RCA → permanent fix → postmortem. Mitigation happens BEFORE root-cause fix (prioritizes stopping bleeding). |
| 70-89 | All steps present but skips verification-of-mitigation step OR skips the postmortem. |
| 40-69 | Plan jumps to root-cause fix without a mitigation step (blocks users for the RCA duration — SLO-hostile). |
| 10-39 | Plan focused on writing tests / prevention without addressing the active incident. |
| 0-9 | <3 steps or invalid schema. |

## Notes
Tests planner's understanding of incident-response ordering. Key discriminator: does the plan mitigate before diagnosing root cause? Models that propose "find the bug then fix it" without a mitigation step reveal shallow ops understanding — the priority is stopping user impact, not eliminating the bug in place.
