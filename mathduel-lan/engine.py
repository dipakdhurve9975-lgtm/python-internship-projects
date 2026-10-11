"""Server-owned match state. No Flask dependency, so time can be tested."""
from dataclasses import dataclass, field
from collections import deque
import math
import random
import re
import secrets
import sqlite3
import threading
import time
from pathlib import Path

LEVELS = ('easy', 'medium', 'hard')

def question(level, rng=None, operation=None):
    rng = rng or random.SystemRandom()
    if level not in LEVELS:
        raise ValueError('Choose easy, medium or hard.')
    ceiling = {'easy': 10, 'medium': 25, 'hard': 60}[level]
    op = operation or rng.choice(('+', '-', '*', '/', 'square', 'root'))
    a, b = rng.randint(1, ceiling), rng.randint(1, ceiling)
    if op == '+': return f'{a} + {b}', a + b
    if op == '-': return f'{a} - {b}', a - b
    if op == '*': return f'{a} × {b}', a * b
    if op == '/': return f'{a * b} ÷ {b}', a
    if op == 'square': return f'{a}²', a * a
    if op == 'root': return f'√{a * a}', a
    raise ValueError('Unknown operation.')

def nickname(value):
    if not isinstance(value, str) or not re.fullmatch(r'[\w .-]{1,20}', value.strip()):
        raise ValueError('Use 1–20 letters, numbers, spaces, dots or hyphens.')
    return value.strip()

def parse_answer(value):
    if isinstance(value, bool) or not isinstance(value, (str, int)):
        raise ValueError('Enter a whole number.')
    if not re.fullmatch(r'-?\d{1,7}', str(value)):
        raise ValueError('Enter a whole number, up to seven digits.')
    return int(value)

def points(correct, elapsed, duration=15):
    # Correct answers earn 10 + 0..5, one bonus point per three seconds left.
    return 10 + max(0, min(5, math.floor((duration - elapsed) / 3))) if correct else 0

class Stats:
    def __init__(self, path):
        self.path = str(path)
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS matches (id TEXT PRIMARY KEY, created REAL, mode TEXT, summary TEXT)')
            db.execute('CREATE TABLE IF NOT EXISTS answers (match_id TEXT, player INTEGER, round INTEGER, correct INTEGER, elapsed REAL, answered INTEGER, PRIMARY KEY(match_id, player, round))')
        self.prune()

    def connect(self): return sqlite3.connect(self.path, timeout=10)

    def prune(self):
        with self.connect() as db:
            cutoff = time.time() - 30 * 86400
            db.execute('DELETE FROM answers WHERE match_id IN (SELECT id FROM matches WHERE created < ?)', (cutoff,))
            db.execute('DELETE FROM matches WHERE created < ?', (cutoff,))

    def save(self, room):
        import json
        self.prune()
        with self.connect() as db:
            db.execute('INSERT OR IGNORE INTO matches VALUES (?, ?, ?, ?)', (room.match_id, time.time(), 'solo' if room.solo else 'duel', json.dumps([p.score for p in room.players])))
            for i, p in enumerate(room.players):
                for n, a in enumerate(p.records):
                    db.execute('INSERT OR IGNORE INTO answers VALUES (?, ?, ?, ?, ?, ?)', (room.match_id, i, n + 1, int(a['correct']), a['elapsed'], int(a['answered'])))

    def summary(self):
        with self.connect() as db:
            count = db.execute('SELECT COUNT(*) FROM matches').fetchone()[0]
            attempts, correct, response = db.execute('SELECT COUNT(*), COALESCE(SUM(correct),0), AVG(CASE WHEN answered = 1 THEN elapsed END) FROM answers').fetchone()
        return {'matches': count, 'rounds': attempts, 'accuracy': round(100 * correct / attempts, 1) if attempts else 0, 'average_response': round(response, 2) if response is not None else None}

@dataclass
class Player:
    name: str
    token: str = field(default_factory=lambda: secrets.token_urlsafe(32))
    sid: str | None = None
    score: int = 0
    records: list = field(default_factory=list)

@dataclass
class Room:
    code: str
    level: str
    solo: bool
    created: float
    players: list
    phase: str = 'lobby'
    round: int = 0
    text: str = ''
    answer: int = 0
    start: float = 0
    deadline: float = 0
    submissions: dict = field(default_factory=dict)
    match_id: str = field(default_factory=lambda: secrets.token_hex(16))
    saved: bool = False

