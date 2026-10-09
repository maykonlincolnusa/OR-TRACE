"""Temporal reachability, not an assertion of ownership of fungible money."""

from collections import defaultdict
from decimal import Decimal

from or_trace.domain.models import Finding, Path
from or_trace.domain.ports import Ledger


class TraceService:
    RULE_VERSION = "1.0"
    RAPID_SECONDS = 3600
    PASS_THROUGH_RATIO = Decimal("0.90")

    def __init__(self, ledger: Ledger):
        self.ledger = ledger

    def trace(
        self,
        account_id,
        direction,
        start,
        end,
        currency,
        max_hops=5,
        max_paths=100,
        max_expansions=10000,
    ):
        if direction not in ("forward", "backward"):
            raise ValueError("invalid direction")
        if not self.ledger.has_account(account_id):
            raise LookupError("account not found")
        if start > end:
            raise ValueError("start must precede end")
        transactions = [
            t
            for t in self.ledger.snapshot()
            if start <= t.occurred_at <= end and t.currency == currency
        ]
        outgoing, incoming = defaultdict(list), defaultdict(list)
        for tx in transactions:
            outgoing[tx.source_account_id].append(tx)
            incoming[tx.destination_account_id].append(tx)
        adjacency = outgoing if direction == "forward" else incoming
        stack = [(account_id, (), (account_id,))]
        paths = []
        expansions = 0
        truncated = False
        while stack:
            node, edges, accounts = stack.pop()
            candidates = adjacency[node]
            advanced = False
            for tx in reversed(candidates):
                if edges:
                    last = edges[-1]
                    if direction == "forward" and tx.occurred_at <= last.occurred_at:
                        continue
                    if direction == "backward" and tx.occurred_at >= last.occurred_at:
                        continue
                if expansions >= max_expansions:
                    truncated = True
                    break
                expansions += 1
                advanced = True
                nxt = tx.destination_account_id if direction == "forward" else tx.source_account_id
                new_edges, new_accounts = edges + (tx,), accounts + (nxt,)
                cycle = nxt in accounts
                if cycle or len(new_edges) >= max_hops:
                    paths.append(
                        self._path(new_edges, new_accounts, direction, cycle, outgoing, incoming)
                    )
                    if not cycle and adjacency[nxt]:
                        truncated = True
                else:
                    stack.append((nxt, new_edges, new_accounts))
                if len(paths) >= max_paths:
                    truncated = True
                    break
            if not advanced and edges:
                paths.append(self._path(edges, accounts, direction, False, outgoing, incoming))
            if expansions >= max_expansions or len(paths) >= max_paths:
                truncated = True
                break
        return {
            "paths": paths[:max_paths],
            "truncated": truncated,
            "expansions": expansions,
            "rule_version": self.RULE_VERSION,
            "attribution_method": "temporal_reachability",
            "assumptions": [
                "Strictly increasing transaction timestamps; equal timestamps are ambiguous",
                "Bottleneck is an upper bound per path, never an allocated amount",
                "Paths may overlap; do not sum bottlenecks",
                "Results cover only ingested transactions in the requested window",
            ],
        }

    def _path(self, edges, accounts, direction, cycle, outgoing, incoming):
        if direction == "backward":
            edges, accounts = edges[::-1], accounts[::-1]
        findings = []
        for account in dict.fromkeys(accounts):
            outs, ins = outgoing[account], incoming[account]
            if len({t.destination_account_id for t in outs}) >= 3:
                findings.append(
                    Finding(
                        "fan_out",
                        15,
                        tuple(t.id for t in outs),
                        (account,),
                        "At least 3 distinct destinations in query window",
                    )
                )
            if len({t.source_account_id for t in ins}) >= 3:
                findings.append(
                    Finding(
                        "fan_in",
                        15,
                        tuple(t.id for t in ins),
                        (account,),
                        "At least 3 distinct origins in query window",
                    )
                )
        for previous, current in zip(edges, edges[1:]):
            seconds = (current.occurred_at - previous.occurred_at).total_seconds()
            if seconds <= self.RAPID_SECONDS:
                ids = (previous.id, current.id)
                middle = (previous.destination_account_id,)
                findings.append(
                    Finding(
                        "rapid_movement",
                        20,
                        ids,
                        middle,
                        f"Consecutive transfers separated by {seconds:g}s (threshold 3600s)",
                    )
                )
                ratio = current.amount / previous.amount
                if self.PASS_THROUGH_RATIO <= ratio <= Decimal("1.10"):
                    findings.append(
                        Finding(
                            "pass_through",
                            25,
                            ids,
                            middle,
                            f"Candidate pass-through: outflow/inflow={ratio}, within 1h",
                        )
                    )
        if cycle:
            findings.append(
                Finding(
                    "circular_flow",
                    30,
                    tuple(t.id for t in edges),
                    accounts,
                    "Temporal path revisits an account; traversal stops at first revisit",
                )
            )
        # A rule contributes once, even when multiple pairs supply evidence.
        weights = {f.code: f.weight for f in findings}
        return Path(
            accounts,
            tuple(t.id for t in edges),
            edges[0].currency,
            min(t.amount for t in edges),
            (edges[-1].occurred_at - edges[0].occurred_at).total_seconds(),
            min(100, sum(weights.values())),
            tuple(findings),
            cycle,
        )
