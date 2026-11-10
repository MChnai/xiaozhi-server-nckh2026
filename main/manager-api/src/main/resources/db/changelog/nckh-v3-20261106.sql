-- v3 fresh install: offline Piper is ready by default; all other TTS remain selectable.
UPDATE ai_model_config SET is_default=0 WHERE model_type='TTS' AND id<>'TTS_PIPER_NCKH';
UPDATE ai_model_config SET is_default=1,remark='Mặc định v3; dịch vụ Piper được bộ cài khởi động tự động.' WHERE id='TTS_PIPER_NCKH';
UPDATE ai_model_config SET remark='EdgeTTS online: chọn Hoài My hoặc Nam Minh; cần Internet, không cần API DeepSeek.' WHERE id='TTS_NCKH';
UPDATE ai_model_config SET remark='VieNeu offline: bật profile vieneu và tải mô hình lần đầu. Xem HUONG_DAN_V3.md.' WHERE id='TTS_VIENEU_NCKH';
UPDATE ai_agent_template SET tts_model_id='TTS_PIPER_NCKH',tts_voice_id='NCKH_VOICE_PIPER' WHERE id='NCKH_AGENT_VI';
UPDATE ai_model_config SET config_json=JSON_SET(config_json,'$.model_path','/model-store/phowhisper-small-ct2') WHERE id='ASR_NCKH';

UPDATE sys_params SET param_value='Robot AI tiếng Việt' WHERE param_code='server.name';
UPDATE sys_params SET param_value='true' WHERE param_code='server.allow_user_register';
UPDATE sys_params SET param_value='true' WHERE param_code='server.auth.enabled';
UPDATE sys_params SET param_value='86400' WHERE param_code='close_connection_no_voice_time';
-- The inherited role presets now use the same supported Vietnamese pipeline.
UPDATE ai_agent_template SET asr_model_id='ASR_NCKH',vad_model_id='VAD_SileroVAD',llm_model_id='LLM_NCKH',tts_model_id='TTS_PIPER_NCKH',tts_voice_id='NCKH_VOICE_PIPER',tts_language='Tiếng Việt',mem_model_id='Memory_nomem',intent_model_id='Intent_NCKH',lang_code='vi-VN',language='Tiếng Việt',system_prompt=CONCAT('Bạn là ',agent_name,'. Giao tiếp thân thiện bằng tiếng Việt. Dùng công cụ được công bố để xem thời tiết, tin tức, âm lịch, giá vàng, phát nhạc, dịch và tạo lời nhắc. Chỉ báo đã điều khiển robot khi công cụ xác nhận thành công. Hỏi lại nếu thiếu thời gian hoặc thông tin cần thiết.') WHERE id<>'NCKH_AGENT_VI';
