"""Explicit offline human review CLI; no imported decisions or execution path."""
from __future__ import annotations

import argparse
import json
import re
import sys

from app.baseline_contracts import MAX_INPUT, MAX_SEQUENCE, M0Error
from app.plan_contracts import PlanError
from app.artifact_contracts import ArtifactError
from app.core.baseline_files import read_bounded
from app.core.review_store import ReviewStore
from app.core.package_review_store import PackageReviewStore
from app.core import package_review_service as service
from app.review_contracts import POLICY_VERSION, ReviewCommandV1, ReviewError, translated


class SafeParser(argparse.ArgumentParser):
    def error(self, message):
        raise ReviewError('INVALID_INPUT')


def _sequence(value: str) -> int:
    if not re.fullmatch(r'0|[1-9][0-9]{0,15}', value) or int(value) > MAX_SEQUENCE:
        raise ReviewError('INVALID_INPUT')
    return int(value)


def _parser() -> argparse.ArgumentParser:
    p = SafeParser(description='Offline M2-R exact plan/package reviews', allow_abbrev=False)
    commands = p.add_subparsers(dest='command', required=True)
    for name in ('help', 'version', 'init', 'register-plan', 'register-package', 'review', 'inspect', 'history', 'assess', 'export'):
        c = commands.add_parser(name, allow_abbrev=False)
        if name in ('help', 'version'):
            continue
        c.add_argument('--db', required=True)
        if name in ('init', 'register-plan', 'register-package', 'assess'):
            c.add_argument('--baseline-db', required=True)
        if name == 'init':
            c.add_argument('--project', required=True)
            c.add_argument('--baseline', required=True)
        if name in ('register-plan', 'register-package'):
            c.add_argument('--plan' if name == 'register-plan' else '--package', required=True)
        if name in ('review', 'inspect', 'assess', 'export'):
            c.add_argument('--kind', choices=('plan', 'package'), required=True)
            c.add_argument('--digest', required=True)
        if name == 'review':
            c.add_argument('--decision', choices=('approve', 'reject', 'revoke'), required=True)
            c.add_argument('--request-id', required=True)
            c.add_argument('--expected-sequence', type=_sequence, required=True)
            c.add_argument('--expected-m0-sequence', type=_sequence)
            c.add_argument('--baseline-db')
            c.add_argument('--note')
        if name == 'history':
            c.add_argument('--after', type=_sequence, default=0)
            c.add_argument('--limit', type=_sequence, default=100)
        if name == 'export':
            c.add_argument('--out', required=True)
    return p


def _emit(value: object) -> None:
    if hasattr(value, 'model_dump'):
        value = value.model_dump(mode='json')
    raw = json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(',', ':')) + '\n'
    if len(raw.encode('ascii')) > MAX_INPUT:
        raise ReviewError('LIMIT_EXCEEDED')
    sys.stdout.write(raw)
    sys.stdout.flush()


def _report(error: ReviewError) -> None:
    try:
        sys.stderr.write(json.dumps(error.as_dict(), ensure_ascii=True, separators=(',', ':')) + '\n')
        sys.stderr.flush()
    except (OSError, ValueError, UnicodeError):
        pass  # Exit remains failure even when the error stream cannot be written.


def _exit(error: ReviewError) -> int:
    conflicts = {'STALE_SEQUENCE', 'STALE_AUTHORITY', 'REQUEST_ID_CONFLICT', 'NOT_APPROVABLE',
                 'PARENT_NOT_REVIEWED', 'INVALID_TRANSITION', 'SEQUENCE_EXHAUSTED',
                 'LOCAL_CONTEXT_REQUIRED', 'UNKNOWN_SUBJECT', 'INVALID_INPUT', 'UNKNOWN_FIELD',
                 'UNSUPPORTED_VERSION', 'LIMIT_EXCEEDED', 'INVALID_REFERENCE', 'DUPLICATE_ID'}
    return 2 if error.source == 'm2r' and error.code in conflicts else 4


def main(argv: list[str] | None = None) -> int:
    acknowledged = False
    try:
        parser = _parser()
        args = parser.parse_args(argv)
        if args.command == 'help':
            parser.print_help()
            return 0
        if args.command == 'version':
            _emit(dict(schema_version=1, policy_version=POLICY_VERSION))
            return 0
        store = PackageReviewStore(args.db)
        if args.command == 'init':
            result = service.initialize(store, ReviewStore(args.baseline_db), args.project, args.baseline)
        elif args.command == 'register-plan':
            result = service.register_plan(store, ReviewStore(args.baseline_db), read_bounded(args.plan))
        elif args.command == 'register-package':
            result = service.register_package(store, ReviewStore(args.baseline_db), read_bounded(args.package))
        elif args.command == 'review':
            approve = args.decision == 'approve'
            if approve != (args.baseline_db is not None) or approve != (args.expected_m0_sequence is not None):
                raise ReviewError('INVALID_INPUT')
            context = store.local_context()
            command = ReviewCommandV1(schema_version=1, project_id=context.project_id, kind=args.kind,
                subject_digest=args.digest, request_id=args.request_id, expected_sequence=args.expected_sequence,
                expected_m0_sequence=args.expected_m0_sequence, decision=args.decision, note=args.note)
            result = service.record_review(store, command, context, ReviewStore(args.baseline_db) if approve else None)
            acknowledged = True
        elif args.command == 'inspect':
            result = store.inspect_subject(args.kind, args.digest)
        elif args.command == 'history':
            result = store.inspect_history(args.after, args.limit)
        elif args.command == 'export':
            service.export_subject(store, args.kind, args.digest, args.out)
            result = dict(schema_version=1, exported=True)
        else:
            method = service.assess_plan_review if args.kind == 'plan' else service.assess_package_review
            result = method(store, ReviewStore(args.baseline_db), args.digest)
        _emit(result)
        return 3 if args.command == 'assess' and result.disposition == 'blocked' else 0
    except SystemExit as exc:
        return int(exc.code)
    except (M0Error, PlanError, ArtifactError) as exc:
        error = translated(exc)
        _report(error)
        return 130 if error.interrupted else _exit(error)
    except ReviewError as error:
        if acknowledged and error.code == 'OUTPUT_FAILURE':
            error = ReviewError('COMMIT_OUTCOME_UNKNOWN')
        _report(error)
        return 130 if error.interrupted else _exit(error)
    except (OSError, ValueError, UnicodeError):
        _report(ReviewError('COMMIT_OUTCOME_UNKNOWN' if acknowledged else 'OUTPUT_FAILURE'))
        return 4
    except KeyboardInterrupt:
        _report(ReviewError('COMMIT_OUTCOME_UNKNOWN' if acknowledged else 'OUTPUT_FAILURE'))
        return 130


if __name__ == '__main__':
    raise SystemExit(main())
