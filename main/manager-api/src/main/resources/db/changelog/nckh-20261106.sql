-- Additive upgrade; preserve old migration checksum, keys and custom prompts.
INSERT IGNORE INTO ai_model_provider (id,model_type,provider_code,name,fields,sort) VALUES ('NCKH_GOLD','Plugin','get_gold_price','Giá vàng Việt Nam','[]',0);

INSERT IGNORE INTO ai_model_provider (id,model_type,provider_code,name,fields,sort) VALUES ('NCKH_TRANSLATE','Plugin','translate_text','Dịch Việt–Anh kèm IPA','[]',0);

INSERT IGNORE INTO ai_model_provider (id,model_type,provider_code,name,fields,sort) VALUES ('NCKH_LUNAR','Plugin','get_lunar','Âm lịch Việt Nam (UTC+7)','[]',0);

INSERT IGNORE INTO ai_model_provider (id,model_type,provider_code,name,fields,sort) VALUES ('NCKH_PIPER','TTS','piper_local','Piper tiếng Việt (offline CPU)','[{"key": "endpoint", "label": "URL nội bộ Docker", "type": "string"}, {"key": "voice", "label": "Giọng đọc", "type": "string"}, {"key": "tts_timeout", "label": "Thời gian chờ (giây)", "type": "number"}, {"key": "output_dir", "label": "Thư mục tạm", "type": "string"}]',1);

INSERT IGNORE INTO ai_model_config (id,model_type,model_code,model_name,is_default,is_enabled,config_json,sort,remark) VALUES ('TTS_PIPER_NCKH','TTS','piper_local','Piper tiếng Việt (offline CPU)',0,1,'{"type": "piper_local", "endpoint": "http://piper:5100", "voice": "vi_VN-vais1000-medium", "tts_timeout": 150, "output_dir": "tmp/"}',1,'Bật profile piper trước khi chọn. Xem HUONG_DAN_V2.md');

INSERT IGNORE INTO ai_tts_voice (id,tts_model_id,name,tts_voice,languages,sort) VALUES ('NCKH_VOICE_PIPER','TTS_PIPER_NCKH','VAIS 1000','vi_VN-vais1000-medium','Tiếng Việt',0);

INSERT IGNORE INTO ai_model_provider (id,model_type,provider_code,name,fields,sort) VALUES ('NCKH_VIENEU','TTS','vieneu_local','VieNeu tiếng Việt (offline CPU)','[{"key": "endpoint", "label": "URL nội bộ Docker", "type": "string"}, {"key": "voice", "label": "Giọng đọc", "type": "string"}, {"key": "tts_timeout", "label": "Thời gian chờ (giây)", "type": "number"}, {"key": "output_dir", "label": "Thư mục tạm", "type": "string"}]',1);

INSERT IGNORE INTO ai_model_config (id,model_type,model_code,model_name,is_default,is_enabled,config_json,sort,remark) VALUES ('TTS_VIENEU_NCKH','TTS','vieneu_local','VieNeu tiếng Việt (offline CPU)',0,1,'{"type": "vieneu_local", "endpoint": "http://vieneu:5100", "voice": "Hải Đăng", "tts_timeout": 150, "output_dir": "tmp/"}',1,'Bật profile vieneu trước khi chọn. Xem HUONG_DAN_V2.md');

INSERT IGNORE INTO ai_tts_voice (id,tts_model_id,name,tts_voice,languages,sort) VALUES ('NCKH_VOICE_VIENEU','TTS_VIENEU_NCKH','Hải Đăng','Hải Đăng','Tiếng Việt',0);

UPDATE ai_model_config SET model_name='Không lưu bộ nhớ dài hạn' WHERE id='Memory_nomem';

UPDATE ai_model_config SET config_json=JSON_SET(config_json,'$.tts_timeout',60) WHERE id='TTS_NCKH' AND JSON_EXTRACT(config_json,'$.tts_timeout') IS NULL;

UPDATE ai_model_config SET config_json=JSON_SET(config_json,'$.functions',CONCAT_WS(';',NULLIF(JSON_UNQUOTE(JSON_EXTRACT(config_json,'$.functions')),''),'get_gold_price','translate_text','get_lunar')) WHERE id='Intent_NCKH';

INSERT IGNORE INTO ai_agent_plugin_mapping(agent_id,plugin_id,param_info) SELECT a.id,p.id,JSON_OBJECT() FROM ai_agent a CROSS JOIN ai_model_provider p WHERE a.llm_model_id='LLM_NCKH' AND p.id IN ('NCKH_GOLD','NCKH_TRANSLATE','NCKH_LUNAR');

UPDATE ai_agent_template SET agent_name='Bạn đồng hành' WHERE agent_name='湾湾小何';

