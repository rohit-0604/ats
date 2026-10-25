"""Single-project M2-R custody and append-only decision transactions."""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
import os
from pathlib import Path
import sqlite3
from uuid import uuid4
from typing import Iterator, TypeVar
from pydantic import BaseModel

from app.baseline_contracts import MAX_INPUT, MAX_SEQUENCE, ProjectRecordV1, M0Error, parse_json, validate_model
from app.plan_contracts import parse_plan, canonical_plan_bytes, PlanError
from app.artifact_contracts import parse_artifact_package, canonical_artifact_bytes, ArtifactError
from app.core.baseline_files import validate_path
from app.core.review_store import ReviewStore
from app.review_contracts import (
    MAX_RECORD, POLICY_VERSION, StoreMetadataV1, ReviewSubjectV1, StoredReviewSubjectV1,
    ReviewCommandV1, ReviewDecisionV1, RegistrationV1, HistoryPageV1, ReviewError,
    canonical_review_bytes, translated,
)

APPLICATION_ID = 0x41545352
Record = TypeVar('Record', bound=BaseModel)
SCHEMA = [
    'CREATE TABLE store_metadata(id INTEGER PRIMARY KEY CHECK(id=1), content BLOB NOT NULL)',
    '''CREATE TABLE subjects(kind TEXT NOT NULL CHECK(kind IN ('plan','package')),
        digest TEXT NOT NULL, baseline_digest TEXT NOT NULL, plan_digest TEXT NOT NULL,
        parent_kind TEXT, parent_digest TEXT, content BLOB NOT NULL, registered_at TEXT NOT NULL,
        PRIMARY KEY(kind,digest), FOREIGN KEY(parent_kind,parent_digest) REFERENCES subjects(kind,digest),
        CHECK((kind='plan' AND parent_kind IS NULL AND parent_digest IS NULL AND plan_digest=digest)
            OR (kind='package' AND parent_kind='plan' AND parent_digest=plan_digest)))''',
    '''CREATE TABLE decisions(sequence INTEGER PRIMARY KEY CHECK(typeof(sequence)='integer'
        AND sequence BETWEEN 1 AND 9007199254740991), request_id TEXT NOT NULL UNIQUE,
        kind TEXT NOT NULL, digest TEXT NOT NULL, content BLOB NOT NULL,
        FOREIGN KEY(kind,digest) REFERENCES subjects(kind,digest))''',
]
for table in ('store_metadata', 'subjects', 'decisions'):
    for action in ('UPDATE', 'DELETE'):
        SCHEMA.append(f"CREATE TRIGGER {table}_no_{action.lower()} BEFORE {action} ON {table} BEGIN SELECT RAISE(ABORT,'immutable M2-R record'); END")
SCHEMA = tuple(SCHEMA)
del table, action


def now() -> str:
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%fZ')


@dataclass(frozen=True)
class LocalReviewContext:
    project_id: str
    store_id: str
    reviewer_label: str


@dataclass(frozen=True)
class ReviewSnapshot:
    metadata: StoreMetadataV1
    subjects: dict[tuple[str, str], StoredReviewSubjectV1]
    decisions: tuple[ReviewDecisionV1, ...]

    @property
    def sequence(self) -> int:
        return len(self.decisions)

    def subject(self, kind: str, digest: str) -> StoredReviewSubjectV1:
        ReviewSubjectV1(schema_version=1, project_id=self.metadata.project.project_id,
            kind=kind, subject_digest=digest, baseline_digest=digest, plan_digest=digest)
        try:
            return self.subjects[kind, digest]
        except KeyError:
            raise ReviewError('UNKNOWN_SUBJECT') from None

    def latest(self, kind: str, digest: str) -> ReviewDecisionV1 | None:
        return next((d for d in reversed(self.decisions) if (d.kind, d.subject_digest) == (kind, digest)), None)


