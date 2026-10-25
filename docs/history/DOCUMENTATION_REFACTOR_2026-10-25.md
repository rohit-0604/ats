# Documentation architecture refactor - 2026-10-25

Scope C22: semantics-preserving documentation/navigation refactor only. No architecture
research, product/source/test/dependency changes or new milestone work. Starting local
HEAD was `b94d76da1a09d6b3df220965c1c7f14884ca394c`; the index was empty. Eight tracked Markdown files already had
uncommitted C20/C21 edits and DOMAIN_WORKFLOWS_REVIEW was untracked. Those working-tree
versions, rather than HEAD versions, were the preservation baseline.

## Findings and structure

The costliest avoidable context was temporal duplication, rather than exact text copies:
AGENTS had 100 lines under authorization history; NEXT_STEPS mixed nine current/old
handoff sections, including incompatible former stop/commit instructions; CURRENT_STATE
began with 94 lines of successive status updates and retained audit/environment/artifact
history. ROADMAP repeated 56 preamble lines of status/research/approval summaries.
The old resume checklist requested many documents even for narrow tasks.

A paragraph scan (at least 25 whitespace-delimited words) found only one exact repeated
paragraph across documents: the shared M0 API signature block in specification/contracts.
It was retained because both documents are approved milestone authorities. Near-duplicate
status claims and temporal contradictions, not verbatim requirement copies, drove the
entry-point refactor. No obligation was deduplicated by interpreting similar wording.

The [index](../README.md) defines Level 1 current rules/scope/status, Level 2 exact
contracts/affected requirements/ADRs/architecture/findings, and Level 3 historical
evidence. Level 3 is a loading category, not retirement of referenced requirements.
Milestone verification records and ADRs stay at their original paths and statuses.

## Always-read context measurement

The same three entry files fell from **851 to 234 lines** (72.5% reduction)
and **7,279 to 1,891 whitespace-delimited words** (74.0% reduction).
These are context-volume proxies, not tokenizer measurements or runtime benchmarks.
The index is task routing, not another mandatory full read. Archives increase stored
history deliberately; total repository text reduction is not the objective.

## Before and after inventory

All Markdown under docs plus root AGENTS is included. Largest section means the direct
span from a heading to the next heading (including its introductory text), not all
nested descendants. Counts include this report; its inventory row is computed after
the final report text is assembled.

