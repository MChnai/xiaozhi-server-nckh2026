"""Demo does not contact a cloud API. Set NCKH_LLM_MODE=deepseek for real chat/tools."""
import os
from core.providers.llm.base import LLMProviderBase


class LLMProvider(LLMProviderBase):
    def __init__(self, config):
        self.delegate = None
        mode = os.environ.get("NCKH_LLM_MODE", "demo").strip().lower()
        if mode not in ("demo", "deepseek"):
            raise ValueError("NCKH_LLM_MODE phải là demo hoặc deepseek")
        if mode == "deepseek":
            if not os.environ.get("DEEPSEEK_API_KEY") and not config.get("api_key"):
                raise ValueError("Chưa đặt DEEPSEEK_API_KEY cho chế độ deepseek")
            from core.providers.llm.openai.openai import LLMProvider as OpenAIProvider
            settings = dict(config)
            settings["model_name"] = os.environ.get("DEEPSEEK_MODEL") or settings.get("model_name", "deepseek-flash")
            self.delegate = OpenAIProvider(settings)

    def response(self, session_id, dialogue, **kwargs):
        if self.delegate:
            yield from self.delegate.response(session_id, dialogue, **kwargs)
        else:
            yield "Máy chủ tiếng Việt đã nhận được lời nói của bạn. Đây là chế độ kiểm tra kết nối. Hãy cấu hình DeepSeek để trò chuyện và gọi công cụ."

    def response_with_functions(self, session_id, dialogue, functions=None, **kwargs):
        if self.delegate:
            yield from self.delegate.response_with_functions(session_id, dialogue, functions, **kwargs)
        else:
            for text in self.response(session_id, dialogue, **kwargs):
                yield text, None