UPDATE ai_agent_template SET agent_name='Nhà thám hiểm' WHERE agent_name='星际游子';

UPDATE ai_agent_template SET agent_name='Giáo viên tiếng Anh' WHERE agent_name='英语老师';

UPDATE ai_agent_template SET agent_name='Bạn nhỏ tò mò' WHERE agent_name='好奇男孩';

UPDATE ai_agent_template SET agent_name='Đội trưởng robot' WHERE agent_name='汪汪队长';

UPDATE ai_agent_template SET system_prompt=CONCAT(system_prompt,' Dùng self.led.set_mode cho đèn mắt; self.robot.wave_hand để vẫy tay; self.robot.set_servo để xoay cổ hoặc tay; self.robot.get_distance để đo khoảng cách; self.robot.move để chạy bánh xe. Chỉ gọi công cụ thiết bị đã công bố. Góc servo 0–180, vẫy tay 1–10 lần, mỗi lệnh di chuyển tối đa 2000 ms. Khi yêu cầu nhảy hoặc biểu cảm, có thể phối hợp LED và tay; không suy đoán robot có chân hoặc chức năng không được công bố. Không xác nhận thành công nếu công cụ lỗi hoặc hết thời gian chờ. Giờ nhắc mặc định là giờ Việt Nam.') WHERE id='NCKH_AGENT_VI';

