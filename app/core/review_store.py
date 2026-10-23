"""Application-owned SQLite baseline/review store, independent of checkpoints."""
from __future__ import annotations
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
import os
from pathlib import Path
import sqlite3
from app.baseline_contracts import (
    MAX_SEQUENCE, BaselineSnapshotV1, EffectiveReviewV1, HistoryPageV1,
    InspectionV1, M0Error, ProjectRecordV1, ReviewCommandV1, ReviewDecisionV1,
    StoredSnapshotV1, canonical_bytes, parse_json, validate_model,
)
from app.core.baseline_files import validate_path
from app.core.baseline_review import approval_blockers
SCHEMA = [
    '''CREATE TABLE projects(project_id TEXT PRIMARY KEY, content BLOB NOT NULL)''',
    '''CREATE TABLE project_state(project_id TEXT PRIMARY KEY REFERENCES projects(project_id),
        review_sequence INTEGER NOT NULL CHECK(typeof(review_sequence)='integer' AND review_sequence BETWEEN 0 AND 9007199254740991),
        head_digest TEXT, active_digest TEXT,
        FOREIGN KEY(project_id,head_digest) REFERENCES snapshots(project_id,digest),
        FOREIGN KEY(project_id,active_digest) REFERENCES snapshots(project_id,digest),
        CHECK(active_digest IS NULL OR active_digest=head_digest))''',
    '''CREATE TABLE snapshots(project_id TEXT NOT NULL REFERENCES projects(project_id),
        digest TEXT NOT NULL, parent_digest TEXT, content BLOB NOT NULL,
        PRIMARY KEY(project_id,digest),
        FOREIGN KEY(project_id,parent_digest) REFERENCES snapshots(project_id,digest),
        CHECK(parent_digest IS NULL OR parent_digest<>digest))''',
    '''CREATE TABLE reviews(project_id TEXT NOT NULL, sequence INTEGER NOT NULL CHECK(sequence>0),
        request_id TEXT NOT NULL, subject_digest TEXT NOT NULL, content BLOB NOT NULL,
        PRIMARY KEY(project_id,sequence), UNIQUE(project_id,request_id),
        FOREIGN KEY(project_id,subject_digest) REFERENCES snapshots(project_id,digest))''',
]
for _table in ('projects','snapshots','reviews'):
    for _action in ('UPDATE','DELETE'):
        SCHEMA.append(f"CREATE TRIGGER {_table}_no_{_action.lower()} BEFORE {_action} ON {_table} BEGIN SELECT RAISE(ABORT,'immutable M0 record'); END")
SCHEMA.append("CREATE TRIGGER state_no_delete BEFORE DELETE ON project_state BEGIN SELECT RAISE(ABORT,'immutable M0 state identity'); END")
SCHEMA = tuple(SCHEMA)
del _table, _action
def _normalized(sql):
    return ' '.join(sql.strip().split())
def _now():
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%fZ')
@dataclass(frozen=True)
class LocalReviewContext:
    project_id: str
    reviewer_label: str
