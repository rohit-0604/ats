# M2 implementation and verification record

Date: 2026-10-25, Asia/Calcutta. Specification: **M2-SPEC-2026-10-25-v2**.
Status: **IMPLEMENTED AND VERIFIED OFFLINE**. The user approved the exact M2 slice,
M2-D01..07, V1 contracts, M2-AC-01..26 and the narrow decoder correction, then resumed
implementation and one reviewed local checkpoint. See C19 in [DECISIONS](DECISIONS.md).
M2-R, M3/M4/M5 and all generated execution remain outside this approval.

## Actual verification

```powershell
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -p "test_*.py" -v
```

**Final rerun: 116 tests passed in 66.165 seconds; zero failures, errors or skips.** This comprises
48 unchanged M0 acceptance/regression tests, 30 unchanged M1 acceptance tests,
26 named M2 acceptance families and 12 additional M2 boundary regressions.
The final rerun includes the complete-package digest-overhead boundary. The preceding
full run passed the same 116 test methods in 53.062 seconds, before that extra boundary
variant was added. No required test or assertion was weakened.

Earlier M2-only evidence: the first test-first run had two import errors because the
implementation modules did not yet exist. The first complete 32-test M2 run had 30
passes and two errors exposing the M1-to-M2 error-translation defect described below.
After correction, all 32 passed in 18.221 seconds. An expanded 36-test M2 run passed
in 26.362 seconds, followed by the full 116-test run above. These are historical
iterations, not additional distinct acceptance cases or current unresolved failures.

Environment verified locally: Python 3.11.9, Pydantic 2.12.5, SQLite 3.45.1, Windows.
No dependencies were installed. No formatting/lint/type-check or clean-install result
is claimed. Tests use synthetic bytes and temporary stores/files, fake inspections,
fault injection, a real Windows junction, real SQLite contention and a hot journal.
Trusted Python child processes create no-effects/crash fixtures; no generated script,
TypeScript compilation, Playwright discovery, browser, target or provider was invoked.

## Implemented behavior and files

| File | Responsibility |
| --- | --- |
| [artifact_contracts.py](../app/artifact_contracts.py) | Separate strict immutable V1 models, safe errors, bounded decoder/base64 integrity, logical paths, canonical manifest/package identity and deterministic test UUIDs |
| [artifact_policy.py](../app/core/artifact_policy.py) | Pure complete scenario/test/configuration mapping, oracle-reference checks, freeze and non-authorizing assessment |
| [artifact_service.py](../app/core/artifact_service.py) | Exactly one read-only M0 inspection per operation; M1 pure-policy composition from the same observation |
| [artifact_cli.py](../app/artifact_cli.py) | Separate help/version/test-id/validate/freeze/assess interface; bounded single-file read/exclusive export through unchanged M0 helpers |
| [contract tests](../tests/test_m2_artifacts.py) | Independent vectors, role/byte changes, mappings, strictness and exact decoder/collection/canonical bounds |
| [boundary tests](../tests/test_m2_artifact_boundaries.py) | Real authority/revocation, CLI, exports/faults, no-effects and protected-source inventory |
| [golden fixture](../tests/fixtures/artifacts/golden.json) | Synthetic independent stdlib-calculated canonical bytes, manifest/package digest and UUID vector |

The fixture was constructed before implementation with only stdlib JSON, hashlib,
base64 and UUID operations plus the existing synthetic M1 fixture. No M2 implementation
was imported to calculate it. Tests compare exact bytes and UUIDs rather than generating
expected values with the implementation under test.

The package manifest hashes the entire declared file set: paths, roles, raw-byte sizes
and hashes, mappings, configurations, plan/baseline references and assertion locations.
Every payload must exist exactly once and match its entry; canonical base64 prevents
alternative encodings from weakening identity. The package digest hashes the canonical
manifest, whose entries transitively bind every exact payload byte. Shared helpers,
configurations, lock/runtime descriptors and data all affect the revision. No bytes are
transformed, imported or unpacked. Review and execution authority are absent.

## Decoder correction and implementation choices

V1's requirement to reuse M0's decoder contradicted the approved payload sizes:
16,384 base64 characters carry only 12,288 raw bytes. Preflight reproduced rejection
at 12,289 bytes and 1 MiB before application coding. The user explicitly approved V2.
M0/M1 decoders and their golden vectors remain unchanged.

M2 uses stdlib JSON after an 8 MiB wire check and preparse depth scan. Duplicate keys,
nonfinite values, BOM, malformed UTF-8, lone surrogates and unsupported root forms fail.
The parsed tree retains ordinary 16,384-character text/key limits and a 100000-node cap.
Only exact recognized candidate/package payload records acquire the larger base64 bound;
unknown root keys, malformed record shapes and the same field name elsewhere cannot
grant the exception. Strict models then validate the complete schema.

