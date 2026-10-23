"""Offline M0 CLI: python -B -m app.baseline_cli. No legacy runtime bootstrap."""
from __future__ import annotations
import argparse
import json
import re
import sys
from uuid import uuid4
from app.baseline_contracts import (
    M0Error, ReviewCommandV1, ValidationReportV1, _uuid,
    canonical_bytes, validate_model,
)
from app.core.baseline_files import read_bounded, validate_path, write_export
from app.core.baseline_review import approval_blockers, freeze_baseline, import_legacy_bundle, validate_draft
from app.core.review_store import ReviewStore
def _emit(value):
    if hasattr(value, 'model_dump'):
        value=value.model_dump(mode='json')
    sys.stdout.write(json.dumps(value,ensure_ascii=True,sort_keys=True,separators=(',',':'))+'\n')
    sys.stdout.flush()
class SafeParser(argparse.ArgumentParser):
    def error(self, message):
        raise M0Error('INVALID_INPUT')
def _parser():
    parser=SafeParser(description='Offline M0 baseline and review records')
    sub=parser.add_subparsers(dest='command',required=True)
    for name in ('version','new-id'):
        sub.add_parser(name)
    init=sub.add_parser('init-store')
    init.add_argument('--db',required=True)
    project=sub.add_parser('create-project')
    project.add_argument('--db',required=True)
    project.add_argument('--project',required=True)
    project.add_argument('--reviewer',required=True)
    prepare=sub.add_parser('prepare')
    for name in ('input','project','source-key','out'):
        prepare.add_argument('--'+name,required=True)
    validate=sub.add_parser('validate')
    validate.add_argument('--draft',required=True)
    freeze=sub.add_parser('freeze')
    freeze.add_argument('--db',required=True)
    freeze.add_argument('--draft',required=True)
    review=sub.add_parser('review')
    for name in ('db','project','digest','decision','request-id','reason'):
        review.add_argument('--'+name,required=True)
    review.add_argument('--expected-sequence',type=int,required=True)
    inspect=sub.add_parser('inspect')
    for name in ('db','project','digest'):
        inspect.add_argument('--'+name,required=True)
    history=sub.add_parser('history')
    history.add_argument('--db',required=True)
    history.add_argument('--project',required=True)
    history.add_argument('--after-sequence',type=int,default=0)
    history.add_argument('--limit',type=int,default=100)
    return parser
def _exit_code(code):
    if code in ('INVALID_INPUT','UNKNOWN_FIELD','UNSUPPORTED_VERSION','LIMIT_EXCEEDED','DUPLICATE_ID','INVALID_REFERENCE'):
        return 2
    if code in ('PROJECT_EXISTS','UNKNOWN_PROJECT','UNKNOWN_SUBJECT','PROJECT_MISMATCH','NOT_APPROVABLE','INVALID_TRANSITION','LINEAGE_CONFLICT','PARENT_ID_LOSS','STALE_SEQUENCE','REQUEST_ID_CONFLICT','SEQUENCE_EXHAUSTED'):
        return 3
    return 4
def main(argv: list[str] | None=None) -> int:
    review_completed=False
    try:
        args=_parser().parse_args(argv)
        if hasattr(args,'project'):
            _uuid(args.project)
        if hasattr(args,'digest') and not re.fullmatch(r'sha256:[0-9a-f]{64}',args.digest):
            raise M0Error('INVALID_INPUT')
        if args.command=='version':
            result={'schema_version':1,'store_version':1}
        elif args.command=='new-id':
            result={'schema_version':1,'id':str(uuid4())}
        elif args.command=='init-store':
            ReviewStore.initialize(args.db)
            result={'schema_version':1,'initialized':True}
        elif args.command=='create-project':
            result=ReviewStore(args.db).create_project(args.project,args.reviewer)
        elif args.command=='prepare':
            imported=import_legacy_bundle(read_bounded(args.input,4*1024*1024),args.project,args.source_key)
            write_export(args.out,canonical_bytes(imported))
            result={'schema_version':1,'prepared':True}
        elif args.command=='validate':
            value=validate_draft(read_bounded(args.draft))
            blockers=approval_blockers(value)
            result=ValidationReportV1(schema_version=1,structurally_valid=True,errors=(),approval_blockers=blockers,store_checks='not_performed')
            _emit(result)
            return 2 if blockers else 0
        elif args.command=='freeze':
            snapshot=freeze_baseline(validate_draft(read_bounded(args.draft)))
            result=ReviewStore(args.db).store_snapshot(snapshot)
        elif args.command=='review':
            command=validate_model(ReviewCommandV1,dict(schema_version=1,project_id=args.project,subject_digest=args.digest,
                decision=args.decision,expected_sequence=args.expected_sequence,request_id=args.request_id,reason=args.reason))
            store=ReviewStore(args.db)
            result=store.record_review(command,store.local_context(args.project))
            review_completed=True
        elif args.command=='inspect':
            result=ReviewStore(args.db).inspect(args.project,args.digest)
        else:
            result=ReviewStore(args.db).history(args.project,args.after_sequence,args.limit)
        _emit(result)
        return 0
    except SystemExit as exc:
        return int(exc.code)
    except M0Error as exc:
        sys.stderr.write(json.dumps(exc.as_dict(),ensure_ascii=True,separators=(',',':'))+'\n')
        return _exit_code(exc.code)
    except OSError:
        code='COMMIT_OUTCOME_UNKNOWN' if review_completed else 'OUTPUT_FAILURE'
        try:
            sys.stderr.write(json.dumps(M0Error(code).as_dict())+'\n')
        except OSError:
            pass
        return 4
    except KeyboardInterrupt:
        try:
            sys.stderr.write(json.dumps({'code':'STORE_FAILURE','pointer':'','message':'Command interrupted; reconcile original request identity'})+'\n')
        except OSError:
            pass
        return 130
if __name__=='__main__':
    raise SystemExit(main())
