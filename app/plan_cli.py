"""Separate offline M1 CLI: python -B -m app.plan_cli. No legacy bootstrap."""
from __future__ import annotations

import argparse
import json
import sys

from app.baseline_contracts import M0Error
from app.core.baseline_files import read_bounded, write_export
from app.core.review_store import ReviewStore
from app.core.plan_service import inspect_plan, prepare_plan
from app.plan_contracts import (
    POLICY_VERSION, PlanError, canonical_plan_bytes, parse_plan, parse_plan_draft, scenario_id,
)


class SafeParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise PlanError('INVALID_INPUT')


def _parser() -> argparse.ArgumentParser:
    parser = SafeParser(description='Offline M1 authority-bound scenario plans', allow_abbrev=False)
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('version', allow_abbrev=False)
    identity = commands.add_parser('scenario-id', allow_abbrev=False)
    for name in ('project', 'criterion', 'key'):
        identity.add_argument('--' + name, required=True)
    for name in ('validate', 'freeze', 'assess'):
        command = commands.add_parser(name, allow_abbrev=False)
        command.add_argument('--db', required=True)
        command.add_argument('--plan' if name == 'assess' else '--draft', required=True)
        if name == 'freeze':
            command.add_argument('--out', required=True)
    return parser


def _emit(value: object) -> None:
    if hasattr(value, 'model_dump'):
        value = value.model_dump(mode='json')
    try:
        sys.stdout.write(json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(',', ':')) + '\n')
        sys.stdout.flush()
    except (OSError, ValueError, UnicodeError):
        raise PlanError('OUTPUT_FAILURE') from None


def _report(error: PlanError) -> None:
    try:
        sys.stderr.write(json.dumps(error.as_dict(), ensure_ascii=True, separators=(',', ':')) + '\n')
        sys.stderr.flush()
    except (OSError, ValueError, UnicodeError):
        return  # Exit status still reports failure when stderr itself is unavailable.


def _read(path: str) -> bytes:
    try:
        return read_bounded(path)
    except M0Error as exc:
        if exc.code == 'LIMIT_EXCEEDED':
            raise PlanError('LIMIT_EXCEEDED') from None
        raise


def main(argv: list[str] | None = None) -> int:
    try:
        args = _parser().parse_args(argv)
        if args.command == 'version':
            _emit(dict(schema_version=1, policy_version=POLICY_VERSION))
            return 0
        if args.command == 'scenario-id':
            _emit(dict(schema_version=1, scenario_id=scenario_id(args.project, args.criterion, args.key)))
            return 0
        if args.command == 'assess':
            plan = parse_plan(_read(args.plan))
            assessment = inspect_plan(ReviewStore(args.db), plan)
            _emit(assessment)
            return 0 if assessment.disposition == 'ready_for_artifact_design' else 3
        draft = parse_plan_draft(_read(args.draft))
        plan, assessment = prepare_plan(ReviewStore(args.db), draft)
        if args.command == 'freeze':
            write_export(args.out, canonical_plan_bytes(plan))
            _emit(dict(schema_version=1, plan_digest=plan.digest, assessment=assessment.model_dump(mode='json')))
            return 0
        _emit(dict(schema_version=1, structurally_valid=True, assessment=assessment.model_dump(mode='json')))
        return 0 if assessment.disposition == 'ready_for_artifact_design' else 3
    except SystemExit as exc:
        return int(exc.code)
    except PlanError as exc:
        _report(exc)
        return 4 if exc.source == 'm0' or exc.code in ('AUTHORITY_MISMATCH', 'OUTPUT_FAILURE') else 2
    except M0Error as exc:
        _report(PlanError(exc.code, source='m0'))
        return 4
    except OSError:
        _report(PlanError('OUTPUT_FAILURE'))
        return 4
    except KeyboardInterrupt:
        error = PlanError('OUTPUT_FAILURE')
        error.message = 'Command interrupted; output may already exist'
        _report(error)
        return 130


if __name__ == '__main__':
    raise SystemExit(main())
