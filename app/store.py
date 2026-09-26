import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta

from domain.charge_rules import canonical, digest


def now():
    return datetime.now(UTC).isoformat()


class PolicyError(ValueError):
    pass


class Store:
    def __init__(self, path):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with self.connection() as db:
            db.executescript("""
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS runs (
                    id TEXT PRIMARY KEY, fixture TEXT NOT NULL UNIQUE,
                    session_id TEXT UNIQUE, issue_id TEXT NOT NULL, team_id TEXT NOT NULL,
                    evidence TEXT, issue_snapshot TEXT, status TEXT NOT NULL DEFAULT 'created'
                );
                CREATE TABLE IF NOT EXISTS executions (
                    id TEXT PRIMARY KEY, run_id TEXT NOT NULL, spec TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS actions (
                    id TEXT PRIMARY KEY, run_id TEXT NOT NULL, kind TEXT NOT NULL,
                    payload TEXT NOT NULL, plan_hash TEXT NOT NULL, expires_at TEXT NOT NULL,
                    status TEXT NOT NULL, proof TEXT, result TEXT
                );
                CREATE UNIQUE INDEX IF NOT EXISTS one_reserved_action
                ON actions(run_id,kind) WHERE status IN ('executing','uncertain','succeeded');
                CREATE TABLE IF NOT EXISTS audit (
                    id INTEGER PRIMARY KEY, created_at TEXT NOT NULL,
                    run_id TEXT NOT NULL, event TEXT NOT NULL, details TEXT NOT NULL
                );
            """)

    @contextmanager
    def connection(self):
        db = sqlite3.connect(self.path, timeout=10)
        try:
            db.row_factory = sqlite3.Row
            with db:
                yield db
        finally:
            db.close()

    def audit(self, run_id, event, details):
        with self.connection() as db:
            db.execute(
                "INSERT INTO audit(created_at,run_id,event,details) VALUES (?,?,?,?)",
                (now(), run_id, event, canonical(details)),
            )

    def create_run(self, issue_id, team_id):
        with self.connection() as db:
            existing = db.execute(
                "SELECT * FROM runs WHERE issue_id=? AND team_id=? ORDER BY rowid DESC LIMIT 1",
                (issue_id, team_id),
            ).fetchone()
            if existing:
                return dict(existing)
            db.execute(
                "INSERT OR IGNORE INTO runs(id,fixture,issue_id,team_id) VALUES (?,?,?,?)",
                (str(uuid.uuid4()), "TEL-1042:" + issue_id, issue_id, team_id),
            )
            row = db.execute(
                "SELECT * FROM runs WHERE issue_id=? AND team_id=? ORDER BY rowid DESC LIMIT 1",
                (issue_id, team_id),
            ).fetchone()
        if not row:
            raise PolicyError("Could not create an idempotent run for the selected ticket")
        return dict(row)

    def run(self, run_id):
        with self.connection() as db:
            row = db.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone()
        if not row:
            raise PolicyError("Unknown run")
        result = dict(row)
        for field in ("evidence", "issue_snapshot"):
            if result[field]:
                result[field] = json.loads(result[field])
        return result

    def latest_run(self):
        with self.connection() as db:
            row = db.execute("SELECT id FROM runs ORDER BY rowid DESC LIMIT 1").fetchone()
        return self.run(row[0]) if row else None

    def actions_for_run(self, run_id):
        with self.connection() as db:
            rows = db.execute(
                "SELECT * FROM actions WHERE run_id=? ORDER BY rowid", (run_id,)
            ).fetchall()
        actions = []
        for row in rows:
            action = dict(row)
            for field in ("payload", "proof", "result"):
                if action[field]:
                    action[field] = json.loads(action[field])
            actions.append(action)
        return actions

    def audit_for_run(self, run_id, limit=50):
        with self.connection() as db:
            rows = db.execute(
                "SELECT created_at,event,details FROM audit WHERE run_id=? "
                "ORDER BY id DESC LIMIT ?",
                (run_id, limit),
            ).fetchall()
        return [
            {
                "created_at": row["created_at"],
                "event": row["event"],
                "details": json.loads(row["details"]),
            }
            for row in reversed(rows)
        ]

    def update_run(self, run_id, **fields):
        if not fields or set(fields) - {"session_id", "evidence", "issue_snapshot", "status"}:
            raise PolicyError("Unsupported state update")
        values = [canonical(v) if isinstance(v, dict) else v for v in fields.values()]
        with self.connection() as db:
            db.execute(
                f"UPDATE runs SET {','.join(k + '=?' for k in fields)} WHERE id=?",
                [*values, run_id],
            )

    def save_execution(self, run_id, spec):
        execution_id = digest(spec)
        with self.connection() as db:
            db.execute(
                "INSERT OR IGNORE INTO executions VALUES (?,?,?)",
                (execution_id, run_id, canonical(spec)),
            )
        return execution_id

    def execution(self, run_id, execution_id):
        with self.connection() as db:
            row = db.execute(
                "SELECT spec FROM executions WHERE id=? AND run_id=?", (execution_id, run_id)
            ).fetchone()
        if not row:
            raise PolicyError("Unknown execution")
        return json.loads(row[0])

    def prepare(self, run_id, kind, payload):
        content = {key: value for key, value in payload.items() if key != "version"}
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            existing = db.execute(
                "SELECT id,payload FROM actions WHERE run_id=? AND kind=? "
                "AND status='pending' AND expires_at>?",
                (run_id, kind, now()),
            ).fetchone()
            if existing:
                previous = json.loads(existing["payload"])
                if {key: value for key, value in previous.items() if key != "version"} == content:
                    return self.action(existing["id"])
            version = (
                db.execute(
                    "SELECT COUNT(*) FROM actions WHERE run_id=? AND kind=?", (run_id, kind)
                ).fetchone()[0]
                + 1
            )
            payload = content | {"version": version}
            plan_hash = digest(payload)
            db.execute(
                "UPDATE actions SET status='revoked' WHERE run_id=? AND kind=? "
                "AND status='pending'",
                (run_id, kind),
            )
            action_id = str(uuid.uuid4())
            expires = (datetime.now(UTC) + timedelta(minutes=15)).isoformat()
            db.execute(
                "INSERT INTO actions(id,run_id,kind,payload,plan_hash,expires_at,status) "
                "VALUES (?,?,?,?,?,?,'pending')",
                (action_id, run_id, kind, canonical(payload), plan_hash, expires),
            )
        return self.action(action_id)

    def action(self, action_id):
        with self.connection() as db:
            row = db.execute("SELECT * FROM actions WHERE id=?", (action_id,)).fetchone()
        if not row:
            raise PolicyError("Unknown approval")
        action = dict(row)
        for field in ("payload", "proof", "result"):
            if action[field]:
                action[field] = json.loads(action[field])
        return action

    def reserve(self, action_id, proof):
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            try:
                cursor = db.execute(
                    "UPDATE actions SET status='executing',proof=? "
                    "WHERE id=? AND status='pending' AND expires_at>?",
                    (canonical(proof), action_id, now()),
                )
            except sqlite3.IntegrityError as exc:
                raise PolicyError("An action was already attempted for this run") from exc
            if cursor.rowcount != 1:
                raise PolicyError("Approval is expired, consumed, or not pending")

    def finish(self, action_id, status, result=None):
        if status not in {"succeeded", "uncertain", "rejected", "revoked"}:
            raise PolicyError("Unsupported action state")
        with self.connection() as db:
            db.execute(
                "UPDATE actions SET status=?,result=? WHERE id=?",
                (status, canonical(result or {}), action_id),
            )

    def succeeded(self, run_id, kind):
        with self.connection() as db:
            row = db.execute(
                "SELECT id FROM actions WHERE run_id=? AND kind=? AND status='succeeded'",
                (run_id, kind),
            ).fetchone()
        return self.action(row[0]) if row else None
