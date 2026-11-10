"""Local music scoped to each agent; never claim playback for a missing file."""
import difflib
import json
import random
import unicodedata
import uuid
from pathlib import Path
from plugins_func.register import register_function,ToolType,ActionResponse,Action
from core.providers.tts.dto.dto import TTSMessageDTO,SentenceType,ContentType
DESC={'type':'function','function':{'name':'play_music','description':'Phát bài hát có sẵn trong thư mục nhạc của server; không tải nhạc từ Internet. Nếu không chỉ định tên, dùng random.','parameters':{'type':'object','properties':{'song_name':{'type':'string','description':'Tên bài hát hoặc random'}},'required':['song_name']}}}
def normalized(text):
    return ''.join(c for c in unicodedata.normalize('NFD',text.casefold().replace('đ','d')) if not unicodedata.combining(c)).replace('-',' ').replace('_',' ').strip()
def find_song(folder,name):
    root=Path(folder).resolve()
    files=sorted(p for p in root.rglob('*') if p.is_file() and p.suffix.lower() in {'.mp3','.wav','.ogg','.flac'} and p.resolve().is_relative_to(root)) if root.is_dir() else []
    if not files:return None
    if name=='random':return random.choice(files)
    query=normalized(name)
    for p in files:
        if normalized(p.stem)==query:return p
    ratio,path=max(((difflib.SequenceMatcher(None,query,normalized(p.stem)).ratio(),p) for p in files),key=lambda pair:pair[0])
    return path if ratio>=0.6 else None
@register_function('play_music',DESC,ToolType.SYSTEM_CTL)
async def play_music(conn,song_name):
    if not isinstance(song_name,str) or not 1<=len(song_name.strip())<=200:return ActionResponse(Action.RESPONSE,response='Tên bài hát không hợp lệ.')
    import asyncio
    folder=conn.config.get('plugins',{}).get('play_music',{}).get('music_dir','music')
    song=await asyncio.to_thread(find_song,folder,song_name.strip())
    if not song:return ActionResponse(Action.RESPONSE,response='Chưa có bài hát phù hợp. Chép MP3/WAV/OGG/FLAC vào thư mục music của server.')
    if not conn.tts:return ActionResponse(Action.RESPONSE,response='Thiết bị chưa sẵn sàng phát âm thanh.')
    own_turn=not conn.client_is_speaking
    if own_turn:
        conn.sentence_id=uuid.uuid4().hex;conn.client_abort=False
        await conn.websocket.send(json.dumps({'type':'tts','state':'start','session_id':conn.session_id}));conn.client_is_speaking=True
        conn.tts.tts_text_queue.put(TTSMessageDTO(conn.sentence_id,SentenceType.FIRST,ContentType.ACTION))
    conn.tts.tts_text_queue.put(TTSMessageDTO(conn.sentence_id,SentenceType.MIDDLE,ContentType.TEXT,content_detail='Mời bạn nghe bài '+song.stem+'.'))
    conn.tts.tts_text_queue.put(TTSMessageDTO(conn.sentence_id,SentenceType.MIDDLE,ContentType.FILE,content_file=str(song)))
    if own_turn:conn.tts.tts_text_queue.put(TTSMessageDTO(conn.sentence_id,SentenceType.LAST,ContentType.ACTION))
    return ActionResponse(Action.RECORD,result='Đã đưa bài '+song.stem+' vào hàng đợi âm thanh của thiết bị.')