-- Translate help text, preserve parameter values.
UPDATE sys_params SET remark='Cho phép người dùng tự đăng ký tài khoản' WHERE param_code='server.allow_user_register';
UPDATE sys_params SET remark='Mã đăng ký an ninh mạng Trung Quốc; để null nếu không áp dụng' WHERE param_code='server.beian_ga_num';
UPDATE sys_params SET remark='Mã ICP Trung Quốc; để null nếu không áp dụng' WHERE param_code='server.beian_icp_num';
UPDATE sys_params SET remark='Bật đăng ký bằng số điện thoại' WHERE param_code='server.enable_mobile_register';
UPDATE sys_params SET remark='Địa chỉ web quản lý hiển thị khi ghép thiết bị' WHERE param_code='server.fronted_url';
UPDATE sys_params SET remark='Điểm kết nối MCP bên ngoài' WHERE param_code='server.mcp_endpoint';
UPDATE sys_params SET remark='Cấu hình MQTT; không bắt buộc với WebSocket trực tiếp' WHERE param_code='server.mqtt_gateway';
UPDATE sys_params SET remark='API quản lý MQTT' WHERE param_code='server.mqtt_manager_api';
UPDATE sys_params SET remark='Khóa ký MQTT; giữ bí mật' WHERE param_code='server.mqtt_signature_key';
UPDATE sys_params SET remark='Cổng UDP khi dùng MQTT' WHERE param_code='server.udp_gateway';
UPDATE sys_params SET remark='Bật xác thực token thiết bị' WHERE param_code='server.auth.enabled';
UPDATE sys_params SET remark='Địa chỉ HTTP OTA mà firmware gọi' WHERE param_code='server.ota';
UPDATE sys_params SET remark='Địa chỉ WebSocket; nhiều địa chỉ phân cách bằng dấu chấm phẩy' WHERE param_code='server.websocket';
UPDATE sys_params SET remark='Khóa nội bộ API Java và voice; không chia sẻ' WHERE param_code='server.secret';
UPDATE sys_params SET remark='IP để dịch vụ lắng nghe' WHERE param_code='server.ip';
UPDATE sys_params SET remark='Cổng WebSocket của voice server' WHERE param_code='server.port';
UPDATE sys_params SET remark='Cổng HTTP nội bộ của voice server' WHERE param_code='server.http_port';
UPDATE sys_params SET remark='Tên máy chủ' WHERE param_code='server.name';
UPDATE sys_params SET remark='Khóa riêng mã hóa đăng nhập' WHERE param_code='server.private_key';
UPDATE sys_params SET remark='Khóa công khai mã hóa đăng nhập' WHERE param_code='server.public_key';
UPDATE sys_params SET remark='Số SMS tối đa mỗi ngày' WHERE param_code='server.sms_max_send_count';
UPDATE sys_params SET remark='API giải thích hình ảnh' WHERE param_code='server.vision_explain';
UPDATE sys_params SET remark='Cấu hình nhận diện giọng người nói' WHERE param_code='server.voice_print';
UPDATE sys_params SET remark='Ngưỡng nhận diện người nói' WHERE param_code='server.voiceprint_similarity_threshold';
UPDATE sys_params SET remark='Giới hạn ký tự trả lời mỗi thiết bị/ngày; 0 là không giới hạn' WHERE param_code='device_max_output_size';
UPDATE sys_params SET remark='Ngắt kết nối sau thời gian không có tiếng nói (giây)' WHERE param_code='close_connection_no_voice_time';
UPDATE sys_params SET remark='Xóa tệp âm thanh tạm sau xử lý' WHERE param_code='delete_audio';
UPDATE sys_params SET remark='Bật câu chào khi kết nối' WHERE param_code='enable_greeting';
UPDATE sys_params SET remark='Phát âm báo kết thúc lời nói' WHERE param_code='enable_stop_tts_notify';
UPDATE sys_params SET remark='Dùng âm thanh chào lưu sẵn theo từ đánh thức' WHERE param_code='enable_wakeup_words_response_cache';
UPDATE sys_params SET remark='Bật ping giữ kết nối WebSocket' WHERE param_code='enable_websocket_ping';
UPDATE sys_params SET remark='Bật lời chào kết thúc hội thoại' WHERE param_code='end_prompt.enable';
UPDATE sys_params SET remark='Chỉ dẫn tạo lời chào kết thúc' WHERE param_code='end_prompt.prompt';
UPDATE sys_params SET remark='Các câu kết thúc hội thoại' WHERE param_code='exit_commands';
UPDATE sys_params SET remark='Các câu đánh thức' WHERE param_code='wakeup_words';
UPDATE sys_params SET remark='Câu trả lời khi hệ thống lỗi' WHERE param_code='system_error_response';
UPDATE sys_params SET remark='Thời gian chờ công cụ (giây)' WHERE param_code='tool_call_timeout';
UPDATE sys_params SET remark='Thời gian chờ TTS mặc định (giây); từng model có thể đặt riêng' WHERE param_code='tts_timeout';
UPDATE sys_params SET remark='Đường dẫn âm báo kết thúc' WHERE param_code='stop_tts_notify_voice';
UPDATE sys_params SET remark='Thư mục dữ liệu nhật ký' WHERE param_code='log.data_dir';
UPDATE sys_params SET remark='Thư mục tệp nhật ký' WHERE param_code='log.log_dir';
UPDATE sys_params SET remark='Tên tệp nhật ký' WHERE param_code='log.log_file';
UPDATE sys_params SET remark='Định dạng log console' WHERE param_code='log.log_format';
UPDATE sys_params SET remark='Định dạng log ghi tệp' WHERE param_code='log.log_format_file';
UPDATE sys_params SET remark='Mức log: INFO/DEBUG/WARNING/ERROR' WHERE param_code='log.log_level';
UPDATE sys_params SET remark='Thư mục nhạc local' WHERE param_code='plugins.play_music.music_dir';
UPDATE sys_params SET remark='Các đuôi tệp nhạc được hỗ trợ' WHERE param_code='plugins.play_music.music_ext';
UPDATE sys_params SET remark='Chu kỳ làm mới danh sách nhạc (giây)' WHERE param_code='plugins.play_music.refresh_time';
UPDATE sys_params SET remark='Máy chủ QWeather của plugin cũ' WHERE param_code='plugins.get_weather.api_host';
UPDATE sys_params SET remark='Khóa QWeather cũ; Robot Việt dùng OPENWEATHER_API_KEY' WHERE param_code='plugins.get_weather.api_key';
UPDATE sys_params SET remark='Địa điểm thời tiết mặc định của plugin cũ' WHERE param_code='plugins.get_weather.default_location';
UPDATE sys_params SET remark='Các nguồn tin của plugin cũ' WHERE param_code='plugins.get_news.category_urls';
UPDATE sys_params SET remark='RSS mặc định của plugin cũ' WHERE param_code='plugins.get_news.default_rss_url';
UPDATE sys_params SET remark='Khóa API Home Assistant' WHERE param_code='plugins.home_assistant.api_key';
UPDATE sys_params SET remark='Địa chỉ Home Assistant' WHERE param_code='plugins.home_assistant.base_url';
UPDATE sys_params SET remark='Thiết bị Home Assistant' WHERE param_code='plugins.home_assistant.devices';
UPDATE sys_params SET remark='Mã truy cập SMS Aliyun' WHERE param_code='aliyun.sms.access_key_id';
UPDATE sys_params SET remark='Khóa bí mật SMS Aliyun' WHERE param_code='aliyun.sms.access_key_secret';
UPDATE sys_params SET remark='Tên hiển thị SMS Aliyun' WHERE param_code='aliyun.sms.sign_name';
UPDATE sys_params SET remark='Mã mẫu SMS Aliyun' WHERE param_code='aliyun.sms.sms_code_template_code';
UPDATE sys_params SET remark='Cấu hình XiaoZhi kế thừa' WHERE param_code='xiaozhi';
