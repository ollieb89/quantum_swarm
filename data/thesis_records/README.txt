Deferred Accuracy path — Phase 16 stub.

At debate time, each agent emits a thesis record to this directory in JSONL format:
{agent_id, decision_id, instrument, direction, timestamp}

A future reconciliation process (Phase 17 or standalone script) will join these
records to trade resolution events and apply the Accuracy EMA update in kami.py.

Format: {decision_id}.jsonl — one JSON object per line.