| Path | Lines before -> after | Words before -> after | Headings before -> after | Largest direct section before -> after | Loading / ownership |
| --- | --- | --- | --- | --- | --- |
| `AGENTS.md` | 213 -> 124 | 1786 -> 1032 | 8 -> 8 | 100 -> 27 | L1: rules |
| `docs/ARCHITECTURE.md` | 446 -> 446 | 4667 -> 4667 | 15 -> 15 | 60 -> 60 | L2 boundaries/FIT; C21 evidence; unchanged |
| `docs/AUDIT_FINDINGS.md` | 306 -> 306 | 1982 -> 1982 | 20 -> 20 | 32 -> 32 | L2: F01-F17 details; unchanged |
| `docs/CAPABILITY_REQUIREMENTS.md` | 715 -> 715 | 6348 -> 6348 | 26 -> 26 | 49 -> 49 | L2: single CAP/acceptance authority; unchanged |
| `docs/CURRENT_STATE.md` | 311 -> 49 | 2755 -> 392 | 9 -> 2 | 94 -> 33 | L1: verified summary |
| `docs/DECISIONS.md` | 192 -> 193 | 2882 -> 2948 | 9 -> 9 | 40 -> 40 | L2: decisions / C01-C22 authorization |
| `docs/DOMAIN_WORKFLOWS_REVIEW.md` | 476 -> 476 | 6011 -> 6011 | 16 -> 16 | 55 -> 55 | L2 methodology + L3 review evidence; unchanged |
| `docs/GIT_PREPARATION.md` | 219 -> 219 | 1712 -> 1712 | 7 -> 7 | 61 -> 61 | L3 assessment / provenance; unchanged |
| `docs/M0_CONTRACTS_V1.md` | 421 -> 421 | 4318 -> 4318 | 10 -> 10 | 72 -> 72 | L2 exact milestone material; unchanged |
| `docs/M0_DECISION_RATIONALE.md` | 237 -> 237 | 2133 -> 2133 | 14 -> 14 | 29 -> 29 | L2 exact milestone material; unchanged |
| `docs/M0_VERIFICATION.md` | 150 -> 150 | 1632 -> 1632 | 6 -> 6 | 59 -> 59 | L3: unchanged verification evidence |
| `docs/M0_VERSIONED_BASELINES.md` | 278 -> 278 | 2756 -> 2756 | 15 -> 15 | 55 -> 55 | L2 exact milestone material; unchanged |
| `docs/M1_AUTHORITY_BOUND_PLANS.md` | 444 -> 444 | 4369 -> 4369 | 17 -> 17 | 45 -> 45 | L2 exact milestone material; unchanged |
| `docs/M1_VERIFICATION.md` | 173 -> 173 | 1824 -> 1824 | 7 -> 7 | 39 -> 39 | L3: unchanged verification evidence |
| `docs/M2_ARTIFACT_PACKAGES.md` | 523 -> 523 | 5121 -> 5121 | 22 -> 22 | 66 -> 66 | L2 exact milestone material; unchanged |
| `docs/M2_VERIFICATION.md` | 202 -> 202 | 1958 -> 1958 | 7 -> 7 | 52 -> 52 | L3: unchanged verification evidence |
| `docs/NEXT_STEPS.md` | 327 -> 61 | 2738 -> 467 | 10 -> 4 | 54 -> 31 | L1: scope / unchanged next task |
| `docs/POST_M0_FOUNDATIONS.md` | 293 -> 293 | 2980 -> 2980 | 13 -> 13 | 41 -> 41 | L3 assessment / provenance; unchanged |
| `docs/README.md` | 0 -> 66 | 0 -> 590 | 0 -> 4 | 0 -> 35 | Routing index, read applicable rows |
| `docs/ROADMAP.md` | 560 -> 518 | 5306 -> 4961 | 20 -> 20 | 58 -> 58 | L2: sequence / SC-01 / workstreams |
| `docs/adr/01-versioned-baselines.md` | 117 -> 117 | 796 -> 796 | 11 -> 11 | 24 -> 24 | L2 applicable decision; dated rationale retained |
| `docs/adr/02-deterministic-lifecycle.md` | 108 -> 108 | 723 -> 723 | 11 -> 11 | 28 -> 28 | L2 applicable decision; dated rationale retained |
| `docs/adr/03-artifact-identity.md` | 108 -> 108 | 807 -> 807 | 11 -> 11 | 36 -> 36 | L2 applicable decision; dated rationale retained |
| `docs/adr/04-isolated-execution.md` | 101 -> 101 | 716 -> 716 | 11 -> 11 | 24 -> 24 | L2 applicable decision; dated rationale retained |
| `docs/adr/05-safe-repair.md` | 104 -> 104 | 746 -> 746 | 11 -> 11 | 24 -> 24 | L2 applicable decision; dated rationale retained |
| `docs/adr/06-persistence-replay.md` | 112 -> 112 | 798 -> 798 | 11 -> 11 | 26 -> 26 | L2 applicable decision; dated rationale retained |
| `docs/adr/README.md` | 123 -> 123 | 1048 -> 1048 | 6 -> 6 | 44 -> 44 | L2 applicable decision; dated rationale retained |
| `docs/history/CONTEXT_BEFORE_2026-10-25.md` | 0 -> 975 | 0 -> 7942 | 0 -> 33 | 0 -> 102 | L3: lossless relocated context snapshots |
| `docs/history/DOCUMENTATION_REFACTOR_2026-10-25.md` | 0 -> 157 | 0 -> 1767 | 0 -> 7 | 0 -> 44 | L3: inventory / preservation verification |

The pre-edit set had 25 Markdown files under docs, plus AGENTS. Three documents were
added: the routing index, one archival snapshot document and this verification report.
All original files remain at their paths. No milestone contract/verification document,
ADR, CAP register, architecture assurance or finding was split to meet a size target.

## Preservation and consolidation limits

