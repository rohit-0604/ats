"""Offline acceptance evidence for M0-SPEC-2026-10-23-v2.

Each test_ac_NN maps directly to M0-AC-NN. All data and stores are synthetic.
"""
from __future__ import annotations
import contextlib
import copy
import io
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
from uuid import uuid4
from app.baseline_contracts import (
    BaselineDraftV1, BaselineSnapshotV1, M0Error, ReviewCommandV1,
    canonical_bytes, digest_content, parse_json, validate_model,
)
from app.core.baseline_review import (
    approval_blockers, freeze_baseline, import_legacy_bundle, validate_draft,
)
from app.core.review_store import ReviewStore
from app.baseline_cli import main, validate_path, write_export
ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable
PROJECT = '00000000-0000-4000-8000-000000000001'
REQ = '00000000-0000-4000-8000-000000000002'
CRITERION = '00000000-0000-4000-8000-000000000003'
EVIDENCE = '00000000-0000-4000-8000-000000000004'
FIXTURES = Path(__file__).parent / 'fixtures' / 'baselines'
def draft_data():
    return dict(schema_version=1, project_id=PROJECT, parent_digest=None,
        requirements=[dict(requirement_id=REQ, title='Feature cards',
            description='Guests see exactly four cards.', source_ids=[EVIDENCE],
            dependency_ids=[], legacy=None)],
        criteria=[dict(criterion_id=CRITERION, requirement_id=REQ,
            preconditions=['Guest session'], action='Open the home page',
            expected_outcome='Exactly four cards are visible.', origin='human_authored',
            clarity='specified', unresolved_reason=None, automation_support='supported',
            support_reason=None, source_ids=[EVIDENCE])],
        sources=[dict(evidence_id=EVIDENCE, kind='human_decision',
            reference='decision:synthetic-1', content_digest=None,
            excerpt='The synthetic fixture requires exactly four cards.')])
def draft(data=None):
    return validate_draft(json.dumps(draft_data() if data is None else data).encode())
def command(subject, decision='approve', sequence=0, request=None, project=PROJECT):
    return validate_model(ReviewCommandV1, dict(schema_version=1, project_id=project,
        subject_digest=subject.digest, decision=decision, expected_sequence=sequence,
        request_id=request or str(uuid4()), reason='Synthetic acceptance review'))
def cli(*args):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = main(list(args))
    return code, out.getvalue(), err.getvalue()