class PackageReviewStore:
    def __init__(self, path: str | Path):
        self.path = Path(path)

    def _checkpoint(self, stage: str) -> None:
        """Fault injection seam; never dispatches an external effect."""

    @staticmethod
    def initialize(path: str | Path, project: ProjectRecordV1) -> StoreMetadataV1:
        try:
            project = validate_model(ProjectRecordV1, project)
        except (M0Error, ValueError, TypeError):
            raise ReviewError('INVALID_INPUT') from None
        metadata = StoreMetadataV1(schema_version=1, store_id=str(uuid4()), project=project,
                                   created_at=now(), policy_version=POLICY_VERSION)
        try:
            path = validate_path(path, database=True)
            fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_RDWR, 0o600)
            os.close(fd)
        except FileExistsError:
            raise ReviewError('STORE_EXISTS') from None
        except M0Error as exc:
            raise translated(exc) from None
        except OSError:
            raise ReviewError('STORE_FAILURE') from None
        con = None
        try:
            con = sqlite3.connect(path, isolation_level=None)
            con.execute('PRAGMA foreign_keys=ON')
            con.execute('PRAGMA journal_mode=DELETE')
            con.execute('PRAGMA synchronous=FULL')
            con.execute('BEGIN IMMEDIATE')
            for sql in SCHEMA:
                con.execute(sql)
            con.execute('PRAGMA user_version=1')
            con.execute(f'PRAGMA application_id={APPLICATION_ID}')
            con.execute('INSERT INTO store_metadata VALUES(1,?)', (canonical_review_bytes(metadata),))
            con.execute('COMMIT')
            return metadata
        except (sqlite3.Error, OSError):
            raise ReviewError('STORE_FAILURE') from None
        finally:
            if con is not None:
                con.close()

    def _sql_error(self, exc: sqlite3.Error, write: bool) -> ReviewError:
        text = str(exc).lower()
        if 'locked' in text or 'busy' in text:
            return ReviewError('STORE_BUSY')
        if not write and 'readonly' in text and Path(str(self.path) + '-journal').exists():
            return ReviewError('RECOVERY_REQUIRED')
        if 'malformed' in text or 'not a database' in text:
            return ReviewError('INTEGRITY_ERROR')
        return ReviewError('STORE_FAILURE')

    @contextmanager
    def _open(self, write: bool = False) -> Iterator[sqlite3.Connection]:
        con = None
        try:
            path = validate_path(self.path, database=True)
            if not path.exists():
                raise ReviewError('STORE_NOT_FOUND')
            # Reject foreign stores before a writable connection can recover them.
            # Reject WAL before even a query could create/use shared-memory files.
            with path.open('rb') as stream:
                header = stream.read(100)
            if len(header) != 100 or header[:16] != b'SQLite format 3\x00':
                raise ReviewError('INTEGRITY_ERROR')
            if int.from_bytes(header[68:72], 'big') != APPLICATION_ID:
                raise ReviewError('STORE_IDENTITY_MISMATCH')
            if int.from_bytes(header[60:64], 'big') != 1:
                raise ReviewError('UNSUPPORTED_VERSION')
            if header[18:20] != b'\x01\x01':
                raise ReviewError('INTEGRITY_ERROR')
            con = sqlite3.connect(path.as_uri() + ('?mode=rw' if write else '?mode=ro'),
                                  uri=True, isolation_level=None, timeout=5)
            con.row_factory = sqlite3.Row
            con.execute('PRAGMA foreign_keys=ON')
            con.execute('PRAGMA busy_timeout=5000')
            if con.execute('PRAGMA foreign_keys').fetchone()[0] != 1:
                raise ReviewError('STORE_FAILURE')
            if con.execute('PRAGMA application_id').fetchone()[0] != APPLICATION_ID:
                raise ReviewError('STORE_IDENTITY_MISMATCH')
            if con.execute('PRAGMA user_version').fetchone()[0] != 1:
                raise ReviewError('UNSUPPORTED_VERSION')
            actual = {' '.join(r[0].split()) for r in con.execute("SELECT sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%' AND sql IS NOT NULL")}
            if actual != {' '.join(sql.split()) for sql in SCHEMA}:
                raise ReviewError('INTEGRITY_ERROR')
            if write:
                if con.execute('PRAGMA journal_mode=DELETE').fetchone()[0] != 'delete':
                    raise ReviewError('STORE_FAILURE')
                con.execute('PRAGMA synchronous=FULL')
                if con.execute('PRAGMA synchronous').fetchone()[0] != 2:
                    raise ReviewError('STORE_FAILURE')
            else:
                con.execute('BEGIN')
            yield con
        except M0Error as exc:
            raise translated(exc) from None
        except sqlite3.Error as exc:
            raise self._sql_error(exc, write) from None
        except OSError:
            raise ReviewError('STORE_FAILURE') from None
        finally:
            if con is not None:
                con.close()

    @contextmanager
    def _transaction(self) -> Iterator[sqlite3.Connection]:
        with self._open(write=True) as con:
            con.execute('BEGIN IMMEDIATE')
            committing = False
            try:
                yield con
                self._checkpoint('before_commit')
                committing = True
                con.execute('COMMIT')
                self._checkpoint('committed')
            except (sqlite3.Error, OSError) as exc:
                if committing:
                    raise ReviewError('COMMIT_OUTCOME_UNKNOWN') from None
                if con.in_transaction:
                    con.execute('ROLLBACK')
                if isinstance(exc, sqlite3.Error):
                    raise self._sql_error(exc, True) from None
                raise ReviewError('STORE_FAILURE') from None
            except BaseException as exc:
                if con.in_transaction:
                    con.execute('ROLLBACK')
                if committing and isinstance(exc, KeyboardInterrupt):
                    error = ReviewError('COMMIT_OUTCOME_UNKNOWN')
                    error.interrupted = True
                    raise error from None
                raise

    @staticmethod
    def _decode(cls: type[Record], blob: bytes) -> Record:
        try:
            raw = bytes(blob)
            result = cls.model_validate(parse_json(raw, MAX_RECORD))
            if canonical_review_bytes(result) != raw:
                raise ReviewError('INTEGRITY_ERROR')
            return result
        except (M0Error, PlanError, ArtifactError, ReviewError, ValueError, TypeError):
            raise ReviewError('INTEGRITY_ERROR') from None

    def _load(self, con: sqlite3.Connection) -> ReviewSnapshot:
        if con.execute('SELECT count(*) FROM store_metadata').fetchone()[0] != 1:
            raise ReviewError('INTEGRITY_ERROR')
        if con.execute('SELECT count(*) FROM store_metadata WHERE length(content)>?', (MAX_RECORD,)).fetchone()[0]:
            raise ReviewError('INTEGRITY_ERROR')
        row = con.execute('SELECT content FROM store_metadata WHERE id=1').fetchone()
        if row is None:
            raise ReviewError('INTEGRITY_ERROR')
        metadata = self._decode(StoreMetadataV1, row[0])
        if con.execute('SELECT count(*) FROM subjects WHERE length(content)>?', (MAX_INPUT,)).fetchone()[0] or con.execute('SELECT count(*) FROM decisions WHERE length(content)>?', (MAX_RECORD,)).fetchone()[0]:
            raise ReviewError('INTEGRITY_ERROR')
        subjects = {}
        try:
            for row in con.execute('SELECT * FROM subjects'):
                raw = bytes(row['content'])
                value = parse_plan(raw) if row['kind'] == 'plan' else parse_artifact_package(raw)
                canonical = canonical_plan_bytes(value) if row['kind'] == 'plan' else canonical_artifact_bytes(value)
                project = value.project_id if row['kind'] == 'plan' else value.manifest.project_id
                baseline = value.baseline_digest if row['kind'] == 'plan' else value.manifest.baseline_digest
                plan = value.digest if row['kind'] == 'plan' else value.manifest.plan_digest
                if (canonical != raw or project != metadata.project.project_id
                        or (value.digest, baseline, plan) != (row['digest'], row['baseline_digest'], row['plan_digest'])
                        or (row['parent_kind'], row['parent_digest']) != (('plan', plan) if row['kind'] == 'package' else (None, None))):
                    raise ReviewError('INTEGRITY_ERROR')
                subject = ReviewSubjectV1(schema_version=1, project_id=project, kind=row['kind'],
                    subject_digest=value.digest, baseline_digest=baseline, plan_digest=plan)
                subjects[row['kind'], value.digest] = StoredReviewSubjectV1(schema_version=1,
                    subject=subject, registered_at=row['registered_at'], canonical_content=raw)
            for stored in subjects.values():
                if stored.subject.kind == 'package':
                    parent = subjects.get(('plan', stored.subject.plan_digest))
                    if parent is None or parent.subject.baseline_digest != stored.subject.baseline_digest:
                        raise ReviewError('INTEGRITY_ERROR')
            history = []
            latest = {}
            requests = set()
            for row in con.execute('SELECT * FROM decisions ORDER BY sequence'):
                d = self._decode(ReviewDecisionV1, row['content'])
                key = d.kind, d.subject_digest
                previous = latest.get(key)
                if (d.store_id != metadata.store_id or d.project_id != metadata.project.project_id
                        or d.reviewer_label != metadata.project.reviewer_label or key not in subjects
                        or (d.sequence, d.request_id, d.kind, d.subject_digest) != (row['sequence'], row['request_id'], row['kind'], row['digest'])
                        or d.sequence != len(history) + 1 or d.request_id in requests
                        or d.previous_decision_sequence != (previous.sequence if previous else None)):
                    raise ReviewError('INTEGRITY_ERROR')
                self._transition(d.decision, previous)
                if d.decision == 'approve' and d.kind == 'package':
                    parent = latest.get(('plan', subjects[key].subject.plan_digest))
                    if (parent is None or parent.decision != 'approve' or parent.sequence != d.parent_plan_approval_sequence
                            or parent.baseline_approval_sequence != d.baseline_approval_sequence):
                        raise ReviewError('INTEGRITY_ERROR')
                latest[key] = d
                requests.add(d.request_id)
                history.append(d)
            if con.execute('PRAGMA foreign_key_check').fetchone() is not None:
                raise ReviewError('INTEGRITY_ERROR')
            return ReviewSnapshot(metadata, subjects, tuple(history))
        except (M0Error, PlanError, ArtifactError, ReviewError, ValueError, TypeError, KeyError):
            raise ReviewError('INTEGRITY_ERROR') from None

    @staticmethod
    def _transition(decision: str, previous: ReviewDecisionV1 | None) -> None:
        approved = previous is not None and previous.decision == 'approve'
        if decision == 'revoke' and not approved or decision == 'reject' and approved:
            raise ReviewError('INVALID_TRANSITION')

    def snapshot(self, *, for_write: bool = False) -> ReviewSnapshot:
        with self._open(write=for_write) as con:
            if for_write:
                con.execute('BEGIN')
            return self._load(con)

    def local_context(self) -> LocalReviewContext:
        # Called by the explicit local review path, never by queries/assessment.
        # Like a review write, it may recover this store's interrupted transaction.
        m = self.snapshot(for_write=True).metadata
        return LocalReviewContext(m.project.project_id, m.store_id, m.project.reviewer_label)

    def register(self, stored: StoredReviewSubjectV1, project: ProjectRecordV1) -> RegistrationV1:
        stored = StoredReviewSubjectV1.model_validate(stored)
        with self._transaction() as con:
            view = self._load(con)
            s = stored.subject
            if project != view.metadata.project or s.project_id != project.project_id:
                raise ReviewError('AUTHORITY_MISMATCH')
            existing = view.subjects.get((s.kind, s.subject_digest))
            if existing is not None:
                if existing.canonical_content != stored.canonical_content or existing.subject != s:
                    raise ReviewError('SUBJECT_CONFLICT')
                return RegistrationV1(schema_version=1, subject=s, created=False)
            if s.kind == 'package':
                parent = view.subject('plan', s.plan_digest)
                if parent.subject.baseline_digest != s.baseline_digest:
                    raise ReviewError('AUTHORITY_MISMATCH')
            con.execute('INSERT INTO subjects VALUES(?,?,?,?,?,?,?,?)', (s.kind, s.subject_digest,
                s.baseline_digest, s.plan_digest, 'plan' if s.kind == 'package' else None,
                s.plan_digest if s.kind == 'package' else None, stored.canonical_content, stored.registered_at))
            self._checkpoint('subject_inserted')
        return RegistrationV1(schema_version=1, subject=s, created=True)

    def record_review(self, command: ReviewCommandV1, context: LocalReviewContext,
                      baseline_store: ReviewStore | None = None) -> ReviewDecisionV1:
        command = ReviewCommandV1.model_validate(command)
        with self._transaction() as con:
            view = self._load(con)
            m = view.metadata
            if not isinstance(context, LocalReviewContext) or context != LocalReviewContext(m.project.project_id, m.store_id, m.project.reviewer_label):
                raise ReviewError('LOCAL_CONTEXT_REQUIRED')
            if command.project_id != m.project.project_id:
                raise ReviewError('AUTHORITY_MISMATCH')
            original = next((d for d in view.decisions if d.request_id == command.request_id), None)
            if original is not None:
                fields = {k: getattr(original, k) for k in ReviewCommandV1.model_fields}
                if canonical_review_bytes(fields) != canonical_review_bytes(command):
                    raise ReviewError('REQUEST_ID_CONFLICT')
                return original
            if command.expected_sequence != view.sequence:
                raise ReviewError('STALE_SEQUENCE')
            if view.sequence == MAX_SEQUENCE:
                raise ReviewError('SEQUENCE_EXHAUSTED')
            stored = view.subject(command.kind, command.subject_digest)
            previous = view.latest(command.kind, command.subject_digest)
            self._transition(command.decision, previous)
            baseline_token = parent_token = None
            if command.decision == 'approve':
                from app.core.package_review_service import approval_tokens
                baseline_token, parent_token = approval_tokens(view, stored, baseline_store, command.expected_m0_sequence)
            decision = ReviewDecisionV1(**command.model_dump(mode='python'), store_id=m.store_id,
                sequence=view.sequence + 1, recorded_at=now(), reviewer_label=m.project.reviewer_label,
                previous_decision_sequence=previous.sequence if previous else None,
                baseline_approval_sequence=baseline_token, parent_plan_approval_sequence=parent_token)
            con.execute('INSERT INTO decisions VALUES(?,?,?,?,?)', (decision.sequence, decision.request_id,
                decision.kind, decision.subject_digest, canonical_review_bytes(decision)))
            self._checkpoint('decision_inserted')
        return decision

    def inspect_subject(self, kind: str, digest: str) -> dict[str, object]:
        view = self.snapshot()
        stored = view.subject(kind, digest)
        d = view.latest(kind, digest)
        return dict(schema_version=1, store_id=view.metadata.store_id, subject=stored.subject.model_dump(mode='json'),
            registered_at=stored.registered_at, size_bytes=len(stored.canonical_content),
            review_sequence=view.sequence, latest_decision=d.model_dump(mode='json') if d else None,
            raw_status={'approve': 'approved', 'reject': 'rejected', 'revoke': 'revoked'}[d.decision] if d else 'pending')

    def inspect_history(self, after: int = 0, limit: int = 100) -> HistoryPageV1:
        if type(after) is not int or not 0 <= after <= MAX_SEQUENCE or type(limit) is not int or not 1 <= limit <= 1000:
            raise ReviewError('INVALID_INPUT')
        view = self.snapshot()
        remaining = tuple(d for d in view.decisions if d.sequence > after)
        page = remaining[:limit]
        return HistoryPageV1(schema_version=1, store_id=view.metadata.store_id,
            project_id=view.metadata.project.project_id, observed_sequence=view.sequence,
            decisions=page, next_after_sequence=page[-1].sequence if len(remaining) > limit else None)

    def export_subject(self, kind: str, digest: str) -> bytes:
        return self.snapshot().subject(kind, digest).canonical_content
