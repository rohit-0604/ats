"""Separate, offline artifact CLI. It neither loads nor materializes payload code."""
from __future__ import annotations

import argparse
import json
import sys

from app.baseline_contracts import M0Error
from app.plan_contracts import PlanError, parse_plan
from app.core.baseline_files import read_bounded, write_export
from app.core.review_store import ReviewStore
from app.artifact_contracts import (
    POLICY_VERSION, ArtifactError, canonical_artifact_bytes, parse_artifact_package, test_id,
)
from app.core.artifact_service import inspect_artifact, prepare_artifact


class SafeParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise ArtifactError('INVALID_INPUT')


def _parser() -> argparse.ArgumentParser:
    parser = SafeParser(description='Offline M2 immutable artifact packages', allow_abbrev=False)
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('help', allow_abbrev=False)
    commands.add_parser('version', allow_abbrev=False)
    identity = commands.add_parser('test-id', allow_abbrev=False)
    for name in ('project', 'scenario', 'key'):
        identity.add_argument('--'+name, required=True)
    for name in ('validate', 'freeze', 'assess'):
        command = commands.add_parser(name, allow_abbrev=False)
        for field in ('db', 'plan', 'package' if name == 'assess' else 'candidate'):
            command.add_argument('--'+field, required=True)
        if name == 'freeze':
            command.add_argument('--out', required=True)
    return parser


def _emit(value: object) -> None:
    if hasattr(value, 'model_dump'):
        value = value.model_dump(mode='json')
    try:
        sys.stdout.write(json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(',', ':'))+'\n')
        sys.stdout.flush()
    except (OSError, ValueError, UnicodeError):
        raise ArtifactError('OUTPUT_FAILURE') from None


def _report(error: ArtifactError) -> None:
    try:
        sys.stderr.write(json.dumps(error.as_dict(), ensure_ascii=True, separators=(',', ':'))+'\n')
        sys.stderr.flush()
    except (OSError, ValueError, UnicodeError):
        return  # The exit status remains failure if stderr is unavailable.


def _read(path: str) -> bytes:
    try:
        return read_bounded(path)
    except M0Error as exc:
        if exc.code == 'LIMIT_EXCEEDED':
            raise ArtifactError('LIMIT_EXCEEDED') from None
        raise


def main(argv: list[str] | None = None) -> int:
    try:
        parser = _parser()
        args = parser.parse_args(argv)
        if args.command == 'help':
            parser.print_help()
            return 0
        if args.command == 'version':
            _emit(dict(schema_version=1, policy_version=POLICY_VERSION))
            return 0
        if args.command == 'test-id':
            _emit(dict(schema_version=1, test_id=test_id(args.project, args.scenario, args.key)))
            return 0
        plan = parse_plan(_read(args.plan))
        if args.command == 'assess':
            package = parse_artifact_package(_read(args.package))
            result = inspect_artifact(ReviewStore(args.db), package, plan)
            _emit(result)
            return 0 if result.disposition == 'ready_for_review_design' else 3
        package, result = prepare_artifact(ReviewStore(args.db), _read(args.candidate), plan)
        if args.command == 'freeze':
            write_export(args.out, canonical_artifact_bytes(package))
            _emit(dict(schema_version=1, package_digest=package.digest, assessment=result.model_dump(mode='json')))
            return 0
        _emit(dict(schema_version=1, structurally_valid=True, assessment=result.model_dump(mode='json')))
        return 0 if result.disposition == 'ready_for_review_design' else 3
    except SystemExit as exc:
        return int(exc.code)
    except ArtifactError as exc:
        _report(exc)
        return 4 if exc.source == 'm0' or exc.code in ('INTEGRITY_ERROR', 'AUTHORITY_MISMATCH', 'OUTPUT_FAILURE', 'PATH_POLICY') else 2
    except PlanError as exc:
        _report(ArtifactError(exc.code, source=exc.source))
        return 4 if exc.source == 'm0' or exc.code in ('PLAN_DIGEST_MISMATCH', 'AUTHORITY_MISMATCH', 'OUTPUT_FAILURE') else 2
    except M0Error as exc:
        _report(ArtifactError(exc.code, source='m0'))
        return 4
    except OSError:
        _report(ArtifactError('OUTPUT_FAILURE'))
        return 4
    except KeyboardInterrupt:
        _report(ArtifactError('OUTPUT_FAILURE'))
        return 130


if __name__ == '__main__':
    raise SystemExit(main())