class ReviewStore:
    def __init__(self, path: str | Path):
        self.path = Path(path)
    @staticmethod
    def initialize(path: str | Path) -> None:
        path = validate_path(path, database=True)
        try:
            fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_RDWR, 0o600)
            os.close(fd)
        except FileExistsError:
            raise M0Error('STORE_EXISTS') from None
        except OSError:
            raise M0Error('STORE_FAILURE') from None
        con = None
        try:
            con = sqlite3.connect(path,isolation_level=None)
            with con:
                con.execute('PRAGMA foreign_keys=ON')
                con.execute('PRAGMA journal_mode=DELETE')
                con.execute('PRAGMA synchronous=FULL')
                con.execute('BEGIN IMMEDIATE')
                for sql in SCHEMA:
                    con.execute(sql)
                con.execute('PRAGMA user_version=1')
                con.execute('COMMIT')
        except sqlite3.Error:
            raise M0Error('STORE_FAILURE') from None
        finally:
            if con is not None:
                con.close()
    def _sqlite_error(self, exc, write):
        message = str(exc).lower()
        if 'locked' in message or 'busy' in message:
            return M0Error('STORE_BUSY')
        if not write and 'readonly' in message and Path(str(self.path)+'-journal').exists():
            return M0Error('RECOVERY_REQUIRED')
        if 'malformed' in message or 'not a database' in message:
            return M0Error('INTEGRITY_ERROR')
        return M0Error('STORE_FAILURE')
    @contextmanager
    def _open(self, write=False):
        path = validate_path(self.path, database=True)
        if not path.exists():
            raise M0Error('STORE_NOT_FOUND')
        con = None
        try:
            con=sqlite3.connect(path.as_uri()+('?mode=rw' if write else '?mode=ro'),uri=True,isolation_level=None,timeout=5)
            con.row_factory=sqlite3.Row
            con.execute('PRAGMA foreign_keys=ON')
            con.execute('PRAGMA busy_timeout=5000')
            if con.execute('PRAGMA foreign_keys').fetchone()[0]!=1:
                raise M0Error('STORE_FAILURE')
            if con.execute('PRAGMA user_version').fetchone()[0]!=1:
                raise M0Error('UNSUPPORTED_VERSION')
            actual={_normalized(r[0]) for r in con.execute("SELECT sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%' AND sql IS NOT NULL")}
            if actual!={_normalized(sql) for sql in SCHEMA}:
                raise M0Error('INTEGRITY_ERROR')
            # Check identity before any persistent PRAGMA can change an unrelated DB.
            if write:
                mode=con.execute('PRAGMA journal_mode=DELETE').fetchone()[0]
                con.execute('PRAGMA synchronous=FULL')
                if mode!='delete' or con.execute('PRAGMA synchronous').fetchone()[0]!=2:
                    raise M0Error('STORE_FAILURE')
            if not write:
                con.execute('BEGIN')
            yield con
        except sqlite3.Error as exc:
            raise self._sqlite_error(exc,write) from None
        except OSError:
            raise M0Error('STORE_FAILURE') from None
        finally:
            if con is not None:
                con.close()
    def _checkpoint(self, stage):
        """Replaceable fault seam for offline crash/transaction verification."""
    @contextmanager
    def _transaction(self):
        with self._open(write=True) as con:
            con.execute('BEGIN IMMEDIATE')
            committing=False
            try:
                yield con
                self._checkpoint('before_commit')
                committing=True
                con.execute('COMMIT')
                self._checkpoint('committed')
            except (sqlite3.Error,OSError) as exc:
                if committing:
                    raise M0Error('COMMIT_OUTCOME_UNKNOWN') from None
                if con.in_transaction:
                    con.execute('ROLLBACK')
                if isinstance(exc,sqlite3.Error):
                    raise self._sqlite_error(exc,True) from None
                raise M0Error('STORE_FAILURE') from None
            except BaseException:
                if con.in_transaction:
                    con.execute('ROLLBACK')
                raise
    def _decode(self, cls, blob):
        try:
            value=validate_model(cls,parse_json(bytes(blob)))
            if canonical_bytes(value)!=bytes(blob):
                raise M0Error('INTEGRITY_ERROR')
            return value
        except (M0Error,TypeError,ValueError):
            raise M0Error('INTEGRITY_ERROR') from None
    def _project(self,con,project_id):
        row=con.execute('SELECT content FROM projects WHERE project_id=?',(project_id,)).fetchone()
        if row is None:
            raise M0Error('UNKNOWN_PROJECT')
        project=self._decode(ProjectRecordV1,row['content'])
        if project.project_id!=project_id:
            raise M0Error('INTEGRITY_ERROR')
        return project
    def _snapshot(self,con,project_id,digest):
        row=con.execute('SELECT * FROM snapshots WHERE project_id=? AND digest=?',(project_id,digest)).fetchone()
        if row is None:
            if con.execute('SELECT 1 FROM snapshots WHERE digest=?',(digest,)).fetchone():
                raise M0Error('PROJECT_MISMATCH')
            raise M0Error('UNKNOWN_SUBJECT')
        snap=self._decode(BaselineSnapshotV1,row['content'])
        if (snap.project_id,snap.digest,snap.parent_digest)!=(project_id,digest,row['parent_digest']):
            raise M0Error('INTEGRITY_ERROR')
        return snap
    def _lineage(self,con,snapshot):
        if snapshot.parent_digest is None:
            return
        parent=self._snapshot(con,snapshot.project_id,snapshot.parent_digest)
        old_r={r.requirement_id:r for r in parent.requirements}
        new_r={r.requirement_id:r for r in snapshot.requirements}
        old_c={c.criterion_id:c for c in parent.criteria}
        new_c={c.criterion_id:c for c in snapshot.criteria}
        old_s={s.evidence_id:s for s in parent.sources}
        new_s={s.evidence_id:s for s in snapshot.sources}
        if not old_r.keys()<=new_r.keys() or not old_c.keys()<=new_c.keys() or not old_s.keys()<=new_s.keys():
            raise M0Error('PARENT_ID_LOSS')
        if any(r.legacy!=new_r[key].legacy for key,r in old_r.items()) or any(s!=new_s[key] for key,s in old_s.items()) or any(c.requirement_id!=new_c[key].requirement_id for key,c in old_c.items()):
            raise M0Error('PARENT_ID_LOSS')
    def _state(self,con,project_id):
        project=self._project(con,project_id)
        state=con.execute('SELECT * FROM project_state WHERE project_id=?',(project_id,)).fetchone()
        if state is None:
            raise M0Error('INTEGRITY_ERROR')
        active=head=None
        history=[]
        statuses={}
        for row in con.execute('SELECT * FROM reviews WHERE project_id=? ORDER BY sequence',(project_id,)):
            r=self._decode(ReviewDecisionV1,row['content'])
            if (r.project_id,r.sequence,r.request_id,r.subject_digest)!=(project_id,row['sequence'],row['request_id'],row['subject_digest']) or r.sequence!=len(history)+1 or r.expected_sequence!=len(history) or r.reviewer_label!=project.reviewer_label or r.previous_active_digest!=active:
                raise M0Error('INTEGRITY_ERROR')
            s=self._snapshot(con,project_id,r.subject_digest)
            try:
                self._lineage(con,s)
            except M0Error:
                raise M0Error('INTEGRITY_ERROR') from None
            status=statuses.get(s.digest,'pending')
            if r.decision=='approve':
                if status!='pending' or s.parent_digest!=head or approval_blockers(s):
                    raise M0Error('INTEGRITY_ERROR')
                if active is not None:
                    statuses[active]='superseded'
                active=head=s.digest
                statuses[s.digest]='approved'
            elif r.decision=='reject':
                if status!='pending':
                    raise M0Error('INTEGRITY_ERROR')
                statuses[s.digest]='rejected'
            else:
                if status!='approved' or active!=s.digest:
                    raise M0Error('INTEGRITY_ERROR')
                active=None
                statuses[s.digest]='revoked'
            if r.resulting_active_digest!=active:
                raise M0Error('INTEGRITY_ERROR')
            history.append(r)
        if (state['review_sequence'],state['active_digest'],state['head_digest'])!=(len(history),active,head):
            raise M0Error('INTEGRITY_ERROR')
        return project,state,history,statuses
    def create_project(self,project_id: str,reviewer_label: str) -> ProjectRecordV1:
        project=validate_model(ProjectRecordV1,dict(schema_version=1,project_id=project_id,reviewer_label=reviewer_label,created_at=_now()))
        with self._transaction() as con:
            if con.execute('SELECT 1 FROM projects WHERE project_id=?',(project_id,)).fetchone():
                raise M0Error('PROJECT_EXISTS')
            con.execute('INSERT INTO projects VALUES(?,?)',(project_id,canonical_bytes(project)))
            con.execute('INSERT INTO project_state VALUES(?,0,NULL,NULL)',(project_id,))
        return project
    def store_snapshot(self,snapshot: BaselineSnapshotV1) -> StoredSnapshotV1:
        snapshot=validate_model(BaselineSnapshotV1,snapshot)
        content=canonical_bytes(snapshot)
        with self._transaction() as con:
            self._state(con,snapshot.project_id)
            self._lineage(con,snapshot)
            row=con.execute('SELECT content FROM snapshots WHERE project_id=? AND digest=?',(snapshot.project_id,snapshot.digest)).fetchone()
            created=row is None
            if row is not None and bytes(row['content'])!=content:
                raise M0Error('INTEGRITY_ERROR')
            if created:
                con.execute('INSERT INTO snapshots VALUES(?,?,?,?)',(snapshot.project_id,snapshot.digest,snapshot.parent_digest,content))
        return StoredSnapshotV1(schema_version=1,project_id=snapshot.project_id,digest=snapshot.digest,created=created)
    def local_context(self,project_id: str) -> LocalReviewContext:
        # Used only by an explicitly requested review command; a write-mode open
        # permits SQLite rollback-journal recovery before reviewer lookup.
        with self._open(write=True) as con:
            project=self._project(con,project_id)
        return LocalReviewContext(project_id,project.reviewer_label)
    def record_review(self,command: ReviewCommandV1,trusted_local_context: LocalReviewContext) -> ReviewDecisionV1:
        command=validate_model(ReviewCommandV1,command)
        if len(canonical_bytes(command))>65536:
            raise M0Error('LIMIT_EXCEEDED')
        result=None
        with self._transaction() as con:
            project,state,history,statuses=self._state(con,command.project_id)
            if not isinstance(trusted_local_context,LocalReviewContext) or (trusted_local_context.project_id,trusted_local_context.reviewer_label)!=(project.project_id,project.reviewer_label):
                raise M0Error('PROJECT_MISMATCH')
            previous=next((r for r in history if r.request_id==command.request_id),None)
            if previous is not None:
                stored={k:previous.model_dump(mode='json')[k] for k in ReviewCommandV1.model_fields}
                if canonical_bytes(stored)!=canonical_bytes(command):
                    raise M0Error('REQUEST_ID_CONFLICT')
                result=previous
            else:
                if state['review_sequence']!=command.expected_sequence:
                    raise M0Error('STALE_SEQUENCE')
                if state['review_sequence']==MAX_SEQUENCE:
                    raise M0Error('SEQUENCE_EXHAUSTED')
                snap=self._snapshot(con,command.project_id,command.subject_digest)
                self._lineage(con,snap)
                status=statuses.get(snap.digest,'pending')
                active=state['active_digest']
                head=state['head_digest']
                if command.decision in ('approve','reject') and status!='pending' or command.decision=='revoke' and (status!='approved' or active!=snap.digest):
                    raise M0Error('INVALID_TRANSITION')
                if command.decision=='approve':
                    if snap.parent_digest!=head:
                        raise M0Error('LINEAGE_CONFLICT')
                    if approval_blockers(snap):
                        raise M0Error('NOT_APPROVABLE')
                    active=head=snap.digest
                elif command.decision=='revoke':
                    active=None
                result=validate_model(ReviewDecisionV1,dict(**command.model_dump(mode='json'),sequence=state['review_sequence']+1,
                    reviewer_label=project.reviewer_label,recorded_at=_now(),previous_active_digest=state['active_digest'],resulting_active_digest=active))
                con.execute('INSERT INTO reviews VALUES(?,?,?,?,?)',(project.project_id,result.sequence,result.request_id,result.subject_digest,canonical_bytes(result)))
                self._checkpoint('decision_inserted')
                con.execute('UPDATE project_state SET review_sequence=?,head_digest=?,active_digest=? WHERE project_id=?',(result.sequence,head,active,project.project_id))
        return result
    def _effective(self,con,project_id,digest,state,history,statuses):
        snap=self._snapshot(con,project_id,digest)
        self._lineage(con,snap)
        matching=[r for r in history if r.subject_digest==digest]
        return EffectiveReviewV1(schema_version=1,project_id=project_id,subject_digest=digest,
            status=statuses.get(digest,'pending'),decision_sequence=matching[-1].sequence if matching else None,
            project_sequence=state['review_sequence'],active_digest=state['active_digest'],head_digest=state['head_digest'])
    def get_effective_review(self,project_id: str,digest: str) -> EffectiveReviewV1:
        with self._open() as con:
            _,state,history,statuses=self._state(con,project_id)
            return self._effective(con,project_id,digest,state,history,statuses)
    def inspect(self,project_id: str,digest: str) -> InspectionV1:
        with self._open() as con:
            project,state,history,statuses=self._state(con,project_id)
            return InspectionV1(schema_version=1,project=project,snapshot=self._snapshot(con,project_id,digest),
                review=self._effective(con,project_id,digest,state,history,statuses))
    def history(self,project_id: str,after_sequence: int=0,limit: int=100) -> HistoryPageV1:
        if type(after_sequence) is not int or not 0<=after_sequence<=MAX_SEQUENCE or type(limit) is not int or not 1<=limit<=1000:
            raise M0Error('INVALID_INPUT')
        with self._open() as con:
            _,_,history,_=self._state(con,project_id)
            selected=[r for r in history if r.sequence>after_sequence]
            page=tuple(selected[:limit])
            return HistoryPageV1(schema_version=1,project_id=project_id,decisions=page,
                next_after_sequence=page[-1].sequence if len(selected)>limit else None)
