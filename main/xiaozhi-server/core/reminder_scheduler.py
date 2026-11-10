"""One scheduler per voice-server process. DB dates are UTC; user dates are Vietnam time.
A queued notification means audio was sent over WebSocket, not a speaker acknowledgement.
"""
import asyncio
import json
import os
import re
import uuid
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

VN = ZoneInfo("Asia/Ho_Chi_Minh")


def device_key(value):
    return value.upper() if re.fullmatch(r'(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}',value or '') else value


def utc_now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def parse_due(value, now=None):
    due = datetime.fromisoformat(value.replace("Z","+00:00"))
    if due.tzinfo is None:
        due = due.replace(tzinfo=VN)
    due = due.astimezone(timezone.utc).replace(tzinfo=None)
    if due <= (now or utc_now()):
        raise ValueError("Thời điểm nhắc phải ở tương lai (giờ Việt Nam nếu không ghi múi giờ).")
    return due


def next_due(due, repeat_type, now):
    if repeat_type == "none":
        return None
    days = {"daily": 1, "weekly": 7}[repeat_type]
    step = timedelta(days=days)
    return due + step * (max(0, (now - due) // step) + 1)


class ReminderStore:
    def _connect(self):
        import pymysql
        return pymysql.connect(host=os.environ.get("REMINDER_DB_HOST", "db"),
            port=int(os.environ.get("REMINDER_DB_PORT", "3306")),
            user=os.environ.get("REMINDER_DB_USER", "robot"),
            password=os.environ.get("REMINDER_DB_PASSWORD", ""),
            database=os.environ.get("REMINDER_DB_NAME", "xiaozhi_esp32_server"),
            charset="utf8mb4", cursorclass=pymysql.cursors.DictCursor,
            connect_timeout=5, read_timeout=5, write_timeout=5, autocommit=True)

    def _query(self, sql, args=(), fetch=False):
        with self._connect() as db:
            with db.cursor() as cur:
                cur.execute(sql, args)
                return cur.fetchall() if fetch else cur.rowcount

    def add(self, device_id, content, due, repeat_type):
        if not device_id:
            raise ValueError("Thiếu định danh thiết bị")
        if not content.strip() or len(content) > 500:
            raise ValueError("Nội dung phải có từ 1 đến 500 ký tự")
        if repeat_type not in ("none", "daily", "weekly"):
            raise ValueError("Kiểu lặp phải là none, daily hoặc weekly")
        rid = uuid.uuid4().hex
        self._query("INSERT INTO ai_reminder_nckh (id,device_id,content,due_at,repeat_type) VALUES (%s,%s,%s,%s,%s)",
                    (rid, device_key(device_id), content.strip(), due, repeat_type))
        return rid

    def list(self, device_id):
        return self._query("SELECT id,content,due_at,repeat_type,status FROM ai_reminder_nckh WHERE device_id=%s AND status IN ('pending','sending') ORDER BY due_at LIMIT 50", (device_id,), True)

    def cancel(self, device_id, reminder_id):
        return self._query("UPDATE ai_reminder_nckh SET status='cancelled' WHERE id=%s AND device_id=%s AND status IN ('pending','sending')", (reminder_id, device_id))

    def due(self, now, device_ids):
        if not device_ids:
            return []
        self._query("UPDATE ai_reminder_nckh SET status='pending' WHERE status='sending' AND attempt_at < %s", (now-timedelta(minutes=5),))
        placeholders = ",".join(["%s"] * len(device_ids))
        return self._query("SELECT * FROM ai_reminder_nckh WHERE status='pending' AND due_at <= %s AND device_id IN (" + placeholders + ") ORDER BY due_at LIMIT 100", (now, *device_ids), True)

    def is_sending(self,rid):
        return bool(self._query("SELECT id FROM ai_reminder_nckh WHERE id=%s AND status='sending'",(rid,),True))

    def claim(self, rid, now):
        return self._query("UPDATE ai_reminder_nckh SET status='sending',attempt_at=%s WHERE id=%s AND status='pending'", (now,rid)) == 1

    def finish(self, row, now):
        following = next_due(row['due_at'], row['repeat_type'], now)
        if following:
            self._query("UPDATE ai_reminder_nckh SET status='pending',due_at=%s,queued_at=%s WHERE id=%s AND status='sending'", (following, now, row['id']))
        else:
            self._query("UPDATE ai_reminder_nckh SET status='queued',queued_at=%s WHERE id=%s AND status='sending'", (now,row['id']))

    def release(self, rid):
        self._query("UPDATE ai_reminder_nckh SET status='pending' WHERE id=%s AND status='sending'", (rid,))


class ReminderService:
    def __init__(self, config, logger, store=None):
        self.enabled = bool(config.get("reminders", {}).get("enabled", False))
        self.logger = logger
        self.store = store or ReminderStore()
        self.connections = {}
        self.inflight = {}

    def attach(self, conn):
        if self.enabled and conn.device_id:
            self.connections[device_key(conn.device_id)] = conn
            conn._reminder_service=self

    def detach(self, conn):
        if self.connections.get(device_key(conn.device_id)) is conn:
            self.connections.pop(device_key(conn.device_id), None)

    async def run(self):
        if not self.enabled:
            return
        while True:
            try:
                await self.tick()
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                self.logger.warning(f"Bộ nhắc nhở chưa xử lý được: {type(exc).__name__}")
            await asyncio.sleep(10)

    async def tick(self):
        now = utc_now()
        for sid,item in list(self.inflight.items()):
            conn=item['conn']
            if not await asyncio.to_thread(self.store.is_sending,item['row']['id']):
                if conn.sentence_id==sid and not conn.client_abort:
                    from core.handle.abortHandle import handleAbortMessage
                    await handleAbortMessage(conn)
                await self.complete(conn,sid,failed=True)
                continue
            if item['deadline']<=now or self.connections.get(device_key(conn.device_id)) is not conn or conn.sentence_id!=sid or conn.client_abort or conn.stop_event.is_set():
                await self.complete(conn,sid,failed=True)
        for row in await asyncio.to_thread(self.store.due, now, tuple(self.connections)):
            conn = self.connections.get(device_key(row['device_id']))
            if not self._ready(conn):
                continue
            if not await asyncio.to_thread(self.store.claim, row['id'], now):
                continue
            try:
                # DB I/O yielded control: a reconnect or new utterance may have arrived.
                if self.connections.get(device_key(row['device_id'])) is not conn or not self._ready(conn):
                    await asyncio.to_thread(self.store.release, row['id'])
                    continue
                sid=uuid.uuid4().hex
                self.inflight[sid]={'row':row,'conn':conn,'deadline':now+timedelta(minutes=3)}
                conn._reminder_sid=sid;conn._reminder_audio_frames=0;conn._reminder_failed=False
                await self.notify(conn,"Đến giờ nhắc: "+row['content'],sid)
            except Exception:
                self.inflight.pop(locals().get("sid"),None)
                await asyncio.to_thread(self.store.release, row['id'])
                raise

    @staticmethod
    def _ready(conn):
        return bool(conn and conn.tts and not conn.need_bind and not conn.stop_event.is_set()
                    and conn.bind_completed_event.is_set()
                    and not conn.client_is_speaking and not conn.client_have_voice
                    and conn.tts.tts_text_queue.empty() and conn.tts.tts_audio_queue.empty())

    async def complete(self,conn,sid,failed=False):
        item=self.inflight.pop(sid,None)
        if not item or item['conn'] is not conn:return
        sent=not failed and not conn.client_abort and not getattr(conn,'_reminder_failed',False) and getattr(conn,'_reminder_audio_frames',0)>0
        if sent:await asyncio.to_thread(self.store.finish,item['row'],utc_now())
        else:await asyncio.to_thread(self.store.release,item['row']['id'])
        if getattr(conn,'_reminder_sid',None)==sid:conn._reminder_sid=None

    async def notify(self, conn, text,sid=None):
        sid = sid or uuid.uuid4().hex
        conn.sentence_id = sid
        conn.client_abort = False
        # An idle firmware must receive tts/start before any audio is queued.
        await conn.websocket.send(json.dumps({"type":"tts", "state":"start", "session_id":conn.session_id}))
        conn.client_is_speaking = True
        try:
            self.enqueue(conn, text, sid)
        except Exception:
            conn.client_is_speaking = False
            raise

    @staticmethod
    def enqueue(conn, text, sentence_id=None):
        from core.providers.tts.dto.dto import TTSMessageDTO, SentenceType, ContentType
        sid = sentence_id or uuid.uuid4().hex
        conn.sentence_id = sid
        conn.client_abort = False
        # Use the same FIRST/TEXT/LAST queue as ordinary conversation.
        for phase, kind, content in ((SentenceType.FIRST, ContentType.ACTION, None),
                                     (SentenceType.MIDDLE, ContentType.TEXT, text),
                                     (SentenceType.LAST, ContentType.ACTION, None)):
            conn.tts.tts_text_queue.put(TTSMessageDTO(sid, phase, kind, content_detail=content))