Base64 length is checked before decoding. Alphabet, padding and projected decoded size
are checked for every payload; the aggregate projected total is checked before any file
is decoded. Actual decoded size and aggregate total are independently checked, and
canonical re-encoding rejects unused-bit variants. The bounds stay 1 MiB/file,
4 MiB decoded aggregate, 8 MiB complete package and 256 files. A candidate at 8 MiB
may fail freeze because the added digest would exceed the complete-package ceiling;
the final package is checked independently.

The simpler stdlib parser avoids a custom streaming JSON grammar. Its trade-off is
that bounded wire text and a parsed object tree coexist before context-sensitive checks;
the node check occurs after JSON allocation. Python callers already own their input
memory. Limits do not claim a fixed peak resident-memory bound. Per-file decoding and
hashing avoid retaining an additional raw-byte bundle; repeated validation favors
integrity over maximum throughput. No performance or concurrent-service claim is made.

One inert JSON file reuses existing exclusive exports and avoids recursive extraction,
partial directory publication or a new artifact store. This costs base64 overhead and
requires a small local bundle. A larger transport needs a new scoped/versioned decision.
M0's host-path checks are accidental-path protection under its single-user trust model,
not a hostile-user filesystem sandbox or race-proof materialization boundary.

## Acceptance evidence

Each AC row maps to one `test_m2_ac_NN_*` method across the two new test modules.
Every row below passed in the full run. The approved specification owns expected
semantics; these are actual tested fixtures, not arbitrary-program correctness proofs.

| Case | Executed evidence |
| --- | --- |
| M2-AC-01 | Real approved M0/M1; exact counts and oracle/source chain; store bytes unchanged; closure unverified, approval/authorization false |
| M2-AC-02 | Independent exact manifest/package canonical vectors and UUID; order-insensitive collections |
| M2-AC-03 | Every file role changes digest on byte edit; logical test ID stable; original retained |
| M2-AC-04 | Binary/empty/Unicode/CRLF/LF round-trip and malformed/noncanonical base64 |
| M2-AC-05 | Missing/extra payloads, hash/size tampering, wrong/dangling role/path references |
| M2-AC-06 | Traversal/absolute/UNC/device/ADS/reserved/invalid paths and case/prefix collisions |
| M2-AC-07 | One criterion, multiple scenarios/tests/configurations with exact explicit pair count |
| M2-AC-08 | Independent logical-ID changes, forged/reassigned/duplicate identities and foreign scenarios |
| M2-AC-09 | Explicit memberships, no inferred cross-product, unused configuration blocker, duplicate/foreign denial |
| M2-AC-10 | Exact dispositions, reason/count rules, criterion/range/duplicate checks and allowed overlap |
| M2-AC-11 | Unsupported/unplanned M1 scope retained, no-tests and unbuilt blockers, zero-scenario M1 remains blocked |
| M2-AC-12 | Pending/rejected/superseded observations, untrusted flags and serialized authority denial; revocation also in AC-13 |
| M2-AC-13 | Real revocation blocks next assessment without changing bytes; unrelated review advances sequence without revoking active baseline |
| M2-AC-14 | Exactly one inspection, malformed/cross-project/wrong-digest/forged effective authority rejected in assess and prepare |
| M2-AC-15 | Revocation after coherent read produces only a staleable observation; next assessment blocks |
| M2-AC-16 | Dynamic imports/missing real tests/fabricated assertion locations remain inert declarations, never closure or authorization |
| M2-AC-17 | Strict fields/version/UUID/Unicode/Boolean input, duplicate JSON keys, immutable tuples and validated copies; literal-false enforcement |
| M2-AC-18 | Count/field limits plus the 12 named decoder/collection regressions described below |
| M2-AC-19 | Real Unicode/space Windows output, no overwrite, forbidden host paths and actual junction; no payload materialization |
| M2-AC-20 | Permission, fsync/publication/stdout-flush failures and interruption; completed output retained on acknowledgment loss |
| M2-AC-21 | Tamper failures and noncanonical JSON revalidation without modifying source |
| M2-AC-22 | Weakened-count/skip/caught-error/empty-loop edits change revision; oracle reference retained and no fidelity claim |
| M2-AC-23 | Missing/future/corrupt/busy/hot-journal store failures; no create/recovery/migration writes |
| M2-AC-24 | Fresh-process write/network/subprocess/store/legacy-import traps; help/version/ID; inert payload sentinel absent from output |
| M2-AC-25 | Offline validate/freeze/assess/revoke/blocked journey, exact CLI exits, forbidden flags and preserved package bytes |
| M2-AC-26 | Pre-M2 tracked non-documentation inventory byte-for-byte unchanged; M0 golden snapshot; all unchanged 78 tests pass |

