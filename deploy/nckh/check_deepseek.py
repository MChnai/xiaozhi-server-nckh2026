import argparse
import json
import os
import urllib.error
import urllib.request

from project import ROOT, parse_env


def main():
    parser = argparse.ArgumentParser(
        description="Kiểm tra DeepSeek, không in khóa API"
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--balance", action="store_true")
    group.add_argument("--chat", action="store_true")
    args = parser.parse_args()

    settings = dict(os.environ)
    try:
        if (ROOT / ".env").is_file():
            settings.update(parse_env(ROOT / ".env"))
    except ValueError as exc:
        raise SystemExit(str(exc))

    key = settings.get("DEEPSEEK_API_KEY", "").strip()
    if not key or "*" in key or key.lower().startswith("bearer "):
        raise SystemExit(
            "Đặt khóa API đầy đủ trong DEEPSEEK_API_KEY; "
            "không dùng Tracking ID, dấu * hoặc tiền tố Bearer."
        )

    headers = {
        "Authorization": "Bearer " + key,
        "Content-Type": "application/json",
    }
    endpoint = "/models"
    data = None

    if args.balance:
        endpoint = "/user/balance"
    elif args.chat:
        endpoint = "/chat/completions"
        data = json.dumps({
            "model": settings.get("DEEPSEEK_MODEL", "").strip()
                     or "deepseek-flash",
            "messages": [{
                "role": "user",
                "content": "Chào tôi bằng một câu tiếng Việt.",
            }],
            "thinking": {"type": "disabled"},
            "max_tokens": 64,
            "stream": False,
        }).encode("utf-8")

    request = urllib.request.Request(
        "https://api.deepseek.com" + endpoint,
        headers=headers,
        data=data,
    )

    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            body = json.load(response)

        if args.balance:
            available = body.get("is_available") is True
            print("Đủ số dư để gọi API:", "CÓ" if available else "KHÔNG")
            for item in body.get("balance_infos", []):
                print(
                    "Số dư:",
                    item.get("total_balance"),
                    item.get("currency"),
                )
            return 0 if available else 1

        if args.chat:
            print(body["choices"][0]["message"]["content"])
            print("Token đã dùng:", body.get("usage", {}))
        else:
            print(
                "Khóa được chấp nhận. Các model:",
                ", ".join(item["id"] for item in body.get("data", [])),
            )
        return 0

    except urllib.error.HTTPError as exc:
        tips = {
            401: "Khóa không hợp lệ. Dùng khóa đầy đủ, không dùng Tracking ID.",
            402: "Không đủ số dư. Vào DeepSeek Platform → Top up.",
            429: "Vượt giới hạn tần suất. Đợi rồi thử lại.",
            400: "Kiểm tra định dạng yêu cầu và tên model.",
            404: "Kiểm tra tên model và địa chỉ API.",
            422: "Tham số yêu cầu không hợp lệ.",
        }
        print(
            f"HTTP {exc.code}: "
            + tips.get(exc.code, "Dịch vụ DeepSeek gặp sự cố; thử lại sau.")
        )
        return 1

    except (urllib.error.URLError, TimeoutError):
        print("Không kết nối được DeepSeek. Kiểm tra mạng, DNS hoặc proxy.")
        return 1

    except (KeyError, IndexError, TypeError, ValueError):
        print("DeepSeek trả dữ liệu không đúng định dạng mong đợi.")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())