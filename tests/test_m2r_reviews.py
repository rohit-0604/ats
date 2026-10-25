"""M2-R offline acceptance: synthetic stores, inert payloads, real M0 authority."""
from __future__ import annotations

import contextlib
import io
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from unittest.mock import patch, PropertyMock
from uuid import uuid4

import test_m0_acceptance as m0
from test_m2_artifacts import M2Harness, wire, replace_payload
from app.baseline_contracts import MAX_SEQUENCE, canonical_bytes
from app.plan_contracts import canonical_plan_bytes
from app.artifact_contracts import canonical_artifact_bytes
from app.core.review_store import ReviewStore
from app.core.package_review_store import PackageReviewStore, LocalReviewContext, ReviewSnapshot
from app.core import package_review_service as service
from app.review_contracts import (
    ReviewError, ReviewCommandV1, ReviewDecisionV1, ReviewSubjectV1,
    StoredReviewSubjectV1, PlanReviewAssessmentV1, PackageReviewAssessmentV1,
    canonical_review_bytes, parse_review_command,
)
from app.review_cli import main


def cli(*args):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = main(list(args))
    return code, out.getvalue(), err.getvalue()


class ReviewAcceptance(M2Harness):
    def setUp(self):
        super().setUp()
        self.planv = self.plan()
        self.packagev = self.package(plan=self.planv)
        self.rdb = self.root / 'packages.sqlite3'
        self.reviews = PackageReviewStore(self.rdb)
        service.initialize(self.reviews, self.store, m0.PROJECT, self.snapshot.digest)
        service.register_plan(self.reviews, self.store, canonical_plan_bytes(self.planv))
        service.register_package(self.reviews, self.store, canonical_artifact_bytes(self.packagev))

    def cmd(self, kind='plan', action='approve', **changes):
        data = dict(schema_version=1, project_id=m0.PROJECT, kind=kind,
            subject_digest=self.planv.digest if kind == 'plan' else self.packagev.digest,
            request_id=str(uuid4()), expected_sequence=self.reviews.snapshot().sequence,
            expected_m0_sequence=self.store.inspect(m0.PROJECT, self.snapshot.digest).review.project_sequence if action == 'approve' else None,
            decision=action, note='Synthetic human review')
        data.update(changes)
        return ReviewCommandV1(**data)

    def decide(self, kind='plan', action='approve', **changes):
        return service.record_review(self.reviews, self.cmd(kind, action, **changes),
                                     self.reviews.local_context(), self.store if action == 'approve' else None)

    def assess(self):
        return service.assess_package_review(self.reviews, self.store, self.packagev.digest)

    def effective(self):
        self.decide()
        self.decide('package')
        self.assertTrue(self.assess().package_review_effective)

    def error(self, code, fn, *args, **kwargs):
        with self.assertRaises(ReviewError) as caught:
            fn(*args, **kwargs)
        self.assertEqual(code, caught.exception.code)
        return caught.exception

    def test_m2r_ac_01_initialization_and_reopen(self):
        before = self.db.read_bytes()
        p = self.root / 'second.sqlite3'
        new = PackageReviewStore(p)
        self.assertFalse(p.exists())
        metadata = service.initialize(new, self.store, m0.PROJECT, self.snapshot.digest)
        self.assertEqual(self.store.inspect(m0.PROJECT, self.snapshot.digest).project, metadata.project)
        self.assertEqual(metadata, PackageReviewStore(p).snapshot().metadata)
        self.assertEqual(0, new.snapshot().sequence)
        self.assertEqual(before, self.db.read_bytes())

    def test_m2r_ac_02_refuse_existing_foreign_and_alias(self):
        before = self.db.read_bytes()
        self.error('STORE_EXISTS', service.initialize, self.reviews, self.store, m0.PROJECT, self.snapshot.digest)
        self.error('STORE_IDENTITY_MISMATCH', service.initialize, PackageReviewStore(self.db), self.store, m0.PROJECT, self.snapshot.digest)
        self.error('STORE_IDENTITY_MISMATCH', PackageReviewStore(self.db).snapshot)
        alias = self.root / 'alias.sqlite3'
        os.link(self.db, alias)
        self.error('STORE_IDENTITY_MISMATCH', service.initialize, PackageReviewStore(alias), self.store, m0.PROJECT, self.snapshot.digest)
        self.assertEqual(before, self.db.read_bytes())

    def test_m2r_ac_03_plan_custody_and_inactive_registration(self):
        self.assertEqual(canonical_plan_bytes(self.planv), self.reviews.export_subject('plan', self.planv.digest))
        self.assertEqual(self.planv.baseline_digest, self.reviews.snapshot().subject('plan', self.planv.digest).subject.baseline_digest)
        successor = self.successor(approve=False)
        plan = self.plan(self.plan_data(successor), successor)
        service.register_plan(self.reviews, self.store, canonical_plan_bytes(plan))
        a = service.assess_plan_review(self.reviews, self.store, plan.digest)
        self.assertEqual('pending', a.raw_status)
        self.assertIn('BASELINE_NOT_ACTIVE', a.blockers)
        self.assertFalse(a.plan_review_effective)

    def test_m2r_ac_04_package_custody_and_invalid_parent(self):
        raw = canonical_artifact_bytes(self.packagev)
        self.assertEqual(raw, self.reviews.export_subject('package', self.packagev.digest))
        other = self.root / 'empty.sqlite3'
        rs = PackageReviewStore(other)
        service.initialize(rs, self.store, m0.PROJECT, self.snapshot.digest)
        self.error('UNKNOWN_SUBJECT', service.register_package, rs, self.store, raw)
        data = json.loads(raw); data['manifest']['plan_digest'] = 'sha256:' + 'f' * 64
        self.error('INTEGRITY_ERROR', service.register_package, self.reviews, self.store, wire(data))

    def test_m2r_ac_05_idempotent_registration_without_review(self):
        before = self.rdb.read_bytes()
        plan = service.register_plan(self.reviews, self.store, json.dumps(self.planv.model_dump(mode='json'), indent=2).encode())
        package = service.register_package(self.reviews, self.store, canonical_artifact_bytes(self.packagev))
        self.assertFalse(plan.created); self.assertFalse(package.created)
        self.assertEqual(0, self.reviews.snapshot().sequence)
        self.assertEqual(before, self.rdb.read_bytes())
        self.assertFalse(self.assess().package_review_effective)

    def test_m2r_ac_06_explicit_trusted_context(self):
        command = self.cmd()
        context = self.reviews.local_context()
        for forged in (context.__dict__, None, LocalReviewContext(m0.PROJECT, str(uuid4()), context.reviewer_label)):
            self.error('LOCAL_CONTEXT_REQUIRED', service.record_review, self.reviews, command, forged, self.store)
        decision = service.record_review(self.reviews, command, context, self.store)
        self.assertEqual((1, 'human operator', 1), (decision.sequence, decision.reviewer_label, decision.baseline_approval_sequence))
        self.assertTrue(service.assess_plan_review(self.reviews, self.store, self.planv.digest).plan_review_effective)
        data = command.model_dump(); data['approved'] = True
        self.error('UNKNOWN_FIELD', ReviewCommandV1.model_validate, data)

    def test_m2r_ac_07_stale_inactive_and_foreign_authority(self):
        self.error('STALE_AUTHORITY', service.record_review, self.reviews, self.cmd(expected_m0_sequence=0), self.reviews.local_context(), self.store)
        self.review(self.snapshot, 'revoke')
        self.error('NOT_APPROVABLE', self.decide)
        self.assertEqual(0, self.reviews.snapshot().sequence)

    def test_m2r_ac_08_package_requires_parent_and_ready_mapping(self):
        self.error('PARENT_NOT_REVIEWED', self.decide, 'package')
        self.decide()
        data = self.candidate_data(self.planv)
        data['manifest']['tests'] = []
        data['manifest']['files'] = [f for f in data['manifest']['files'] if f['role'] != 'spec']
        paths = {f['path'] for f in data['manifest']['files']}
        data['payloads'] = [p for p in data['payloads'] if p['path'] in paths]
        data['manifest']['scenario_dispositions'][0].update(status='unbuilt', reason='Not automated')
        package = self.package(data, self.planv)
        service.register_package(self.reviews, self.store, canonical_artifact_bytes(package))
        self.error('NOT_APPROVABLE', self.decide, 'package', subject_digest=package.digest)
        a = service.assess_package_review(self.reviews, self.store, package.digest)
        self.assertIn('PACKAGE_STRUCTURALLY_BLOCKED', a.blockers)
        self.assertEqual(1, a.artifact_assessment.unbuilt_scenario_count)

    def test_m2r_ac_09_transition_matrix(self):
        self.error('INVALID_TRANSITION', self.decide, 'plan', 'revoke')
        self.decide('plan', 'reject'); self.decide('plan', 'reject')
        self.decide('plan'); self.decide('plan')
        self.error('INVALID_TRANSITION', self.decide, 'plan', 'reject')
        self.decide('plan', 'revoke')
        self.error('INVALID_TRANSITION', self.decide, 'plan', 'revoke')
        self.decide('plan', 'reject'); self.decide('plan')
        self.assertEqual(7, self.reviews.snapshot().sequence)

    def test_m2r_ac_10_exact_ack_replay_after_revocation(self):
        command = self.cmd(); context = self.reviews.local_context()
        original = service.record_review(self.reviews, command, context, self.store)
        self.decide('plan', 'revoke')
        self.review(self.snapshot, 'revoke')
        self.assertEqual(original, service.record_review(self.reviews, command, context))
        self.error('REQUEST_ID_CONFLICT', service.record_review, self.reviews,
                   command.model_copy(update={'note': 'Different'}), context)
        self.assertEqual(2, self.reviews.snapshot().sequence)
        self.assertFalse(service.assess_plan_review(self.reviews, self.store, self.planv.digest).plan_review_effective)

    def test_m2r_ac_11_stale_competing_writers_and_sequences(self):
        a, b = self.cmd(), self.cmd()
        context = self.reviews.local_context()
        other = PackageReviewStore(self.rdb)
        service.record_review(self.reviews, a, context, self.store)
        self.error('STALE_SEQUENCE', service.record_review, other, b, context, self.store)
        self.assertEqual(1, len(other.inspect_history().decisions))
        for n in (-1, True, MAX_SEQUENCE + 1, '0'):
            self.error('INVALID_INPUT', self.cmd, expected_sequence=n)

    def test_m2r_ac_12_revocation_retains_child_history(self):
        self.effective()
        before = self.reviews.export_subject('package', self.packagev.digest)
        self.decide('plan', 'revoke')
        a = self.assess()
        self.assertEqual('approved', a.raw_status)
        self.assertFalse(a.package_review_effective)
        self.assertEqual(2, a.latest_decision_sequence)
        self.assertEqual(before, self.reviews.export_subject('package', self.packagev.digest))

    def test_m2r_ac_13_reapproval_requires_fresh_parent_token(self):
        self.effective()
        self.decide('plan', 'revoke'); self.decide('plan')
        self.assertIn('PARENT_PLAN_APPROVAL_CHANGED', self.assess().blockers)
        self.decide('package')
        self.assertTrue(self.assess().package_review_effective)
        self.decide('plan')
        self.assertFalse(self.assess().package_review_effective)
        self.assertEqual(4, self.assess().parent_plan_approval_sequence)

    def test_m2r_ac_14_exact_subject_no_implicit_heads(self):
        self.effective()
        data = self.plan_data(); data['scenarios'][0]['title'] += ' revised'
        plan = self.plan(data)
        service.register_plan(self.reviews, self.store, canonical_plan_bytes(plan))
        self.assertTrue(self.assess().package_review_effective)
        self.assertFalse(service.assess_plan_review(self.reviews, self.store, plan.digest).plan_review_effective)
        self.decide('package', 'revoke')
        self.assertFalse(self.assess().package_review_effective)
        self.assertTrue(self.assess().plan_review_effective)

    def test_m2r_ac_15_baseline_supersession_and_unrelated_sequence(self):
        self.effective()
        child = self.successor(approve=False); self.review(child, 'reject')
        self.assertTrue(self.assess().package_review_effective)
        self.assertEqual(2, self.assess().baseline_review.project_sequence)
        self.successor(lambda data: data['criteria'][0].update(expected_outcome='A distinct approved successor.'))
        self.assertIn('BASELINE_NOT_ACTIVE', self.assess().blockers)
        self.assertFalse(self.assess().package_review_effective)

    def test_m2r_ac_16_fresh_false_execution_envelope(self):
        self.effective()
        a = self.assess()
        self.assertEqual(2, a.review_sequence)
        self.assertIs(False, a.execution_authorized)
        self.assertIs(False, a.artifact_assessment.bundle_approved)
        self.assertIs(False, a.plan_review.plan_assessment.plan_approved)
        for field in ('execution_authorized',):
            for value in (True, 0, 'false'):
                self.error('INVALID_INPUT', a.model_copy, update={field: value})
        self.error('INVALID_INPUT', a.model_copy, update={'package_review_effective': False})

    def test_m2r_ac_17_cross_store_observation_is_not_dispatch(self):
        command = self.cmd(); original = self.store.inspect
        def read_then_revoke(*args):
            observation = original(*args)
            self.store.record_review(m0.command(self.snapshot, 'revoke', observation.review.project_sequence),
                                     self.store.local_context(m0.PROJECT))
            return observation
        with patch.object(self.store, 'inspect', side_effect=read_then_revoke):
            decision = service.record_review(self.reviews, command, self.reviews.local_context(), self.store)
        self.assertEqual('approve', decision.decision)
        a = service.assess_plan_review(self.reviews, self.store, self.planv.digest)
        self.assertFalse(a.plan_review_effective)
        self.assertIs(False, a.execution_authorized)

    def test_m2r_ac_18_revocation_and_replay_without_m0(self):
        command = self.cmd(); context = self.reviews.local_context()
        d = service.record_review(self.reviews, command, context, self.store)
        with patch.object(self.store, 'inspect', side_effect=AssertionError('M0 access forbidden')):
            self.assertEqual(d, service.record_review(self.reviews, command, context))
            service.record_review(self.reviews, self.cmd('plan', 'revoke'), context)
        self.error('INVALID_INPUT', service.record_review, self.reviews, self.cmd(), context)

    def test_m2r_ac_19_history_cursor_and_bounds(self):
        self.decide(); self.decide('package'); self.decide('plan')
        a = self.reviews.inspect_history(limit=2)
        b = self.reviews.inspect_history(a.next_after_sequence, 2)
        self.assertEqual([1, 2, 3], [d.sequence for d in a.decisions + b.decisions])
        self.assertIsNone(b.next_after_sequence)
        for after, limit in ((-1, 1), (True, 2), (0, 0), (0, 1001)):
            self.error('INVALID_INPUT', self.reviews.inspect_history, after, limit)

    def test_m2r_ac_20_untrusted_wire_and_python_boundaries(self):
        valid = self.cmd().model_dump(mode='json')
        for edit, code in (({'schema_version': 2}, 'UNSUPPORTED_VERSION'), ({'unknown': 'PRIVATE_SENTINEL'}, 'UNKNOWN_FIELD'),
                           ({'note': 'x' * 2049}, 'LIMIT_EXCEEDED'), ({'project_id': 'PRIVATE_SENTINEL'}, 'INVALID_INPUT')):
            self.error(code, parse_review_command, wire(dict(valid, **edit)))
        for raw in (b'{"a":1,"a":2}', b'{"a":NaN}', b'\xff', b'[' * 33 + b']' * 33):
            self.assertRaises(ReviewError, parse_review_command, raw)
        self.error('LIMIT_EXCEEDED', parse_review_command, b' ' * 65537)

    def test_m2r_ac_21_independent_canonical_and_corrupt_store(self):
        command = self.cmd()
        expected = json.dumps(command.model_dump(mode='json'), ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()
        self.assertEqual(expected, canonical_review_bytes(command))
        stored = self.reviews.snapshot().subject('plan', self.planv.digest)
        self.error('SUBJECT_CONFLICT', stored.model_copy, update={'subject': stored.subject.model_copy(update={'baseline_digest': 'sha256:' + 'a' * 64})})
        self.decide()
        with contextlib.closing(sqlite3.connect(self.rdb)) as con:
            con.execute('DROP TRIGGER decisions_no_update')
            con.commit()
        self.error('INTEGRITY_ERROR', self.reviews.snapshot)

    def test_m2r_ac_22_transaction_rollback_and_unknown_commit(self):
        command = self.cmd(); context = self.reviews.local_context()
        def before(stage):
            if stage == 'decision_inserted': raise OSError('PRIVATE_SENTINEL')
        with patch.object(self.reviews, '_checkpoint', side_effect=before):
            self.error('STORE_FAILURE', service.record_review, self.reviews, command, context, self.store)
        self.assertEqual(0, self.reviews.snapshot().sequence)
        def after(stage):
            if stage == 'committed': raise OSError('PRIVATE_SENTINEL')
        with patch.object(self.reviews, '_checkpoint', side_effect=after):
            self.error('COMMIT_OUTCOME_UNKNOWN', service.record_review, self.reviews, command, context, self.store)
        replay = service.record_review(self.reviews, command, context)
        self.assertEqual(1, replay.sequence)
        self.assertEqual(1, self.reviews.snapshot().sequence)

    def test_m2r_ac_23_schema_journal_and_sql_errors(self):
        self.assertEqual('STORE_BUSY', self.reviews._sql_error(sqlite3.OperationalError('database locked'), True).code)
        self.assertEqual('STORE_FAILURE', self.reviews._sql_error(sqlite3.OperationalError('database or disk is full'), True).code)
        self.assertEqual('INTEGRITY_ERROR', self.reviews._sql_error(sqlite3.DatabaseError('not a database'), False).code)
        with contextlib.closing(sqlite3.connect(self.rdb)) as con:
            con.execute('PRAGMA user_version=2')
        self.error('UNSUPPORTED_VERSION', self.reviews.snapshot)

    def test_m2r_ac_24_export_and_path_denials(self):
        p = self.root / 'frozen.json'
        service.export_subject(self.reviews, 'package', self.packagev.digest, p)
        expected = canonical_artifact_bytes(self.packagev)
        self.assertEqual(expected, p.read_bytes())
        self.error('OUTPUT_FAILURE', service.export_subject, self.reviews, 'package', self.packagev.digest, p)
        self.assertEqual(expected, p.read_bytes())
        for path in ('//server/share/review.sqlite3', 'NUL.sqlite3', 'C:relative.sqlite3'):
            self.assertRaises(ReviewError, service.export_subject, self.reviews, 'plan', self.planv.digest, path)

    def test_m2r_ac_25_safe_output_and_post_commit_failure(self):
        command = self.cmd(note='PRIVATE_SENTINEL\n<script>')
        args = self.review_args(command)
        class Broken(io.StringIO):
            def write(self, text): raise OSError('PRIVATE_SENTINEL')
        err = io.StringIO()
        with contextlib.redirect_stdout(Broken()), contextlib.redirect_stderr(err):
            self.assertEqual(4, main(args))
        self.assertEqual('COMMIT_OUTCOME_UNKNOWN', json.loads(err.getvalue())['code'])
        self.assertNotIn('PRIVATE_SENTINEL', err.getvalue())
        self.assertEqual(1, self.reviews.snapshot().sequence)
        code, out, error = cli(*args)
        self.assertEqual(0, code, error)
        self.assertIn('\\n', out)
        self.assertEqual(command.note, json.loads(out)['note'])

    def review_args(self, command):
        args = ['review', '--db', str(self.rdb), '--kind', command.kind, '--digest', command.subject_digest,
                '--decision', command.decision, '--request-id', command.request_id,
                '--expected-sequence', str(command.expected_sequence)]
        if command.decision == 'approve':
            args += ['--baseline-db', str(self.db), '--expected-m0-sequence', str(command.expected_m0_sequence)]
        if command.note is not None: args += ['--note', command.note]
        return args

    def test_m2r_ac_26_no_import_or_payload_effects(self):
        program = '''import sys,os,builtins
original=builtins.__import__
def guarded(name,*a,**k):
 if name=='main' or name.startswith(('app.config','app.llm','app.agents','app.memory','app.core.react_controller','app.core.evaluator','app.core.route_crawler','app.core.auth_handler')): raise AssertionError('runtime import')
 return original(name,*a,**k)
builtins.__import__=guarded
def audit(event,args):
 if event=='open' and (isinstance(args[1],str) and any(c in args[1] for c in 'wax+') or isinstance(args[2],int) and args[2] & (os.O_WRONLY|os.O_RDWR|os.O_CREAT)): raise AssertionError('write')
 if event in ('os.mkdir','sqlite3.connect','socket.connect','socket.bind','subprocess.Popen'): raise AssertionError(event)
sys.addaudithook(audit)
from app.review_cli import main
for argv in [['--help'],['help'],['version']]: assert main(argv)==0
'''
        p = subprocess.run([sys.executable, '-B', '-c', program], cwd=self.root,
            env={'SystemRoot': os.environ.get('SystemRoot', ''), 'PYTHONPATH': str(m0.ROOT)}, capture_output=True, text=True)
        self.assertEqual(0, p.returncode, p.stderr)
        data = self.candidate_data(self.planv)
        replace_payload(data, 'suite.spec.ts', b'PRIVATE_SENTINEL; import host_secret; run_provider()')
        package = self.package(data, self.planv)
        with patch('socket.socket.connect', side_effect=AssertionError('network')), patch('subprocess.run', side_effect=AssertionError('process')):
            service.register_package(self.reviews, self.store, canonical_artifact_bytes(package))
            self.assertEqual('pending', self.reviews.inspect_subject('package', package.digest)['raw_status'])

    def test_m2r_ac_27_complete_cli_journey_and_flags(self):
        self.assertEqual(0, cli('version')[0])
        code, out, err = cli(*self.review_args(self.cmd()))
        self.assertEqual(0, code, err)
        self.assertEqual(0, cli(*self.review_args(self.cmd('package')))[0])
        args = ['assess', '--db', str(self.rdb), '--baseline-db', str(self.db), '--kind', 'package', '--digest', self.packagev.digest]
        code, out, err = cli(*args)
        self.assertEqual(0, code, err)
        self.assertTrue(json.loads(out)['package_review_effective'])
        self.assertEqual(0, cli(*self.review_args(self.cmd('plan', 'revoke')))[0])
        self.assertEqual(3, cli(*args)[0])
        for flag in ('--execute', '--approved', '--actor', '--force', '--auto', '--install'):
            code, out, err = cli(*args, flag, 'PRIVATE_SENTINEL')
            self.assertEqual((2, ''), (code, out))
            self.assertNotIn('PRIVATE_SENTINEL', err)
        for seq in ('-1', '+1', ' 1', '01', str(MAX_SEQUENCE + 1)):
            self.assertEqual(2, cli('history', '--db', str(self.rdb), '--after', seq)[0])

    def test_m2r_ac_28_protected_sources_and_false_contracts(self):
        paths = subprocess.check_output(['git', 'ls-tree', '-r', '--name-only', 'b94d76d'], cwd=m0.ROOT, text=True).splitlines()
        for p in paths:
            if p.endswith('.md'): continue
            self.assertEqual(subprocess.check_output(['git', 'show', 'b94d76d:' + p], cwd=m0.ROOT), (m0.ROOT / p).read_bytes(), p)
        self.assertIs(False, self.assess().artifact_assessment.execution_authorized)
        self.assertEqual(self.planv.digest, self.assess().plan_review.subject.plan_digest)

    def test_m2r_ac_29_real_store_lineage_and_read_only_assessments(self):
        self.effective()
        a, b = self.db.read_bytes(), self.rdb.read_bytes()
        result = self.assess()
        self.assertEqual(self.snapshot.digest, result.subject.baseline_digest)
        self.assertEqual(self.planv.digest, result.subject.plan_digest)
        self.assertEqual(self.packagev.digest, result.subject.subject_digest)
        self.assertEqual(2, result.latest_decision_sequence)
        self.assertEqual(1, result.parent_plan_approval_sequence)
        self.assertEqual((a, b), (self.db.read_bytes(), self.rdb.read_bytes()))

    def test_crash_process_before_and_after_commit(self):
        for stage, expected in (('decision_inserted', 0), ('before_commit', 0), ('committed', 1)):
            with self.subTest(stage=stage):
                request = str(uuid4())
                command = self.cmd(request_id=request)
                program = '''import sys,os,json
from app.core.package_review_store import PackageReviewStore
from app.core.review_store import ReviewStore
from app.core.package_review_service import record_review
from app.review_contracts import ReviewCommandV1
r=PackageReviewStore(sys.argv[1]); c=r.local_context()
def crash(stage):
 if stage==sys.argv[4]: os._exit(71)
r._checkpoint=crash
record_review(r,ReviewCommandV1.model_validate(json.loads(sys.argv[3])),c,ReviewStore(sys.argv[2]))
'''
                result = subprocess.run([sys.executable, '-B', '-c', program, str(self.rdb), str(self.db),
                    json.dumps(command.model_dump(mode='json')), stage], capture_output=True, text=True)
                self.assertEqual(71, result.returncode, result.stderr)
                self.assertEqual(expected, self.reviews.snapshot().sequence)
                if expected:
                    d = service.record_review(self.reviews, command, self.reviews.local_context())
                    self.assertEqual(1, d.sequence)

    def test_hot_journal_read_denial_then_explicit_write_recovery(self):
        self.decide()
        command = self.cmd('plan', 'revoke')
        program = '''import sqlite3,sys,os
c=sqlite3.connect(sys.argv[1],isolation_level=None)
c.execute('PRAGMA cache_size=10');c.execute('PRAGMA synchronous=FULL');c.execute('BEGIN IMMEDIATE')
c.execute('DROP TRIGGER store_metadata_no_update')
c.execute('UPDATE store_metadata SET content=?',(b'x'*3000000,))
os._exit(72)
'''
        result = subprocess.run([sys.executable, '-B', '-c', program, str(self.rdb)], capture_output=True, text=True)
        self.assertEqual(72, result.returncode, result.stderr)
        journal = Path(str(self.rdb) + '-journal'); self.assertTrue(journal.exists())
        before = self.rdb.read_bytes(), journal.read_bytes(), self.db.read_bytes()
        self.error('RECOVERY_REQUIRED', self.reviews.inspect_history)
        self.assertEqual(before, (self.rdb.read_bytes(), journal.read_bytes(), self.db.read_bytes()))
        code, out, err = cli(*self.review_args(command))
        self.assertEqual(0, code, err)
        self.assertEqual('revoke', json.loads(out)['decision'])
        self.assertEqual(before[2], self.db.read_bytes())
        self.assertEqual(2, self.reviews.snapshot().sequence)

    def test_concurrent_writers_and_disk_full_rollback(self):
        commands = [self.cmd(), self.cmd()]
        context = self.reviews.local_context()
        def attempt(command):
            try:
                return service.record_review(PackageReviewStore(self.rdb), command, context, self.store).decision
            except ReviewError as exc:
                return exc.code
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(attempt, commands))
        self.assertEqual(['STALE_SEQUENCE', 'approve'], sorted(results))
        command = self.cmd('plan', 'revoke')
        before = self.rdb.read_bytes()
        def disk_full(stage):
            if stage == 'decision_inserted': raise sqlite3.OperationalError('database or disk is full')
        with patch.object(self.reviews, '_checkpoint', side_effect=disk_full):
            self.error('STORE_FAILURE', service.record_review, self.reviews, command, context)
        self.assertEqual(before, self.rdb.read_bytes())
        self.assertEqual(1, self.reviews.snapshot().sequence)

    def test_large_package_uses_unchanged_m2_decoder(self):
        data = self.candidate_data(self.planv)
        replace_payload(data, 'large.bin', b'x' * 25000, role='data')
        package = self.package(data, self.planv)
        raw = canonical_artifact_bytes(package)
        result = service.register_package(self.reviews, self.store, raw)
        self.assertTrue(result.created)
        self.assertEqual(raw, self.reviews.export_subject('package', package.digest))
        self.assertIs(False, service.assess_package_review(self.reviews, self.store, package.digest).execution_authorized)

    def test_history_overflow_requires_smaller_explicit_page(self):
        self.decide()
        view = self.reviews.snapshot()
        d = view.decisions[0]
        decisions = tuple(d.model_copy(update=dict(sequence=i, expected_sequence=i-1,
            previous_decision_sequence=i-1 if i>1 else None, request_id=str(uuid4()),
            note='\U0001f642' * 2048)) for i in range(1,1001))
        with patch.object(self.reviews, 'snapshot', return_value=replace(view, decisions=decisions)):
            self.error('LIMIT_EXCEEDED', self.reviews.inspect_history, 0, 1000)
            page = self.reviews.inspect_history(0, 100)
            self.assertEqual(100, len(page.decisions))
            self.assertEqual(100, page.next_after_sequence)

    def test_upstream_hot_journal_is_not_recovered(self):
        command = self.cmd()
        program = '''import sqlite3,sys,os
c=sqlite3.connect(sys.argv[1],isolation_level=None)
c.execute('PRAGMA cache_size=10');c.execute('PRAGMA synchronous=FULL');c.execute('BEGIN IMMEDIATE')
c.execute('UPDATE project_state SET review_sequence=99')
c.execute('INSERT INTO snapshots VALUES(?,?,NULL,?)',(sys.argv[2],'sha256:'+'e'*64,b'x'*3000000))
os._exit(73)
'''
        result = subprocess.run([sys.executable, '-B', '-c', program, str(self.db), m0.PROJECT], capture_output=True, text=True)
        self.assertEqual(73, result.returncode, result.stderr)
        journal = Path(str(self.db) + '-journal'); self.assertTrue(journal.exists())
        before = self.db.read_bytes(), journal.read_bytes(), self.rdb.read_bytes()
        code, out, err = cli(*self.review_args(command))
        self.assertEqual(4, code)
        self.assertEqual(('m0','RECOVERY_REQUIRED'), (json.loads(err)['source'],json.loads(err)['code']))
        self.assertEqual(before, (self.db.read_bytes(),journal.read_bytes(),self.rdb.read_bytes()))
        # A mistaken review --db must not recover a foreign authority database just
        # to discover that its application identity is wrong.
        self.error('STORE_IDENTITY_MISMATCH', PackageReviewStore(self.db).local_context)
        self.assertEqual(before, (self.db.read_bytes(),journal.read_bytes(),self.rdb.read_bytes()))

    def test_sql_column_tampering_with_original_schema(self):
        # Preserve the schema while changing a nullable parent column: SQLite CHECK
        # expressions containing NULL are insufficient without independent row checks.
        with contextlib.closing(sqlite3.connect(self.rdb)) as con:
            sql = con.execute("SELECT sql FROM sqlite_master WHERE name='subjects_no_update'").fetchone()[0]
            con.execute('DROP TRIGGER subjects_no_update')
            con.execute("UPDATE subjects SET parent_kind=NULL WHERE kind='package'")
            con.execute(sql);con.commit()
        self.error('INTEGRITY_ERROR', self.reviews.snapshot)

    def test_full_cli_initialization_registration_inspection_export(self):
        rdb = self.root / 'cli-review.sqlite3'
        plan = self.root / 'plan.json'; plan.write_bytes(canonical_plan_bytes(self.planv))
        package = self.root / 'package.json'; package.write_bytes(canonical_artifact_bytes(self.packagev))
        def run(*args):
            code, out, err = cli(*args)
            self.assertEqual(0, code, err)
            return json.loads(out)
        run('init', '--db', str(rdb), '--baseline-db', str(self.db), '--project', m0.PROJECT, '--baseline', self.snapshot.digest)
        run('register-plan', '--db', str(rdb), '--baseline-db', str(self.db), '--plan', str(plan))
        run('register-package', '--db', str(rdb), '--baseline-db', str(self.db), '--package', str(package))
        inspected = run('inspect', '--db', str(rdb), '--kind', 'package', '--digest', self.packagev.digest)
        self.assertEqual('pending', inspected['raw_status'])
        self.assertNotIn('canonical_content', inspected)
        for command in (self.cmd(), self.cmd('package', expected_sequence=1)):
            run(*(str(rdb) if a == str(self.rdb) else a for a in self.review_args(command)))
        history = run('history', '--db', str(rdb), '--limit', '1')
        self.assertEqual(1, history['next_after_sequence'])
        output = self.root / 'export.json'
        run('export', '--db', str(rdb), '--kind', 'package', '--digest', self.packagev.digest, '--out', str(output))
        self.assertEqual(package.read_bytes(), output.read_bytes())

    def test_foreign_project_record_and_forged_assessment(self):
        other = self.root / 'other-m0.sqlite3'
        ReviewStore.initialize(other)
        baseline = ReviewStore(other)
        baseline.create_project(m0.PROJECT, 'different operator')
        baseline.store_snapshot(self.snapshot)
        before = self.rdb.read_bytes()
        self.error('AUTHORITY_MISMATCH', service.register_plan, self.reviews, baseline, canonical_plan_bytes(self.planv))
        self.error('AUTHORITY_MISMATCH', service.assess_plan_review, self.reviews, baseline, self.planv.digest)
        self.assertEqual(before, self.rdb.read_bytes())
        self.effective()
        a = self.assess()
        self.error('INVALID_INPUT', a.model_copy, update={'plan_review': a.plan_review.model_copy(update={'review_sequence': a.review_sequence + 1})})
        self.assertRaises(ReviewError, service.record_review, self.reviews, a.model_dump(), self.reviews.local_context())

    def test_actual_store_busy_and_sequence_exhaustion(self):
        command = self.cmd(); context = self.reviews.local_context()
        with contextlib.closing(sqlite3.connect(self.rdb, isolation_level=None)) as con:
            con.execute('BEGIN IMMEDIATE')
            self.error('STORE_BUSY', service.record_review, self.reviews, command, context, self.store)
            con.execute('ROLLBACK')
        with patch.object(ReviewSnapshot, 'sequence', new_callable=PropertyMock, return_value=MAX_SEQUENCE):
            command = command.model_copy(update={'expected_sequence': MAX_SEQUENCE})
            self.error('SEQUENCE_EXHAUSTED', service.record_review, self.reviews, command, context, self.store)
        self.assertEqual(0, self.reviews.snapshot().sequence)

    def test_unapproved_wal_store_is_not_adopted(self):
        with contextlib.closing(sqlite3.connect(self.rdb)) as con:
            self.assertEqual('wal', con.execute('PRAGMA journal_mode=WAL').fetchone()[0])
        before = {p.name: p.read_bytes() for p in self.root.glob('packages.sqlite3*')}
        self.error('INTEGRITY_ERROR', self.reviews.snapshot)
        self.error('INTEGRITY_ERROR', self.reviews.local_context)
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.root.glob('packages.sqlite3*')})

    def test_interrupt_preserves_commit_uncertainty(self):
        command = self.cmd()
        for stage, count, code in (('decision_inserted', 0, 'OUTPUT_FAILURE'), ('committed', 1, 'COMMIT_OUTCOME_UNKNOWN')):
            def interrupt(current):
                if current == stage: raise KeyboardInterrupt('PRIVATE_SENTINEL')
            with patch.object(PackageReviewStore, '_checkpoint', side_effect=interrupt):
                status, out, err = cli(*self.review_args(command))
            self.assertEqual(130, status)
            self.assertEqual(code, json.loads(err)['code'])
            self.assertEqual(count, self.reviews.snapshot().sequence)
            self.assertNotIn('PRIVATE_SENTINEL', out + err)
        self.assertEqual(0, cli(*self.review_args(command))[0])
        self.assertEqual(1, self.reviews.snapshot().sequence)
