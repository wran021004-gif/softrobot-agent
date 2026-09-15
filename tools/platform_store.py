"""Local trusted-host SQLite ledger. Transactions cover rows and immutable blobs.

Working directories are not transactions. External side effects can finish without
a commit; such reservations remain unknown and are never automatically replayed.
"""
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
from uuid import uuid4
from schemas.platform import Budget, EvidenceRef, ProjectConfig, Event, VERSION
from tools.spec_tools import ROOT
from tools.state_io import digest


def plain(value):
    return value.model_dump(mode='json') if hasattr(value, 'model_dump') else value


def encode(value):
    return json.dumps(plain(value), ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


def zero():
    return dict(tool_calls=0, model_calls=0, backend_solves=0, worker_calls=0, wall_s=0.)


def now():
    return datetime.now(timezone.utc).isoformat()


class Store:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.db = self.root / 'platform.sqlite'

    def connect(self, readonly=False):
        if readonly:
            db = sqlite3.connect(self.db.as_uri() + '?mode=ro', uri=True, timeout=10)
            db.execute('PRAGMA query_only=ON')
        else:
            db = sqlite3.connect(self.db, timeout=10)
            db.execute('PRAGMA synchronous=FULL')
        db.row_factory = sqlite3.Row
        return db

    @contextmanager
    def transaction(self):
        db = self.connect()
        try:
            db.execute('BEGIN IMMEDIATE')
            self.check_root(db)
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    def create(self, config):
        config = ProjectConfig.model_validate(config)
        if any(type(n) is not int or n < 1 for n in config.exclusive_resources.values()):
            raise ValueError('INVALID_RESOURCE_CAPACITY')
        # One machine/workspace authority index: copying a project cannot mint a grant.
        # This is a trusted local anchor, NOT authentication or tamper resistance.
        anchor = ROOT / 'runs' / '.platform_authorities.sqlite'
        anchor.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(anchor, timeout=10) as db:
            db.execute('CREATE TABLE IF NOT EXISTS grants (grant_id TEXT PRIMARY KEY, root TEXT, config_hash TEXT)')
            db.execute('BEGIN IMMEDIATE')
            prior = db.execute('SELECT root,config_hash FROM grants WHERE grant_id=?', (config.grant_id,)).fetchone()
            if prior and prior != (str(self.root), digest(plain(config))):
                raise ValueError('GRANT_ALREADY_BOUND: 复制目录不产生新额度')
            if self.db.exists():
                raise ValueError('PROJECT_ALREADY_EXISTS')
            self.root.mkdir(parents=True, exist_ok=True)
            db.execute('INSERT OR IGNORE INTO grants VALUES (?,?,?)', (config.grant_id, str(self.root), digest(plain(config))))
        # Crash between anchor and project creation permits only same-root retry.
        with self.connect() as db:
            db.executescript('''
                CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
                CREATE TABLE artifacts (id TEXT PRIMARY KEY, media TEXT NOT NULL, body BLOB NOT NULL);
                CREATE TABLE sessions (run_id TEXT PRIMARY KEY, snapshot TEXT NOT NULL, status TEXT NOT NULL, state TEXT NOT NULL);
                CREATE TABLE calls (run_id TEXT, request_id TEXT, request_hash TEXT NOT NULL, execution_id TEXT UNIQUE,
                    caller TEXT, status TEXT, reserved TEXT, charged TEXT, resources TEXT, cache_key TEXT,
                    receipt TEXT, parent_id TEXT, PRIMARY KEY(run_id,request_id));
                CREATE TABLE events (seq INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT, body TEXT);
                CREATE TABLE memories (id TEXT PRIMARY KEY, run_id TEXT, body TEXT);
                CREATE TABLE workers (run_id TEXT, work_id TEXT, order_json TEXT, status TEXT, pid INTEGER,
                    output TEXT, reason TEXT, PRIMARY KEY(run_id,work_id));
                CREATE TABLE merges (run_id TEXT, work_id TEXT, claim_key TEXT, conclusion TEXT,
                    output TEXT, PRIMARY KEY(run_id,work_id));
            ''')
            db.executemany('INSERT INTO meta VALUES (?,?)', [('root', encode(str(self.root))), ('config', encode(config)), ('version', encode(VERSION))])
        return plain(config)

    def check_root(self, db):
        root = json.loads(db.execute("SELECT value FROM meta WHERE key='root'").fetchone()[0])
        if root != str(self.root):
            raise ValueError('PROJECT_MOVED_OR_COPIED: 只读导出可用；执行需显式迁移授权绑定')
        cfg = json.loads(db.execute("SELECT value FROM meta WHERE key='config'").fetchone()[0])
        anchor = ROOT / 'runs' / '.platform_authorities.sqlite'
        with sqlite3.connect(anchor.as_uri() + '?mode=ro', uri=True) as grants:
            row = grants.execute('SELECT root,config_hash FROM grants WHERE grant_id=?', (cfg['grant_id'],)).fetchone()
        if row != (root, digest(cfg)):
            raise ValueError('AUTHORITY_ANCHOR_MISMATCH')

    def config(self, db=None):
        if db is not None:
            return json.loads(db.execute("SELECT value FROM meta WHERE key='config'").fetchone()[0])
        with self.connect(True) as conn:
            return self.config(conn)

    def put(self, db, value, media='application/json'):
        body = value if isinstance(value, bytes) else encode(value).encode('utf8')
        identity = hashlib.sha256(body).hexdigest()
        db.execute('INSERT OR IGNORE INTO artifacts VALUES (?,?,?)', (identity, media, body))
        return EvidenceRef(artifact_id=identity, media_type=media)

    def artifact(self, ref, *, raw=False, db=None):
        ref = EvidenceRef.model_validate(ref)
        if db is None:
            with self.connect(True) as conn:
                return self.artifact(ref, raw=raw, db=conn)
        row = db.execute('SELECT body,media FROM artifacts WHERE id=?', (ref.artifact_id,)).fetchone()
        if row is None or hashlib.sha256(row['body']).hexdigest() != ref.artifact_id or row['media'] != ref.media_type:
            raise ValueError('EVIDENCE_MISSING_OR_CHANGED: ' + ref.artifact_id)
        return row['body'] if raw else json.loads(row['body'])

    def session(self, run_id, db=None):
        if db is None:
            with self.connect(True) as conn:
                return self.session(run_id, conn)
        row = db.execute('SELECT * FROM sessions WHERE run_id=?', (run_id,)).fetchone()
        if row is None:
            raise ValueError('SESSION_NOT_FOUND')
        value = dict(row)
        value['state'] = json.loads(value['state'])
        value['snapshot'] = self.artifact(EvidenceRef(artifact_id=value['snapshot']), db=db)
        return value

    def create_session(self, snapshot):
        run_id = snapshot['input']['run_id']
        with self.transaction() as db:
            reference = self.put(db, snapshot)
            db.execute('INSERT INTO sessions VALUES (?,?,?,?)', (run_id, reference.artifact_id, 'created', encode(dict(turn=0, pending=None, last_receipt=None, model_notes=[], reads={}, repairs=0, repeated=0))))
            self.event(db, run_id, 'session', 'created', outputs=[reference])
        return self.session(run_id)

    def update_state(self, db, run_id, state, status=None):
        db.execute('UPDATE sessions SET state=? WHERE run_id=?', (encode(state), run_id))
        if status:
            db.execute('UPDATE sessions SET status=? WHERE run_id=?', (status, run_id))

    def event(self, db, run_id, kind, status, *, parent=None, request=None, execution=None, caller='host', inputs=(), outputs=(), cost=None, candidate=None, version=VERSION):
        row = db.execute('INSERT INTO events(run_id,body) VALUES (?,?)', (run_id, '{}'))
        event_id = uuid4().hex
        event = Event(project_id=self.config(db)['project_id'], run_id=run_id, sequence=row.lastrowid,
                      event_id=event_id, parent_id=parent, candidate_id=candidate, agent_id=caller,
                      request_id=request, execution_id=execution, timestamp=now(), kind=kind, status=status,
                      inputs=list(inputs), outputs=list(outputs), cost=cost or zero(), implementation_version=version)
        db.execute('UPDATE events SET body=? WHERE seq=?', (encode(event), row.lastrowid))
        return event_id

    def events(self, run_id, parent=None):
        with self.connect(True) as db:
            rows = [json.loads(r[0]) for r in db.execute('SELECT body FROM events WHERE run_id=? ORDER BY seq', (run_id,))]
        if parent:
            selected = {parent}
            for row in rows:
                if row['parent_id'] in selected:
                    selected.add(row['event_id'])
            rows = [r for r in rows if r['event_id'] in selected]
        return rows

    def remaining(self, run_id=None, db=None):
        if db is None:
            with self.connect(True) as conn:
                return self.remaining(run_id, conn)
        limit = self.session(run_id, db)['snapshot']['input']['policy']['budget'] if run_id else self.config(db)['budget']
        if run_id:
            scopes = [run_id]
            for item in db.execute('SELECT run_id,snapshot FROM sessions'):
                snap = self.artifact(EvidenceRef(artifact_id=item['snapshot']), db=db)
                if snap.get('parent_run_id') == run_id:
                    scopes.append(item['run_id'])
            rows = db.execute('SELECT charged FROM calls WHERE run_id IN (' + ','.join('?' for _ in scopes) + ')', scopes)
        else:
            rows = db.execute('SELECT charged FROM calls')
        used = zero()
        for row in rows:
            for key, value in json.loads(row[0]).items():
                used[key] += value
        occupied = {}
        for row in db.execute("SELECT resources FROM calls WHERE status IN ('running','unknown')"):
            for name in json.loads(row[0]):
                occupied[name] = occupied.get(name, 0) + 1
        return dict(limit=limit, used=used, remaining={k: max(0, limit[k] - used[k]) for k in limit}, occupied=occupied)

    def lookup(self, run_id, request_id, db=None):
        if db is None:
            with self.connect(True) as conn:
                return self.lookup(run_id, request_id, conn)
        row = db.execute('SELECT * FROM calls WHERE run_id=? AND request_id=?', (run_id, request_id)).fetchone()
        return dict(row) if row else None

    def reserve(self, run_id, request_id, request_hash, caller, cost, resources=(), cache_key=None, parent=None, inputs=(), kind='tool', version=VERSION):
        Budget.model_validate(cost)
        with self.transaction() as db:
            old = self.lookup(run_id, request_id, db)
            if old:
                if old['request_hash'] != request_hash or old['caller'] != caller:
                    raise ValueError('REQUEST_ID_COLLISION')
                return old, False
            parent_run = self.session(run_id, db)['snapshot'].get('parent_run_id')
            for scope in ([None, run_id, parent_run] if parent_run else [None, run_id]):
                remainder = self.remaining(scope, db)['remaining']
                if any(cost[k] > remainder[k] + 1e-9 for k in cost):
                    raise ValueError('BUDGET_EXHAUSTED: ' + ('project' if scope is None else 'session'))
            available = self.config(db)['exclusive_resources']
            occupied = self.remaining(None, db)['occupied']
            for resource in resources:
                if resource not in available or occupied.get(resource, 0) >= available[resource]:
                    raise ValueError('RESOURCE_BUSY_OR_NOT_GRANTED: ' + resource)
            execution_id = uuid4().hex
            event_id = self.event(db, run_id, kind, 'reserved', parent=parent, request=request_id,
                                  execution=execution_id, caller=caller, inputs=inputs, cost=cost, version=version)
            db.execute('INSERT INTO calls VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',
                       (run_id, request_id, request_hash, execution_id, caller, 'running', encode(cost), encode(cost), encode(list(resources)), cache_key, None, event_id))
            # SQLite column count checked by focused tests, not separate accounting.
            return self.lookup(run_id, request_id, db), True

    def complete(self, row, receipt, output=None, elapsed=0., kind='tool'):
        with self.transaction() as db:
            current = self.lookup(row['run_id'], row['request_id'], db)
            if current['receipt']:
                return json.loads(current['receipt'])
            charged = json.loads(current['reserved'])
            # Known completion settles actual wall time. Overrun remains charged.
            charged['wall_s'] = max(0, elapsed)
            if output is not None:
                receipt['output'] = plain(self.put(db, output))
            receipt['charged'] = charged
            from schemas.platform import ToolReceipt
            parsed = ToolReceipt.model_validate(receipt)
            self.put(db, parsed)
            db.execute('UPDATE calls SET status=?,charged=?,receipt=? WHERE run_id=? AND request_id=?',
                       (parsed.execution_status, encode(charged), encode(parsed), row['run_id'], row['request_id']))
            self.event(db, row['run_id'], kind, parsed.execution_status, parent=current['parent_id'],
                       request=row['request_id'], execution=row['execution_id'], caller=row['caller'],
                       outputs=[parsed.output] if parsed.output else [], cost=charged, version=parsed.tool_version)
            return plain(parsed)

    def cache(self, run_id, key):
        with self.connect(True) as db:
            row = db.execute("SELECT receipt FROM calls WHERE run_id=? AND cache_key=? AND status='completed' ORDER BY rowid DESC LIMIT 1", (run_id, key)).fetchone()
            if row:
                value = json.loads(row[0])
                self.artifact(value['output'], db=db)
                return value
        return None

    def mark_unknown(self, run_id, request_id):
        with self.transaction() as db:
            row = self.lookup(run_id, request_id, db)
            if row and row['status'] == 'running':
                db.execute("UPDATE calls SET status='unknown' WHERE run_id=? AND request_id=?", (run_id, request_id))
                self.event(db, run_id, 'recovery', 'unknown', parent=row['parent_id'], request=request_id, execution=row['execution_id'], cost=json.loads(row['charged']))

    def save_memory(self, run_id, entry):
        with self.transaction() as db:
            for ref in entry.sources:
                self.artifact(ref, db=db)
            old = db.execute('SELECT body FROM memories WHERE id=?', (entry.memory_id,)).fetchone()
            if old and old[0] != encode(entry):
                raise ValueError('MEMORY_IMMUTABLE: 新内容需要新身份')
            db.execute('INSERT OR IGNORE INTO memories VALUES (?,?,?)', (entry.memory_id, run_id, encode(entry)))
            self.event(db, run_id, 'memory', 'indexed', inputs=entry.sources)
        return entry

    def memories(self, filters):
        from schemas.platform import MemoryEntry
        result = []
        with self.connect(True) as db:
            for row in db.execute('SELECT body,run_id FROM memories ORDER BY id'):
                entry = MemoryEntry.model_validate_json(row[0])
                if entry.invalidated or (entry.expires_at and entry.expires_at <= now()):
                    continue
                scoped = filters.get('model_scope')
                entry_scope = entry.model_scope
                if scoped and entry_scope is None:
                    source = self.session(row['run_id'], db)['snapshot']['input']
                    entry_scope = digest(dict(robot=source['robot'], backend=source['policy']['backend']))
                transferable = scoped is not None and scoped in entry.transferable_scopes
                if scoped and entry_scope != scoped and not transferable:
                    continue
                if any(value is not None and getattr(entry, key) != value for key, value in filters.items()
                       if key not in ('tags', 'model_scope') and not (key == 'model_id' and transferable)):
                    continue
                if set(filters.get('tags', [])) - set(entry.tags):
                    continue
                try:
                    for ref in entry.sources:
                        self.artifact(ref, db=db)
                except ValueError:
                    continue
                result.append(entry)
        return result
