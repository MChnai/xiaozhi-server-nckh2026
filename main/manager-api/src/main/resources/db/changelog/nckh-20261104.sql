-- NCKH profile only. Keep upstream history intact. Use a fresh database for the first deployment.

CREATE TABLE IF NOT EXISTS ai_reminder_nckh (
 id VARCHAR(32) NOT NULL PRIMARY KEY,
 device_id VARCHAR(128) NOT NULL,
 content VARCHAR(500) NOT NULL,
 due_at DATETIME NOT NULL COMMENT 'UTC',
 repeat_type VARCHAR(10) NOT NULL DEFAULT 'none',
 status VARCHAR(12) NOT NULL DEFAULT 'pending',
 attempt_at DATETIME NULL,
 queued_at DATETIME NULL,
 created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
 updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
 INDEX idx_reminder_due(status,due_at),
 INDEX idx_reminder_device(device_id,status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

INSERT INTO ai_model_provider (id,model_type,provider_code,name,fields,sort) VALUES ('NCKH_ASR','ASR','PhoWhisper','PhoWhisper tiếng Việt (CPU)','[{"key": "model_path", "label": "Thư mục model CT2", "type": "string"}, {"key": "language", "label": "Ngôn ngữ (vi)", "type": "string"}, {"key": "cpu_threads", "label": "Số luồng CPU", "type": "number"}, {"key": "output_dir", "label": "Thư mục tạm", "type": "string"}]',0);

INSERT INTO ai_model_provider (id,model_type,provider_code,name,fields,sort) VALUES ('NCKH_LLM','LLM','NckhLLM','DeepSeek / kiểm tra kết nối','[{"key": "model_name", "label": "Tên model", "type": "string"}, {"key": "base_url", "label": "Địa chỉ API", "type": "string"}, {"key": "api_key", "label": "Khóa API (ưu tiên biến môi trường)", "type": "string"}, {"key": "api_key_env", "label": "Tên biến môi trường chứa khóa", "type": "string"}, {"key": "max_tokens", "label": "Giới hạn token đầu ra", "type": "number"}]',0);

INSERT INTO ai_model_provider (id,model_type,provider_code,name,fields,sort) VALUES ('NCKH_NEWS','Plugin','get_news_from_vnexpress','Tin tức VnExpress','[]',0);

INSERT INTO ai_model_provider (id,model_type,provider_code,name,fields,sort) VALUES ('NCKH_WEATHER','Plugin','get_weather_vn','Thời tiết tiếng Việt','[]',0);

INSERT INTO ai_model_provider (id,model_type,provider_code,name,fields,sort) VALUES ('NCKH_ADD_REMINDER','Plugin','add_reminder','Tạo lời nhắc','[]',0);

INSERT INTO ai_model_provider (id,model_type,provider_code,name,fields,sort) VALUES ('NCKH_LIST_REMINDERS','Plugin','list_reminders','Danh sách lời nhắc','[]',0);

INSERT INTO ai_model_provider (id,model_type,provider_code,name,fields,sort) VALUES ('NCKH_DELETE_REMINDER','Plugin','delete_reminder','Hủy lời nhắc','[]',0);

UPDATE ai_model_config SET is_default=0 WHERE model_type IN ('ASR','LLM','TTS','Intent');

INSERT INTO ai_model_config (id,model_type,model_code,model_name,is_default,is_enabled,config_json,sort,remark) VALUES ('ASR_NCKH','ASR','PhoWhisper','PhoWhisper-small tiếng Việt',1,1,'{"type": "pho_whisper_ct2", "model_path": "models/phowhisper-small-ct2", "language": "vi", "cpu_threads": 4, "output_dir": "tmp/"}',0,'Cấu hình đề tài Robot AI tiếng Việt. Hướng dẫn: HUONG_DAN_VI.md');

INSERT INTO ai_model_config (id,model_type,model_code,model_name,is_default,is_enabled,config_json,sort,remark) VALUES ('LLM_NCKH','LLM','NckhLLM','Robot AI: Demo / DeepSeek',1,1,'{"type": "nckh", "model_name": "deepseek-flash", "base_url": "https://api.deepseek.com", "api_key": "", "api_key_env": "DEEPSEEK_API_KEY", "max_tokens": 512, "temperature": 0.5, "thinking": "off"}',0,'Cấu hình đề tài Robot AI tiếng Việt. Hướng dẫn: HUONG_DAN_VI.md');

INSERT INTO ai_model_config (id,model_type,model_code,model_name,is_default,is_enabled,config_json,sort,remark) VALUES ('TTS_NCKH','TTS','edge','Giọng Việt: Hoài My / Nam Minh',1,1,'{"type": "edge", "voice": "vi-VN-HoaiMyNeural", "language": "Tiếng Việt", "output_dir": "tmp/", "format": "mp3"}',0,'Cấu hình đề tài Robot AI tiếng Việt. Hướng dẫn: HUONG_DAN_VI.md');

INSERT INTO ai_model_config (id,model_type,model_code,model_name,is_default,is_enabled,config_json,sort,remark) VALUES ('Intent_NCKH','Intent','function_call','Gọi công cụ của Robot AI',1,1,'{"type": "function_call", "functions": "get_news_from_vnexpress;get_weather_vn;add_reminder;list_reminders;delete_reminder;play_music"}',0,'Cấu hình đề tài Robot AI tiếng Việt. Hướng dẫn: HUONG_DAN_VI.md');

INSERT INTO ai_tts_voice (id,tts_model_id,name,tts_voice,languages,sort) VALUES ('NCKH_VOICE_MY','TTS_NCKH','Hoài My (nữ)','vi-VN-HoaiMyNeural','Tiếng Việt',0);

INSERT INTO ai_tts_voice (id,tts_model_id,name,tts_voice,languages,sort) VALUES ('NCKH_VOICE_MINH','TTS_NCKH','Nam Minh (nam)','vi-VN-NamMinhNeural','Tiếng Việt',0);

UPDATE ai_agent_template SET sort=sort+10;

INSERT INTO ai_agent_template (id,agent_code,agent_name,asr_model_id,vad_model_id,llm_model_id,tts_model_id,tts_voice_id,tts_language,mem_model_id,intent_model_id,system_prompt,lang_code,language,sort,chat_history_conf) VALUES ('NCKH_AGENT_VI','robot-viet','Trợ lý Robot Việt','ASR_NCKH','VAD_SileroVAD','LLM_NCKH','TTS_NCKH','NCKH_VOICE_MY','Tiếng Việt','Memory_nomem','Intent_NCKH','Bạn là trợ lý Robot AI tiếng Việt. Trả lời ngắn gọn, thân thiện bằng tiếng Việt. Dùng đúng công cụ phiên hiện tại để lấy tin tức, thời tiết, tạo lời nhắc và điều khiển phần cứng. Khi chưa rõ ngày giờ hoặc hành động, hỏi lại người dùng. Chỉ xác nhận thành công khi công cụ báo thành công.','vi-VN','Tiếng Việt',0,0);

UPDATE sys_params SET param_value='86400' WHERE param_code='close_connection_no_voice_time';

UPDATE sys_params SET param_value='false' WHERE param_code='enable_wakeup_words_response_cache';

UPDATE sys_params SET param_value='tạm biệt;dừng trò chuyện' WHERE param_code='exit_commands';

UPDATE sys_params SET param_value='xin chào robot;robot ơi' WHERE param_code='wakeup_words';

UPDATE sys_params SET param_value='true' WHERE param_code='server.auth.enabled';

UPDATE sys_params SET param_value='Máy chủ đang gặp lỗi. Bạn vui lòng thử lại sau.' WHERE param_code='system_error_response';

UPDATE sys_params SET param_value='Bạn là trợ lý Robot AI tiếng Việt. Trả lời ngắn gọn, thân thiện bằng tiếng Việt. Dùng đúng công cụ phiên hiện tại để lấy tin tức, thời tiết, tạo lời nhắc và điều khiển phần cứng. Khi chưa rõ ngày giờ hoặc hành động, hỏi lại người dùng. Chỉ xác nhận thành công khi công cụ báo thành công.' WHERE param_code='prompt';

UPDATE sys_params SET param_value='Kết thúc cuộc trò chuyện bằng một lời chào ngắn bằng tiếng Việt.' WHERE param_code='end_prompt.prompt';

UPDATE sys_params SET param_value=JSON_SET(param_value,'$.features.asr.enabled',true) WHERE param_code='system-web.menu' AND JSON_VALID(param_value);