class Acceptance(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='ats_m0_')
        self.root = Path(self.temp.name)
        self.db = self.root / 'review.sqlite3'
        ReviewStore.initialize(self.db)
        self.store = ReviewStore(self.db)
        self.store.create_project(PROJECT, 'human operator')
    def tearDown(self):
        self.temp.cleanup()
    def assertError(self, code, fn, *args, **kwargs):
        with self.assertRaises(M0Error) as cm:
            fn(*args, **kwargs)
        self.assertEqual(code, cm.exception.code)
        return cm.exception
    def review(self, cmd, store=None):
        s = store or self.store
        return s.record_review(cmd, s.local_context(cmd.project_id))
    def put(self, data=None):
        s = freeze_baseline(draft(data))
        self.store.store_snapshot(s)
        return s
    def child(self, parent, expected='Exactly five cards are visible.'):
        d = parent.model_dump(mode='json')
        d.pop('digest')
        d['parent_digest'] = parent.digest
        d['criteria'][0]['expected_outcome'] = expected
        return self.put(d)
    def test_ac_01_legacy_flags_are_claims(self):
        raw = (FIXTURES / 'legacy.json').read_bytes()
        r = import_legacy_bundle(raw, PROJECT, 'sample')
        self.assertTrue(r.draft.requirements[0].legacy.approved)
        self.assertTrue(any(w.code == 'LEGACY_APPROVAL_UNTRUSTED' for w in r.warnings))
        s = freeze_baseline(r.draft)
        self.store.store_snapshot(s)
        self.assertEqual('pending', self.store.get_effective_review(PROJECT, s.digest).status)
        self.assertError('NOT_APPROVABLE', self.review, command(s))
        obj = json.loads(raw)
        obj['requirements'][0]['rejected'] = True
        both = import_legacy_bundle(json.dumps(obj).encode(), PROJECT, 'sample')
        self.assertTrue(both.draft.requirements[0].legacy.rejected)
        self.assertTrue(both.draft.requirements[0].legacy.approved)
    def test_ac_02_semantic_records_survive(self):
        r = import_legacy_bundle((FIXTURES / 'legacy.json').read_bytes(), PROJECT, 'sample')
        self.assertEqual(2, len(r.draft.requirements))
        self.assertEqual({'Guests must not access reports.', 'Administrators must access reports.'},
            {v.legacy.original_description for v in r.draft.requirements})
    def test_ac_03_multiple_criteria(self):
        d = draft_data()
        c = copy.deepcopy(d['criteria'][0])
        c['criterion_id'] = str(uuid4())
        c['expected_outcome'] = 'A guest cannot edit a card.'
        d['criteria'].append(c)
        s = self.put(d)
        self.assertEqual(2, len(self.store.inspect(PROJECT, s.digest).snapshot.criteria))
    def test_ac_04_pending_content_cannot_be_approved(self):
        d = draft_data()
        c = d['criteria'][0]
        c.update(action=None, expected_outcome=None, clarity='unresolved', unresolved_reason='Needs human clarification')
        s = self.put(d)
        self.assertError('NOT_APPROVABLE', self.review, command(s))
        self.assertEqual(0, self.store.get_effective_review(PROJECT, s.digest).project_sequence)
    def test_ac_05_unsupported_is_preserved(self):
        d = draft_data()
        d['criteria'][0].update(automation_support='unsupported', support_reason='Requires manual observation')
        s = self.put(d)
        self.review(command(s))
        inspected = self.store.inspect(PROJECT, s.digest)
        self.assertEqual('approved', inspected.review.status)
        self.assertEqual('unsupported', inspected.snapshot.criteria[0].automation_support)
    def test_ac_06_strict_versions_ids_and_references(self):
        for modify, code in [
            (lambda d: d.update(schema_version=2), 'UNSUPPORTED_VERSION'),
            (lambda d: d['requirements'].append(copy.deepcopy(d['requirements'][0])), 'DUPLICATE_ID'),
            (lambda d: d['criteria'][0].update(requirement_id=str(uuid4())), 'INVALID_REFERENCE'),
            (lambda d: d.update(resource={'password': 'synthetic private value'}), 'UNKNOWN_FIELD'),
            (lambda d: d.update(schema_version=True), 'INVALID_INPUT')]:
            with self.subTest(code=code):
                d = draft_data()
                modify(d)
                self.assertError(code, draft, d)
        self.assertError('INVALID_INPUT', parse_json, b'{"a":1,"a":2}')
    def test_ac_07_canonical_golden(self):
        vector = json.loads((FIXTURES / 'golden.json').read_text(encoding='utf-8'))
        s = freeze_baseline(draft())
        body = s.model_dump(mode='json')
        body.pop('digest')
        self.assertEqual(vector['canonical'], canonical_bytes(body).decode('utf-8'))
        self.assertEqual(vector['digest'], s.digest)
        d = draft_data()
        d['requirements'][0]['source_ids'].reverse()
        d['sources'].reverse()
        self.assertEqual(s.digest, freeze_baseline(draft(d)).digest)
    def test_ac_08_changed_threshold_changes_digest(self):
        a = self.put()
        b = self.child(a)
        self.assertNotEqual(a.digest, b.digest)
        self.assertEqual(a, self.store.inspect(PROJECT, a.digest).snapshot)
    def test_ac_09_old_approval_cannot_approve_new_content(self):
        a = self.put()
        self.review(command(a))
        b = self.child(a)
        self.assertEqual('pending', self.store.get_effective_review(PROJECT, b.digest).status)
        self.assertEqual('approved', self.store.get_effective_review(PROJECT, a.digest).status)
    def test_ac_10_project_mismatch(self):
        s = self.put()
        other = str(uuid4())
        self.store.create_project(other, 'other synthetic operator')
        self.assertError('PROJECT_MISMATCH', self.review, command(s, project=other))
        self.assertEqual(0, self.store.get_effective_review(PROJECT, s.digest).project_sequence)
    def test_ac_11_identical_retry_after_revocation(self):
        s = self.put()
        cmd = command(s)
        first = self.review(cmd)
        self.review(command(s, 'revoke', 1))
        self.assertEqual(first, self.review(cmd))
        self.assertEqual('revoked', self.store.get_effective_review(PROJECT, s.digest).status)
        self.assertEqual(2, len(self.store.history(PROJECT).decisions))
    def test_ac_12_request_conflicts_and_stale_commands(self):
        s = self.put()
        c = command(s)
        self.review(c)
        self.assertError('REQUEST_ID_CONFLICT', self.review, c.model_copy(update={'reason': 'Different request contents'}))
        self.assertError('STALE_SEQUENCE', self.review, command(s, 'revoke', 0))
        self.assertEqual(1, len(self.store.history(PROJECT).decisions))
    def test_ac_13_supersession_and_revocation(self):
        a = self.put()
        self.review(command(a))
        b = self.child(a)
        self.review(command(b, sequence=1))
        self.review(command(b, 'revoke', 2))
        self.assertEqual('superseded', self.store.get_effective_review(PROJECT, a.digest).status)
        r = self.store.get_effective_review(PROJECT, b.digest)
        self.assertEqual(('revoked', None, b.digest, 3), (r.status, r.active_digest, r.head_digest, r.project_sequence))
    def test_ac_14_failure_before_commit_rolls_back(self):
        s = self.put()
        def fault(stage):
            if stage == 'decision_inserted':
                raise OSError('synthetic disk failure')
        with patch.object(self.store, '_checkpoint', side_effect=fault):
            self.assertError('STORE_FAILURE', self.review, command(s))
        r = ReviewStore(self.db).get_effective_review(PROJECT, s.digest)
        self.assertEqual(('pending', 0, None), (r.status, r.project_sequence, r.active_digest))
    def test_ac_15_committed_data_survives_reopen(self):
        s = self.put()
        r = self.review(command(s))
        again = ReviewStore(self.db)
        self.assertEqual(r, again.history(PROJECT).decisions[0])
        self.assertEqual(s, again.inspect(PROJECT, s.digest).snapshot)
    def test_ac_16_tampered_snapshot_fails(self):
        s = self.put()
        with contextlib.closing(sqlite3.connect(self.db)) as con, con:
            con.execute('DROP TRIGGER snapshots_no_update')
            con.execute('UPDATE snapshots SET content=?', (b'{}',))
        self.assertError('INTEGRITY_ERROR', self.store.inspect, PROJECT, s.digest)
    def test_ac_17_imports_and_help_have_no_effects(self):
        program = '''import sys, pathlib, socket, builtins
before=set(pathlib.Path('.').rglob('*'))
original=builtins.__import__
def guarded(name,*a,**k):
 if name.startswith(('app.config','app.llm','app.agents','app.memory','app.core.react_controller')) or name=='main': raise AssertionError('Forbidden runtime import')
 return original(name,*a,**k)
builtins.__import__=guarded
class NoNetworkSocket(socket.socket):
 def __init__(self,*a,**k): raise AssertionError('network')
socket.socket=NoNetworkSocket
def audit(event,args):
 if event=='open' and (isinstance(args[1],str) and any(c in args[1] for c in 'wax+') or isinstance(args[2],int) and args[2] & (os.O_WRONLY|os.O_RDWR|os.O_CREAT)): raise AssertionError('file write')
 if event in ('os.mkdir','sqlite3.connect'): raise AssertionError('filesystem/database effect')
import os
sys.addaudithook(audit)
import app.baseline_contracts, app.core.baseline_review, app.core.review_store, app.baseline_cli
for args in [['--help'],['version']]:
 try: app.baseline_cli.main(args)
 except SystemExit as e: assert e.code==0
assert before==set(pathlib.Path('.').rglob('*'))
'''
        env = {'SystemRoot': os.environ.get('SystemRoot', ''), 'PYTHONPATH': str(ROOT)}
        p = subprocess.run([PYTHON, '-B', '-c', program], cwd=self.root, env=env, capture_output=True, text=True)
        self.assertEqual(0, p.returncode, p.stderr)
    def test_ac_18_import_identity_is_stable(self):
        obj = json.loads((FIXTURES / 'legacy.json').read_bytes())
        def ids(value, project=PROJECT, key='sample'):
            r = import_legacy_bundle(json.dumps(value).encode(), project, key)
            return {v.legacy.original_req_id: v.requirement_id for v in r.draft.requirements}, {c.criterion_id for c in r.draft.criteria}
        a = ids(obj)
        obj['requirements'].reverse()
        obj['requirements'][0]['description'] = 'Changed description'
        self.assertEqual(a, ids(obj))
        self.assertNotEqual(a, ids(obj, key='other'))
        self.assertNotEqual(a, ids(obj, project=str(uuid4())))
    def test_ac_19_nested_immutability_and_validated_copy(self):
        s = freeze_baseline(draft())
        before = s.digest
        with self.assertRaises(Exception):
            s.requirements[0].title = 'Changed'
        with self.assertRaises(Exception):
            s.requirements += (s.requirements[0],)
        self.assertError('INVALID_INPUT', s.model_copy, update={'schema_version': True})
        self.assertError('INTEGRITY_ERROR', s.model_copy, update={'project_id': str(uuid4())})
        self.assertEqual(before, s.digest)
    def test_ac_20_unicode_order_and_all_content_is_hashed(self):
        d = draft_data()
        d['requirements'][0]['description'] = 'Café\n  four cards'
        d['criteria'][0]['preconditions'] = ['first', 'second']
        a = freeze_baseline(draft(d))
        self.assertIn('Café\n  four cards', a.requirements[0].description)
        self.assertNotIn('created_at', a.model_dump())
        for field, value in [('preconditions', ['second', 'first']), ('expected_outcome', 'five'), ('automation_support', 'unknown')]:
            v = copy.deepcopy(d)
            v['criteria'][0][field] = value
            self.assertNotEqual(a.digest, freeze_baseline(draft(v)).digest)
        for modify in [lambda v: v.update(project_id=str(uuid4())), lambda v: v.update(parent_digest='sha256:'+'a'*64), lambda v: v['sources'][0].update(excerpt='Other evidence')]:
            v = copy.deepcopy(d)
            modify(v)
            self.assertNotEqual(a.digest, freeze_baseline(draft(v)).digest)
        e = copy.deepcopy(d['sources'][0])
        e['evidence_id'] = str(uuid4())
        d['sources'].append(e)
        d['requirements'][0]['source_ids'].append(e['evidence_id'])
        a = freeze_baseline(draft(d))
        d['sources'].reverse()
        d['requirements'][0]['source_ids'].reverse()
        self.assertEqual(a.digest, freeze_baseline(draft(d)).digest)
    def test_ac_21_transition_matrix(self):
        for state in ['pending','approved','rejected','revoked','superseded']:
            for action in ['approve','reject','revoke']:
                with self.subTest(state=state, action=action):
                    path = self.root / (state+action+'.sqlite3')
                    ReviewStore.initialize(path)
                    st = ReviewStore(path)
                    st.create_project(PROJECT, 'human operator')
                    s = freeze_baseline(draft())
                    st.store_snapshot(s)
                    seq = 0
                    if state in ('approved','revoked','superseded'):
                        self.review(command(s), st)
                        seq=1
                    if state=='rejected':
                        self.review(command(s,'reject'), st)
                        seq=1
                    if state=='revoked':
                        self.review(command(s,'revoke',1),st)
                        seq=2
                    if state=='superseded':
                        d = draft_data()
                        d['parent_digest']=s.digest
                        d['criteria'][0]['expected_outcome']='five'
                        child=freeze_baseline(draft(d))
                        st.store_snapshot(child)
                        self.review(command(child,sequence=1),st)
                        seq=2
                    valid = (state=='pending' and action in ('approve','reject')) or (state=='approved' and action=='revoke')
                    if valid:
                        self.review(command(s,action,seq),st)
                    else:
                        self.assertError('INVALID_TRANSITION', self.review, command(s,action,seq),st)
    def test_ac_22_competing_writers_and_stale_lineage(self):
        a = self.put()
        self.review(command(a))
        b = self.child(a)
        c = self.child(a,'six')
        other = ReviewStore(self.db)
        self.review(command(b,sequence=1))
        self.assertError('STALE_SEQUENCE',self.review, command(c,sequence=1), other)
        self.assertError('LINEAGE_CONFLICT',self.review, command(c,sequence=2), other)
        self.assertEqual(2,len(other.history(PROJECT).decisions))
    def test_ac_23_lineage_and_restoration(self):
        a = self.put()
        self.review(command(a))
        self.review(command(a,'revoke',1))
        b = self.child(a,a.criteria[0].expected_outcome)
        self.review(command(b,sequence=2))
        self.assertEqual('approved',self.store.get_effective_review(PROJECT,b.digest).status)
        for change in [lambda d:d['criteria'].clear(), lambda d:d['sources'].clear(),
                lambda d:d.update(parent_digest='sha256:'+'f'*64)]:
            d=b.model_dump(mode='json')
            d.pop('digest')
            d['parent_digest']=b.digest
            change(d)
            try:
                candidate=freeze_baseline(draft(d))
            except M0Error as e:
                self.assertEqual('INVALID_REFERENCE',e.code)
                continue
            self.assertIn(self.assertErrorAny(self.store.store_snapshot,candidate),{'PARENT_ID_LOSS','UNKNOWN_SUBJECT'})
    def assertErrorAny(self, fn, *args):
        with self.assertRaises(M0Error) as cm:
            fn(*args)
        return cm.exception.code
    def test_ac_24_lost_commit_acknowledgment_and_crash(self):
        s=self.put()
        cmd=command(s)
        def fault(stage):
            if stage=='committed':
                raise OSError('lost acknowledgment')
        with patch.object(self.store,'_checkpoint',side_effect=fault):
            self.assertError('COMMIT_OUTCOME_UNKNOWN',self.review,cmd)
        self.assertEqual(1,self.review(cmd).sequence)
        child=self.child(s)
        c=command(child,sequence=1)
        program='''import sys,json,os
from pathlib import Path
from app.core.review_store import ReviewStore
from app.baseline_contracts import ReviewCommandV1,validate_model
s=ReviewStore(Path(sys.argv[1])); c=validate_model(ReviewCommandV1,json.loads(sys.argv[2]))
s._checkpoint=lambda stage: os._exit(71) if stage=='committed' else None
s.record_review(c,s.local_context(c.project_id))
'''
        p=subprocess.run([PYTHON,'-B','-c',program,str(self.db),c.model_dump_json()],cwd=ROOT,capture_output=True)
        self.assertEqual(71,p.returncode,p.stderr)
        self.assertEqual(2,self.review(c).sequence)
        self.assertEqual(2,len(self.store.history(PROJECT).decisions))
    def test_ac_25_authority_is_project_owned(self):
        s=self.put()
        c=command(s)
        bad=c.model_dump(mode='json')
        bad['actor']='model'
        self.assertError('UNKNOWN_FIELD',validate_model,ReviewCommandV1,bad)
        context=self.store.local_context(PROJECT)
        with self.assertRaises(Exception):
            context.reviewer_label='model'
        self.assertEqual('human operator',self.review(c).reviewer_label)
        code,_,_=cli('review','--actor','model')
        self.assertEqual(2,code)
    def test_ac_26_approval_blockers(self):
        for change in [lambda d:d['criteria'].clear(),lambda d:d['requirements'][0].update(title='  '),
                lambda d:d['criteria'][0].update(automation_support='unknown')]:
            d=draft_data()
            change(d)
            self.assertTrue(approval_blockers(draft(d)))
        d=draft_data()
        d['requirements'].clear()
        self.assertError('INVALID_INPUT',draft,d)
        d=draft_data()
        d['sources'][0].update(kind='legacy_import',content_digest='sha256:'+'a'*64)
        self.assertTrue(approval_blockers(draft(d)))
    def test_ac_27_bounded_parsing_and_safe_errors(self):
        for raw in [b'\xff', b'{', b'{"x":NaN}', b'['*33+b'0'+b']'*33,b'{"secret":"\\ud800"}']:
            with self.subTest(raw_type=len(raw)):
                self.assertIn(self.assertErrorAny(parse_json,raw),{'INVALID_INPUT','LIMIT_EXCEEDED'})
        self.assertError('LIMIT_EXCEEDED',parse_json,b' '*8388609)
        base=(FIXTURES/'legacy.json').read_bytes()
        padded=base+b' '*(4194304-len(base))
        self.assertEqual(2,len(import_legacy_bundle(padded,PROJECT,'sample').draft.requirements))
        self.assertError('LIMIT_EXCEEDED',import_legacy_bundle,padded+b' ',PROJECT,'sample')
        bom=import_legacy_bundle(b'\xef\xbb\xbf'+base,PROJECT,'sample')
        self.assertIn('BOM_REMOVED',{w.code for w in bom.warnings})
        self.assertError('LIMIT_EXCEEDED',parse_json,json.dumps(['x']*100001).encode())
        self.assertError('LIMIT_EXCEEDED',parse_json,json.dumps('x'*16385).encode())
        self.assertEqual('x'*16384,parse_json(json.dumps('x'*16384).encode()))
        error=self.assertError('UNKNOWN_FIELD',import_legacy_bundle,b'{"requirements":[],"synthetic-secret-value":"synthetic-secret-value"}',PROJECT,'sample')
        self.assertNotIn('synthetic-secret-value',str(error))
    def test_ac_28_lock_and_storage_failures(self):
        s=self.put()
        with contextlib.closing(sqlite3.connect(self.db,isolation_level=None)) as c:
            c.execute('BEGIN IMMEDIATE')
            start=time.monotonic()
            self.assertError('STORE_BUSY',self.review,command(s))
            self.assertGreaterEqual(time.monotonic()-start,4.5)
            c.execute('ROLLBACK')
        with patch.object(self.store,'_checkpoint',side_effect=PermissionError('synthetic permissions')):
            self.assertError('STORE_FAILURE',self.review,command(s))
        self.assertEqual('pending',self.store.get_effective_review(PROJECT,s.digest).status)
    def test_ac_29_windows_file_boundaries(self):
        for path in [r'\\server\share\x.sqlite3',r'\\?\C:\x.sqlite3',r'C:review.sqlite3',
                     str(self.root/'NUL.sqlite3'),str(self.root/'x.sqlite3:stream'),str(self.root/'trail. '),str(self.root/'missing'/'x.sqlite3')]:
            with self.subTest(path=path):
                self.assertError('PATH_POLICY',validate_path,path)
        good=self.root/'space café.sqlite3'
        ReviewStore.initialize(good)
        self.assertTrue(good.is_file())
        with patch('app.core.baseline_files._drive_type',return_value=4):
            self.assertError('PATH_POLICY',validate_path,str(good))
        if os.name=='nt':
            junction=self.root/'junction'
            target=self.root/'target'
            target.mkdir()
            p=subprocess.run(['cmd','/c','mklink','/J',str(junction),str(target)],capture_output=True)
            self.assertEqual(0,p.returncode,p.stderr)
            self.assertError('PATH_POLICY',validate_path,str(junction/'x.sqlite3'))
    def test_ac_30_legacy_metadata_and_unknown_fields(self):
        r=import_legacy_bundle((FIXTURES/'legacy.json').read_bytes(),PROJECT,'sample')
        self.assertTrue(any(w.pointer.endswith('/confidence') for w in r.warnings))
        claims={v.legacy.original_req_id:v.legacy for v in r.draft.requirements}
        self.assertIsNone(claims['REQ-2'].rejected)
        self.assertEqual('3.2',claims['REQ-1'].section_ref)
        for key in ['actor','resource','password']:
            obj={'requirements':[],key:{'token':'synthetic private text'}}
            self.assertError('UNKNOWN_FIELD',import_legacy_bundle,json.dumps(obj).encode(),PROJECT,'sample')
    def test_ac_31_exclusive_output_and_missing_store(self):
        out=self.root/'draft.json'
        out.write_bytes(b'keep')
        self.assertError('OUTPUT_FAILURE',write_export,out,b'new')
        self.assertEqual(b'keep',out.read_bytes())
        self.assertError('STORE_EXISTS',ReviewStore.initialize,self.db)
        missing=self.root/'absent.sqlite3'
        self.assertError('STORE_NOT_FOUND',ReviewStore(missing).history,PROJECT)
        self.assertFalse(missing.exists())
        with patch('app.core.baseline_files.os.rename',side_effect=OSError('synthetic publish failure')):
            self.assertError('OUTPUT_FAILURE',write_export,self.root/'new.json',b'{}')
        self.assertFalse((self.root/'new.json').exists())
        s=self.put()
        cmd=command(s)
        with patch('app.baseline_cli._emit',side_effect=BrokenPipeError()):
            code,_,_=cli('review','--db',str(self.db),'--project',PROJECT,'--digest',s.digest,
                '--decision','approve','--expected-sequence','0','--request-id',cmd.request_id,'--reason',cmd.reason)
        self.assertEqual(4,code)
        self.assertEqual(1,self.review(cmd).sequence)
    def test_ac_32_sqlite_constraints_integrity_and_recovery(self):
        s=self.put()
        original=command(s)
        self.review(original)
        with contextlib.closing(sqlite3.connect(self.db)) as c, c:
            c.execute('PRAGMA foreign_keys=ON')
            for sql in ['DELETE FROM snapshots','UPDATE snapshots SET content=content','DELETE FROM reviews','UPDATE reviews SET content=content']:
                with self.subTest(sql=sql),self.assertRaises(sqlite3.IntegrityError):
                    c.execute(sql)
            with self.assertRaises(sqlite3.IntegrityError):
                c.execute('UPDATE project_state SET active_digest=?',('sha256:'+'f'*64,))
        wrong=self.root/'wrong.sqlite3'
        with contextlib.closing(sqlite3.connect(wrong)) as c, c:
            c.execute('PRAGMA user_version=2')
        self.assertError('UNSUPPORTED_VERSION',ReviewStore(wrong).history,PROJECT)
        program='''import sys,sqlite3,os
c=sqlite3.connect(sys.argv[1],isolation_level=None);c.execute('PRAGMA cache_size=1');c.execute('BEGIN IMMEDIATE')
c.execute('UPDATE project_state SET review_sequence=99')
c.execute('INSERT INTO snapshots(project_id,digest,parent_digest,content) VALUES(?,?,?,?)',(sys.argv[2],'sha256:'+'e'*64,None,b'x'*1048576))
os._exit(72)
'''
        p=subprocess.run([PYTHON,'-B','-c',program,str(self.db),PROJECT],capture_output=True)
        self.assertEqual(72,p.returncode,p.stderr)
        self.assertTrue(Path(str(self.db)+'-journal').exists())
        self.assertError('RECOVERY_REQUIRED',self.store.inspect,PROJECT,s.digest)
        # An explicitly requested writer open performs SQLite's rollback recovery.
        self.assertEqual(1,self.review(original).sequence)
    def test_ac_33_complete_offline_cli_flow(self):
        path=self.root/'cli.sqlite3'
        prepared=self.root/'prepared.json'
        for args in [('init-store','--db',str(path)),('create-project','--db',str(path),'--project',PROJECT,'--reviewer','human operator'),
                ('prepare','--input',str(FIXTURES/'legacy.json'),'--project',PROJECT,'--source-key','sample','--out',str(prepared))]:
            code,_,err=cli(*args)
            self.assertEqual(0,code,err)
        code,_,_=cli('validate','--draft',str(prepared))
        self.assertEqual(2,code)
        reviewed=self.root/'reviewed.json'
        reviewed.write_text(json.dumps(draft_data()),encoding='utf-8')
        self.assertEqual(0,cli('validate','--draft',str(reviewed))[0])
        code,out,err=cli('freeze','--db',str(path),'--draft',str(reviewed))
        self.assertEqual(0,code,err)
        digest=json.loads(out)['digest']
        for decision,seq in [('approve',0),('revoke',1)]:
            code,_,err=cli('review','--db',str(path),'--project',PROJECT,'--digest',digest,
                '--decision',decision,'--expected-sequence',str(seq),'--request-id',str(uuid4()),'--reason','Synthetic operator decision')
            self.assertEqual(0,code,err)
        code,out,err=cli('inspect','--db',str(path),'--project',PROJECT,'--digest',digest)
        self.assertEqual(0,code,err)
        self.assertEqual('revoked',json.loads(out)['review']['status'])
        code,out,err=cli('history','--db',str(path),'--project',PROJECT,'--limit','1')
        self.assertEqual(0,code,err)
        self.assertEqual(1,json.loads(out)['next_after_sequence'])
if __name__=='__main__':
    unittest.main(verbosity=2)
