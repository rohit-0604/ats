"""Focused boundary/fault regressions supplementing the 33 acceptance families."""
import contextlib
import copy
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import sqlite3
import threading
import unittest
from uuid import uuid4
import test_m0_acceptance as a
from app.baseline_contracts import M0Error, canonical_bytes, parse_json
from app.core.baseline_review import import_legacy_bundle
from app.core.review_store import ReviewStore
class Focused(unittest.TestCase):
    setUp=a.Acceptance.setUp
    tearDown=a.Acceptance.tearDown
    assertError=a.Acceptance.assertError
    review=a.Acceptance.review
    put=a.Acceptance.put
    child=a.Acceptance.child

    def test_ac_27_python_snapshot_api_obeys_aggregate_limits(self):
        from app.baseline_contracts import BaselineSnapshotV1, digest_content, validate_model
        data=a.draft_data()
        for _ in range(63):
            data['sources'].append(dict(data['sources'][0],evidence_id=str(uuid4())))
        candidate=data['criteria'][0]
        candidate['source_ids']=[s['evidence_id'] for s in data['sources']]
        for _ in range(1799):
            data['criteria'].append(dict(candidate,criterion_id=str(uuid4())))
        data['digest']=digest_content(data)
        self.assertLess(len(canonical_bytes(data)),8388608)
        self.assertError('LIMIT_EXCEEDED',validate_model,BaselineSnapshotV1,data)
    def test_ac_06_and_25_argparse_never_echoes_untrusted_values(self):
        sentinel='SYNTHETIC_PRIVATE_ARGUMENT'
        for args in [('review','--expected-sequence',sentinel),('review','--'+sentinel)]:
            with self.subTest(args=args):
                code,out,err=a.cli(*args)
                self.assertEqual(2,code)
                self.assertNotIn(sentinel,out+err)
                self.assertEqual('INVALID_INPUT',json.loads(err)['code'])
    def test_ac_19_deprecated_copy_cannot_bypass_validation(self):
        s=self.put()
        self.assertError('INVALID_INPUT',s.copy,update={'schema_version':True})
    def test_ac_27_numeric_metadata_overflow_is_a_safe_failure(self):
        d=json.loads((a.FIXTURES/'legacy.json').read_bytes())
        d['requirements'][0]['confidence']=10**400
        self.assertError('INVALID_INPUT',import_legacy_bundle,json.dumps(d).encode(),a.PROJECT,'sample')
        d['requirements'][0]['confidence']=1
        d['pass_stats']['total_time_s']=10**400
        r=import_legacy_bundle(json.dumps(d).encode(),a.PROJECT,'sample')
        self.assertEqual(2,len(r.draft.requirements))
    def test_ac_32_unknown_wal_store_is_not_modified(self):
        path=self.root/'unknown.sqlite3'
        with contextlib.closing(sqlite3.connect(path)) as con, con:
            con.execute('PRAGMA journal_mode=WAL')
            con.execute('CREATE TABLE checkpoint_example(value TEXT)')
        before=path.read_bytes()
        self.assertError('UNSUPPORTED_VERSION',ReviewStore(path).local_context,a.PROJECT)
        self.assertEqual(before,path.read_bytes())
        with contextlib.closing(sqlite3.connect(path)) as con:
            self.assertEqual('wal',con.execute('PRAGMA journal_mode').fetchone()[0])
    def test_ac_22_actual_concurrent_commands(self):
        one=self.put()
        d=a.draft_data()
        d['criteria'][0]['expected_outcome']='Exactly six cards.'
        two=self.put(d)
        barrier=threading.Barrier(2)
        def worker(subject):
            store=ReviewStore(self.db)
            ctx=store.local_context(a.PROJECT)
            barrier.wait(timeout=10)
            try:
                return store.record_review(a.command(subject),ctx).decision
            except M0Error as exc:
                return exc.code
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures=[pool.submit(worker,s) for s in (one,two)]
            results=[f.result(timeout=15) for f in futures]
        self.assertCountEqual(['approve','STALE_SEQUENCE'],results)
        self.assertEqual(1,len(self.store.history(a.PROJECT).decisions))
    def test_ac_16_digest_verification_with_intact_schema(self):
        s=self.put()
        with contextlib.closing(sqlite3.connect(self.db)) as con, con:
            sql=con.execute("SELECT sql FROM sqlite_master WHERE name='snapshots_no_update'").fetchone()[0]
            con.execute('DROP TRIGGER snapshots_no_update')
            body=json.loads(canonical_bytes(s))
            body['criteria'][0]['expected_outcome']='Three cards'
            con.execute('UPDATE snapshots SET content=?',(canonical_bytes(body),))
            con.execute(sql)
        self.assertError('INTEGRITY_ERROR',self.store.inspect,a.PROJECT,s.digest)
    def test_ac_23_original_claim_and_criterion_mapping_cannot_change(self):
        imported=import_legacy_bundle((a.FIXTURES/'legacy.json').read_bytes(),a.PROJECT,'sample')
        from app.core.baseline_review import freeze_baseline
        parent=freeze_baseline(imported.draft)
        self.store.store_snapshot(parent)
        for modify in [lambda d:d['requirements'][0]['legacy'].update(original_description='Changed original'),
                lambda d:d['criteria'][0].update(requirement_id=d['requirements'][1]['requirement_id']),
                lambda d:d['sources'][0].update(excerpt='Changed source')]:
            data=parent.model_dump(mode='json')
            data.pop('digest')
            data['parent_digest']=parent.digest
            modify(data)
            self.assertError('PARENT_ID_LOSS',self.store.store_snapshot,freeze_baseline(a.draft(data)))
    def test_ac_27_depth_and_node_boundaries(self):
        self.assertIsNotNone(parse_json(b'['*32+b'0'+b']'*32))
        self.assertError('LIMIT_EXCEEDED',parse_json,b'['*33+b'0'+b']'*33)
        self.assertEqual(99999,len(parse_json(json.dumps([None]*99999).encode())))
        self.assertError('LIMIT_EXCEEDED',parse_json,json.dumps([None]*100000).encode())
    def test_ac_27_record_and_reference_limits(self):
        data=a.draft_data()
        for _ in range(999):
            r=copy.deepcopy(data['requirements'][0])
            r['requirement_id']=str(uuid4())
            data['requirements'].append(r)
        self.assertEqual(1000,len(a.draft(data).requirements))
        data['requirements'].append(dict(data['requirements'][0],requirement_id=str(uuid4())))
        self.assertError('LIMIT_EXCEEDED',a.draft,data)
        data=a.draft_data()
        for _ in range(64):
            source=dict(data['sources'][0],evidence_id=str(uuid4()))
            data['sources'].append(source)
        data['requirements'][0]['source_ids']=[s['evidence_id'] for s in data['sources'][:64]]
        self.assertEqual(64,len(a.draft(data).requirements[0].source_ids))
        data['requirements'][0]['source_ids'].append(data['sources'][64]['evidence_id'])
        self.assertError('LIMIT_EXCEEDED',a.draft,data)
        data=a.draft_data()
        data['criteria'][0]['preconditions']=['x']*64
        a.draft(data)
        data['criteria'][0]['preconditions'].append('x')
        self.assertError('LIMIT_EXCEEDED',a.draft,data)
    def test_ac_27_criteria_and_source_count_limits(self):
        data=a.draft_data()
        for _ in range(4999):
            data['criteria'].append(dict(data['criteria'][0],criterion_id=str(uuid4())))
        self.assertEqual(5000,len(a.draft(data).criteria))
        data['criteria'].append(dict(data['criteria'][0],criterion_id=str(uuid4())))
        self.assertError('LIMIT_EXCEEDED',a.draft,data)
        data=a.draft_data()
        for _ in range(9999):
            data['sources'].append(dict(data['sources'][0],evidence_id=str(uuid4())))
        self.assertEqual(10000,len(a.draft(data).sources))
        data['sources'].append(dict(data['sources'][0],evidence_id=str(uuid4())))
        self.assertError('LIMIT_EXCEEDED',a.draft,data)
    def test_ac_32_state_tampering_fails_closed(self):
        s=self.put()
        with contextlib.closing(sqlite3.connect(self.db)) as con,con:
            con.execute('UPDATE project_state SET review_sequence=1')
        self.assertError('INTEGRITY_ERROR',self.store.inspect,a.PROJECT,s.digest)
    def test_ac_20_unicode_golden_and_source_metadata_identity(self):
        from app.core.baseline_review import freeze_baseline
        vector=json.loads((a.FIXTURES/'golden.json').read_text(encoding='utf-8'))['unicode']
        data=a.draft_data()
        data['requirements'][0]['description']='Café\n  four cards'
        data['criteria'][0]['preconditions']=['first','second']
        s=freeze_baseline(a.draft(data))
        body=s.model_dump(mode='json')
        body.pop('digest')
        self.assertEqual(vector['canonical'],canonical_bytes(body).decode())
        self.assertEqual(vector['digest'],s.digest)
    def test_ac_30_current_exporter_domain_fields(self):
        obj=json.loads((a.FIXTURES/'legacy.json').read_bytes())
        obj['domain_profile']=dict(framework_hints=['synthetic'],has_rest_api=False,auth_type='none')
        self.assertEqual(2,len(import_legacy_bundle(json.dumps(obj).encode(),a.PROJECT,'sample').draft.requirements))
        obj['requirements'][0]['source_chunk']=True
        self.assertError('INVALID_INPUT',import_legacy_bundle,json.dumps(obj).encode(),a.PROJECT,'sample')
    def test_ac_31_export_interruption_keeps_existing_files(self):
        from unittest.mock import patch
        from app.core.baseline_files import write_export
        path=self.root/'export.json'
        with patch('app.core.baseline_files.os.fsync',side_effect=OSError('synthetic full disk')):
            self.assertError('OUTPUT_FAILURE',write_export,path,b'{}')
        self.assertFalse(path.exists())