[CONTEXT_BEFORE](CONTEXT_BEFORE_2026-10-25.md) preserves complete original AGENTS,
NEXT_STEPS and CURRENT_STATE plus the removed ROADMAP preamble. It includes the
preexisting uncommitted edits, superseded instructions, Git permissions/checkpoints,
API/environment inventory, historical metrics, failures/limitations and negative evidence.
Mechanical edits there only relocate relative link paths and heading depth; explicit
source-prefixed anchors avoid ambiguous headings. Compatibility anchors at original
entry paths lead to the corresponding historical sections.

ARCHITECTURE (446 lines) and CAPABILITY_REQUIREMENTS (715 lines) remain byte-for-byte
unchanged: their sectioned evidence, alternatives and 19 stable CAP owners are task-specific
material. The index links directly to relevant sections, including domain acceptance
additions. ROADMAP's detailed body beginning with Product definition is unchanged;
only its repeated preamble was replaced. SC-01/SC-AC-01..06 remain in place. DECISIONS
retains all old text and rows, with only the new C22 scope row added.

No safe consolidation was inferred between similarly worded obligations in CAPs,
roadmap, approved milestone contracts or ADRs: they have different authority/scope.
Historical assessments retain useful alternatives and technical evidence. They remain
available on demand, rather than copied into a new specification. Dated installed
versions and untracked runtime artifact links remain qualified; their availability in
this checkout cannot establish clean-clone reproducibility or current product quality.

M0/M1/M2 are still complete offline; recorded verification results are not rerun.
The exact next bounded M2-R specification recommendation, numbered steps, non-goals
and MANUAL-first alternative were retained without textual change. No M2-R work began.

## Verification

Read-only Python standard-library checks covered all 29 Markdown files (28 under docs
plus AGENTS). The pre-edit reference inventory had **524 local links / 215 anchors**;
the final tree has **636 local links / 279 anchors**. All targets and source-line/heading/
explicit compatibility anchors resolve in this checkout; fences balance and no replacement
characters were found. Original heading anchors remain available at all original paths.
Historical untracked evidence links are still not promised to resolve in a clean clone.

All **274 inventoried stable identifier tokens** remain present. More strongly, all
**15 protected milestone/ADR documents** and the complete CAP, architecture, domain-review
and F01-F17 documents are unchanged. The detailed ROADMAP body (including SC acceptance)
and exact numbered M2-R recommendation/non-goals match their pre-edit texts. C01-C21
and every earlier decision/status remain unchanged; C22 is the only added scope row.
Four archive blocks match their complete original source chunks after mechanical link/
heading relocation. This comparison preserves prose, code, tables, limitations and prior
uncommitted content, rather than relying on identifier presence alone.

All **66 tracked non-documentation files** match pre-edit SHA-256 hashes. Twenty-one
original Markdown files are unchanged; only AGENTS, NEXT_STEPS, CURRENT_STATE, ROADMAP
and the additive DECISIONS row changed. AGENTS retains its standing policy sections;
its dated no-regression-suite sentence was clarified to distinguish the existing offline
suite from the unverified legacy-runtime/lint/type/CI gates. The original wording is
retained in the archive. No product behavior or verification obligation changed.

`git diff --check` passed. A bounded common token/private-key-pattern scan found no
matches in changed/new documentation; this is not a proof that arbitrary free text is
nonsensitive. HEAD and the empty index remain unchanged. No application tests, installs,
providers, generated execution/compilation, commits, remote queries or deployment ran.
The historical 116-test result is unchanged evidence, not a new test result.


## Cross-reference inventory and authority boundaries

The baseline link inventory was captured before edits. Highest inbound reference counts
are listed below as a navigation measurement, not a requirement-importance ranking.
All original document paths and heading anchors were retained; new index/compatibility
links increase total references intentionally while reducing default loading.

| Original target | Inbound local links before refactor |
| --- | --- |
| `app/core/react_controller.py` | 32 |
| `app/core/evaluator_engine.py` | 29 |
| `docs/CAPABILITY_REQUIREMENTS.md` | 25 |
| `docs/ROADMAP.md` | 23 |
| `docs/ARCHITECTURE.md` | 20 |
| `docs/AUDIT_FINDINGS.md` | 20 |
| `docs/M0_VERIFICATION.md` | 20 |
| `docs/M0_VERSIONED_BASELINES.md` | 17 |
