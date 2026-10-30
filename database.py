"""Persistencia compatible con CNShopper Client Assistant V3."""
import os
import sqlite3
from datetime import datetime

APP_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(APP_DIR, 'data')
BACKUP_DIR = os.path.join(APP_DIR, 'backups')
DB_PATH = os.path.join(DATA_DIR, 'clients.db')
REGISTRATION_STATES = ('No iniciado', 'En proceso', 'Esperando OTP', 'Completado', 'Cancelado')


def db():
    os.makedirs(DATA_DIR, exist_ok=True)
    con = sqlite3.connect(DB_PATH, timeout=15)
    con.execute('PRAGMA foreign_keys=ON')
    return con


def make_backup():
    """Respaldo consistente antes de migraciones y al iniciar."""
    if not os.path.exists(DB_PATH):
        return None
    os.makedirs(BACKUP_DIR, exist_ok=True)
    stamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    target = os.path.join(BACKUP_DIR, f'clients_{stamp}.db')
    with sqlite3.connect(DB_PATH) as source, sqlite3.connect(target) as dest:
        source.backup(dest)
    backups = sorted((os.path.join(BACKUP_DIR, f) for f in os.listdir(BACKUP_DIR)
                      if f.endswith('.db')), key=os.path.getmtime, reverse=True)
    for old in backups[20:]:
        try:
            os.remove(old)
        except OSError:
            pass
    return target


def init_db():
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(BACKUP_DIR, exist_ok=True)
    # Nunca alterar una base existente sin respaldo previo.
    make_backup()
    with db() as con:
        con.execute('''CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            contact TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'Pendiente',
            notes TEXT DEFAULT '',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)''')
        cols = {r[1] for r in con.execute('PRAGMA table_info(clients)')}
        for col, definition in {'email': "TEXT DEFAULT ''", 'phone': "TEXT DEFAULT ''",
                                'updated_at': 'TEXT'}.items():
            if col not in cols:
                con.execute(f'ALTER TABLE clients ADD COLUMN {col} {definition}')
        con.execute('''CREATE TABLE IF NOT EXISTS client_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER NOT NULL,
            action TEXT NOT NULL,
            details TEXT DEFAULT '',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)''')
        con.execute('''CREATE TABLE IF NOT EXISTS registration_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER NOT NULL,
            started_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            status TEXT NOT NULL DEFAULT 'En proceso',
            finished_at TEXT,
            observations TEXT NOT NULL DEFAULT '',
            FOREIGN KEY(client_id) REFERENCES clients(id))''')
        con.execute('CREATE INDEX IF NOT EXISTS idx_registration_client ON registration_history(client_id, id)')
        con.execute('PRAGMA user_version=4')


def start_registration(client_id):
    with db() as con:
        row = con.execute('SELECT name, email FROM clients WHERE id=?', (client_id,)).fetchone()
        if not row or not row[0].strip() or not (row[1] or '').strip():
            raise ValueError('El cliente debe tener nombre y correo electrónico.')
        active = con.execute('''SELECT id FROM registration_history WHERE client_id=?
                                AND status IN ('En proceso','Esperando OTP')
                                ORDER BY id DESC LIMIT 1''', (client_id,)).fetchone()
        if active:
            raise ValueError('Ya existe un registro activo para este cliente.')
        cur = con.execute('INSERT INTO registration_history(client_id) VALUES (?)', (client_id,))
        con.execute("UPDATE clients SET status='En proceso', updated_at=CURRENT_TIMESTAMP WHERE id=?", (client_id,))
        con.execute('INSERT INTO client_history(client_id,action,details) VALUES (?,?,?)',
                    (client_id, 'Registro iniciado', f'Intento #{cur.lastrowid}; autorización confirmada por operador'))
        return cur.lastrowid


def change_registration(registration_id, state, observation=''):
    if state not in REGISTRATION_STATES or state == 'No iniciado':
        raise ValueError('Estado de registro no válido.')
    observation = observation.strip()
    with db() as con:
        row = con.execute('SELECT client_id,status FROM registration_history WHERE id=?',
                          (registration_id,)).fetchone()
        if not row:
            raise ValueError('Intento de registro no encontrado.')
        client_id, old_state = row
        if old_state in ('Completado', 'Cancelado'):
            raise ValueError('El intento ya está cerrado.')
        if state == 'Completado' and old_state != 'Esperando OTP':
            raise ValueError('Primero marca el intento como Esperando OTP.')
        finished = state in ('Completado', 'Cancelado')
        con.execute('''UPDATE registration_history SET status=?, observations=?,
                       finished_at=CASE WHEN ? THEN CURRENT_TIMESTAMP ELSE NULL END WHERE id=?''',
                    (state, observation, int(finished), registration_id))
        general = 'Completado' if state == 'Completado' else 'Pendiente' if state == 'Cancelado' else 'En proceso'
        con.execute('UPDATE clients SET status=?, updated_at=CURRENT_TIMESTAMP WHERE id=?',
                    (general, client_id))
        con.execute('INSERT INTO client_history(client_id,action,details) VALUES (?,?,?)',
                    (client_id, 'Estado de registro', f'Intento #{registration_id}: {state}'))


def latest_registration(client_id):
    with db() as con:
        return con.execute('''SELECT id,status,started_at,finished_at,observations
                              FROM registration_history WHERE client_id=? ORDER BY id DESC LIMIT 1''',
                           (client_id,)).fetchone()


def registration_history(client_id):
    with db() as con:
        return con.execute('''SELECT id,status,started_at,finished_at,observations
                              FROM registration_history WHERE client_id=? ORDER BY id DESC''',
                           (client_id,)).fetchall()