The 12 additional regressions cover file sizes 12,288/12,289 bytes and 1 MiB minus/
exact/plus one; encoded exact/overflow and same-length decoded overflow; decoder-call
traps proving prechecks; aggregate 4 MiB minus/exact/plus one; exact/over 8 MiB wire,
candidate and complete-package canonical sizes; ordinary keys/strings and contextual
spoofing; depth 32/33, nodes 100000/100001, Unicode/nonfinite/duplicate-key forms;
positive 5000 tests/dispositions, 64 configurations/memberships/assertions, 256 files,
240-character path and over-limit denial; nested ordering and metadata changes;
independent actual decoded-length checks and canonical unused bits. Simultaneous maxima
that exceed node/wire limits correctly reject rather than weakening the aggregate bounds.

## Defects corrected and unchanged acceptance

Two authority-negative cases exposed that a `PlanError` escaped M2's public error
boundary. Small `checked_plan`/`checked_inspection` wrappers and explicit pure-policy
translation now retain safe source/code information as `ArtifactError`, without exposing
raw inspection/user text or changing M1. The same negative cases now pass for both
prepare and inspect. Assessment invariants also explicitly reject a ready record with
zero tests, inconsistent pair counts or blocked M1 state. No expectation, assertion or
approved oracle was weakened; no required case was skipped or removed.

## Operator use, limitations and handoff

Final review covered exactly 18 paths: four implementation modules, two test modules,
one synthetic fixture and 11 documentation/instruction files, including the preserved
preexisting M2 specification changes. All 59 tracked pre-M2 non-documentation files
were byte-for-byte unchanged against the M1 parent. All 50 first-party Python files
parsed with `ast.parse`; 11 changed/new Markdown files, 268 local links and 69 anchors
passed validation. Seven decision sections and all 26 acceptance rows remain present;
existing capability and SC-01 acceptance IDs are preserved. `git diff --check` passed.
Common credential-token/private-key pattern scanning found no matches. No runtime
database, real SRS input, environment file, browser session or generated runtime artifact
is in the reviewed inventory. External references were not network-checked.

A documentation-review helper initially used Windows' default cp1252 to decode a Git
UTF-8 document; the helper was corrected to explicit UTF-8 and all checks reran
successfully. This was a verification-helper issue, not an application defect or a
weakened product assertion. The index was empty before staging the reviewed inventory.

Run `python -B -m app.artifact_cli help` or `version` without legacy configuration.
Prepare a private candidate JSON containing exact `schema_version, manifest, payloads`;
use `test-id --project ... --scenario ... --key ...` for logical identity. Supply the
immutable plan explicitly. `validate --db ... --plan ... --candidate ...` assesses it;
`freeze` with the same arguments plus `--out ...` exports one exclusive canonical file;
`assess --db ... --plan ... --package ...` rereads current authority. No file collection,
directory unpacking, generation, review, install or execution command exists.

Validate/assess exit 0 means ready for review design, 3 means blocked. Freeze can export
a structurally valid blocked proposal and exits 0 with that status explicit. Input
errors exit 2, store/path/integrity/output errors 4, interruption 130. On output failure,
inspect an existing destination rather than overwrite. Store read errors never authorize
write recovery. There is no atomic transaction between authority read, export and stdout.

`closure_status` stays `unverified`; `bundle_approved` and `execution_authorized` stay
literal false. M2 never establishes dependency closure, TypeScript validity, actual test
discovery, semantic assertion preservation, safe execution or target permission. Supplied
runtime/configuration/lock bytes are declarations; matching a real isolated environment
remains future work. A hash is not authentication, secrecy or human approval.

All legacy F01-F17 remain open, including host execution and assertion weakening.
M2-R durable review, M3 reconciliation, M4 budgets/effects and M5 isolation retain their
own scoped gates. [CAPABILITY_REQUIREMENTS](CAPABILITY_REQUIREMENTS.md) and ROADMAP
retain model routing, source-aware diagnosis/workflows, professional UI, public SC-01,
observability/evaluations, Test Lab, POM, extensibility, recovery, data and portability.
None is silently implemented or removed by M2.

The authorized local checkpoint includes the previously uncommitted M2 specification
and related documentation changes after review. Parent is M1 commit
`58c1faef6fb6b96e126e67afa73e6c3af2cce41f`; checkpoint subject is
`feat: implement offline M2 artifact packages and mapping assessment`.
Recover its exact hash with `git log -1 --format="%H %s"` after commit completion;
the containing commit cannot embed its own hash. NEXT_STEPS records the stop boundary.
No push or live remote query is part of this task.