class Engine:
    def __init__(self, stats, clock=time.monotonic, duration=15, feedback=2):
        self.stats, self.clock, self.duration, self.feedback = stats, clock, duration, feedback
        self.rooms = {}
        self.lock = threading.RLock()

    def expire(self):
        now = self.clock()
        for code, room in list(self.rooms.items()):
            if now - room.created > 1800: del self.rooms[code]

    def create(self, name, level, solo=False):
        self.expire()
        if level not in LEVELS: raise ValueError('Invalid difficulty.')
        if len(self.rooms) >= 100: raise ValueError('Server is full. Try later.')
        for _ in range(100):
            code = str(secrets.randbelow(900000) + 100000)
            if code not in self.rooms: break
        else: raise ValueError('Could not allocate a room code. Try again.')
        room = Room(code, level, solo, self.clock(), [Player(nickname(name))])
        self.rooms[code] = room
        return room, room.players[0]

    def join(self, code, name):
        self.expire()
        room = self.get(code)
        if room.solo: raise ValueError('This is a solo room. Ask your friend for a two-player room code.')
        if room.phase != 'lobby': raise ValueError('This match has already started. Existing players should reconnect in their original tab.')
        if len(room.players) >= 2: raise ValueError('Room is full. Existing players should reconnect in their original tab, or create a new room.')
        p = Player(nickname(name))
        room.players.append(p)
        return room, p

    def get(self, code):
        if not isinstance(code, str) or not re.fullmatch(r'[0-9]{6}', code):
            raise ValueError('Enter the six-digit room code.')
        if code not in self.rooms:
            raise ValueError('Room not found or expired. The server may have restarted. Ask your friend to create a new room.')
        return self.rooms[code]

    def find(self, sid):
        for room in self.rooms.values():
            for i, p in enumerate(room.players):
                if p.sid == sid: return room, i
        raise ValueError('Join or resume a room first.')

    def resume(self, code, token):
        self.expire()
        room = self.get(code)
        if not isinstance(token, str): raise ValueError('Invalid resume token.')
        for p in room.players:
            if secrets.compare_digest(p.token, token): return room, p
        raise ValueError('Resume token is invalid.')

    def start_match(self, room, index):
        if index != 0: raise ValueError('Only the host may start.')
        if room.phase not in ('lobby', 'results'): raise ValueError('A match is already running.')
        if len(room.players) != (1 if room.solo else 2) or any(p.sid is None for p in room.players):
            raise ValueError('Wait for all players to connect.')
        room.round, room.match_id, room.saved = 0, secrets.token_hex(16), False
        for p in room.players: p.score, p.records = 0, []
        self.next_round(room)

    def next_round(self, room):
        if room.solo and room.round and room.round % 5 == 0:
            recent = room.players[0].records[-5:]
            accuracy = sum(a['correct'] for a in recent) / len(recent)
            mean = sum(a['elapsed'] for a in recent) / len(recent)
            index = LEVELS.index(room.level)
            if accuracy >= .8 and mean < 6: index = min(2, index + 1)
            elif accuracy < .5 or mean > 12: index = max(0, index - 1)
            room.level = LEVELS[index]
        room.round += 1
        room.text, room.answer = question(room.level)
        room.start, room.submissions, room.phase = self.clock(), {}, 'question'
        room.deadline = room.start + self.duration

    def submit(self, room, index, value, round_number, match_id):
        if room.phase != 'question' or self.clock() >= room.deadline:
            raise ValueError('This round is closed.')
        if round_number != room.round or match_id != room.match_id:
            raise ValueError('That answer belongs to an old round.')
        if index in room.submissions: raise ValueError('Answer already received.')
        answer = parse_answer(value)
        elapsed = max(0, self.clock() - room.start)
        correct = answer == room.answer
        gain = points(correct, elapsed, self.duration)
        room.players[index].score += gain
        room.submissions[index] = {'correct': correct, 'elapsed': elapsed, 'points': gain, 'answered': True}
        if len(room.submissions) == len(room.players): self.finish_round(room)

    def finish_round(self, room):
        for i, p in enumerate(room.players):
            p.records.append(room.submissions.get(i, {'correct': False, 'elapsed': self.duration, 'points': 0, 'answered': False}))
        room.phase, room.deadline = 'feedback', self.clock() + self.feedback

    def tick(self):
        changed = []
        for room in list(self.rooms.values()):
            if self.clock() - room.created > 1800:
                del self.rooms[room.code]
                changed.append((room.code, None))
                continue
            if room.phase == 'question' and self.clock() >= room.deadline:
                self.finish_round(room)
                changed.append((room.code, room))
            elif room.phase == 'feedback' and self.clock() >= room.deadline:
                if room.round >= 10:
                    self.stats.save(room)
                    room.saved, room.phase = True, 'results'
                else: self.next_round(room)
                changed.append((room.code, room))
        return changed

    def public(self, room):
        now = self.clock()
        state = {'code': room.code, 'solo': room.solo, 'level': room.level, 'phase': room.phase, 'round': room.round, 'total': 10, 'match_id': room.match_id,
                 'question': room.text, 'remaining': max(0, room.deadline - now), 'duration': self.duration,
                 'players': [{'name': p.name, 'score': p.score, 'connected': p.sid is not None, 'submitted': i in room.submissions} for i, p in enumerate(room.players)]}
        if room.phase in ('feedback', 'results'):
            state['answer'] = room.answer
            state['feedback'] = [p.records[-1] for p in room.players]
        if room.phase == 'results':
            high = max(p.score for p in room.players)
            state['winners'] = [p.name for p in room.players if p.score == high]
            state['statistics'] = [{'accuracy': round(sum(a['correct'] for a in p.records) * 10), 'average_response': round(sum(a['elapsed'] for a in p.records if a['answered']) / max(1, sum(a['answered'] for a in p.records)), 2)} for p in room.players]
        return state
