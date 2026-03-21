#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import binascii
import html
import json
import re
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from html.parser import HTMLParser
from http.cookiejar import CookieJar
from typing import Any

FORM_URL = "https://input-form.jp/modules/nespresso_recyclingathome/"
FORM_POST_URL = urllib.parse.urljoin(FORM_URL, "index.php?page=customerform")
KEYCHAIN_SERVICE = "st.rio.nes_recycle"
KEYCHAIN_ACCOUNT = "profile"
HTTP_TIMEOUT = 20

TIME_CHOICES = ["指定なし", "午前", "14時～16時", "16時～18時", "18時～21時"]
TIME_VALUE_MAP = {
    "指定なし": "",
    "午前": "AM",
    "14時～16時": "14",
    "16時～18時": "16",
    "18時～21時": "18",
}

CAPSULE_TYPE_CODE_TO_LABEL = {
    "1": "オリジナル",
    "2": "ヴァーチュオ",
    "3": "オリジナルとヴァーチュオ",
}
CAPSULE_TYPE_LABEL_TO_CODE = {label: code for code, label in CAPSULE_TYPE_CODE_TO_LABEL.items()}
CAPSULE_TYPE_CODES = list(CAPSULE_TYPE_CODE_TO_LABEL.keys())
CAPSULE_TYPE_LABELS = list(CAPSULE_TYPE_CODE_TO_LABEL.values())


def log_info(message: str) -> None:
    print(f"[INFO] {message}", file=sys.stderr)


def log_error(message: str) -> None:
    print(f"[ERROR] {message}", file=sys.stderr)


def mask_sensitive_value(value: str, visible_suffix: int = 4) -> str:
    if not value:
        return value
    if len(value) <= visible_suffix:
        return "*" * len(value)
    return "*" * (len(value) - visible_suffix) + value[-visible_suffix:]


def capsule_type_code_to_label(code: str) -> str:
    return CAPSULE_TYPE_CODE_TO_LABEL.get(str(code).strip(), "")


def normalize_capsule_type_code(value: Any) -> str:
    text = str(value).strip()

    if text in CAPSULE_TYPE_CODE_TO_LABEL:
        return text

    if text in CAPSULE_TYPE_LABEL_TO_CODE:
        return CAPSULE_TYPE_LABEL_TO_CODE[text]

    return text


def is_valid_capsule_type_code(value: str) -> bool:
    return normalize_capsule_type_code(value) in CAPSULE_TYPE_CODE_TO_LABEL


def parse_capsule_type_arg(value: str) -> str:
    normalized = normalize_capsule_type_code(value)
    if normalized not in CAPSULE_TYPE_CODE_TO_LABEL:
        raise argparse.ArgumentTypeError("カプセル種類は 1 / 2 / 3 のいずれかで指定してください。")
    return normalized


def masked_profile(profile: dict[str, str]) -> dict[str, str]:
    default_capsule_type_code = profile.get("default_capsule_type", "")
    default_capsule_type_label = capsule_type_code_to_label(default_capsule_type_code)

    return {
        "customer_number": mask_sensitive_value(profile["customer_number"]),
        "last_name": profile["last_name"],
        "first_name": profile["first_name"],
        "postal_code": mask_sensitive_value(profile["postal_code"], visible_suffix=3),
        "address1": profile["address1"][:3] + "***" if profile["address1"] else "",
        "address2": profile["address2"][:3] + "***" if profile["address2"] else "",
        "phone": mask_sensitive_value(profile["phone"]),
        "email": (
            profile["email"].split("@", 1)[0][:1] + "***@" + profile["email"].split("@", 1)[1]
            if "@" in profile["email"]
            else "***"
        ),
        "default_capsule_type": (
            f"{default_capsule_type_code}:{default_capsule_type_label}"
            if default_capsule_type_label
            else default_capsule_type_code
        ),
    }


def normalize_customer_number(value: str) -> str:
    digits = re.sub(r"\D", "", value)
    if len(digits) == 7:
        return f"0{digits}"
    return digits


def normalize_postal_code(value: str) -> str:
    return re.sub(r"\D", "", value)


def normalize_phone(value: str) -> str:
    return re.sub(r"\D", "", value)


def is_valid_customer_number(value: str) -> bool:
    return value.isdigit() and len(value) == 8


def is_valid_postal_code(value: str) -> bool:
    digits = normalize_postal_code(value)
    return len(digits) == 7


def is_valid_phone(value: str) -> bool:
    digits = normalize_phone(value)
    return 10 <= len(digits) <= 11


def is_valid_email(value: str) -> bool:
    return bool(re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", value))


def parse_date(value: str) -> str:
    try:
        return date.fromisoformat(value).isoformat()
    except ValueError as e:
        raise argparse.ArgumentTypeError("日付は YYYY-MM-DD 形式で指定してください。") from e


def build_http_opener() -> urllib.request.OpenerDirector:
    cookie_jar = CookieJar()
    return urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookie_jar))


def fetch_calendar_config() -> dict[str, str]:
    opener = build_http_opener()

    bootstrap_request = urllib.request.Request(
        urllib.parse.urljoin(FORM_URL, "index.php"),
        headers={
            "User-Agent": "nes_recycle/0.0.5",
            "Referer": FORM_URL,
        },
        method="GET",
    )

    try:
        with opener.open(bootstrap_request, timeout=HTTP_TIMEOUT) as response:
            response.read()
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"カレンダー初期化の HTTP エラー: {e.code}\n{body[:1000]}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"カレンダー初期化通信に失敗しました: {e}") from e

    calendar_request = urllib.request.Request(
        urllib.parse.urljoin(FORM_URL, "index.php?page=get_cal_day"),
        headers={
            "User-Agent": "nes_recycle/0.0.5",
            "Referer": urllib.parse.urljoin(FORM_URL, "index.php"),
            "X-Requested-With": "XMLHttpRequest",
        },
        method="GET",
    )

    try:
        with opener.open(calendar_request, timeout=HTTP_TIMEOUT) as response:
            body = response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"カレンダー設定取得の HTTP エラー: {e.code}\n{body[:1000]}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"カレンダー設定取得に失敗しました: {e}") from e

    try:
        payload = json.loads(body)
    except json.JSONDecodeError as e:
        raise RuntimeError("カレンダー設定レスポンスを JSON として解釈できませんでした。") from e

    if str(payload.get("result")) != "1":
        raise RuntimeError("カレンダー設定取得に失敗しました。")

    return {
        "shime_time_h": str(payload.get("shime_time_h", "23")),
        "shime_time_m": str(payload.get("shime_time_m", "0")),
        "flg_use_calender": str(payload.get("flg_use_calender", "0")),
        "afer_day_text": str(payload.get("afer_day_text", "1")),
    }


def resolve_min_collection_date(today: date | None = None) -> date:
    base_date = today or date.today()
    config = fetch_calendar_config()

    offset_days = int(config["afer_day_text"])
    candidate = base_date + timedelta(days=offset_days)

    if config["flg_use_calender"] == "1":
        cutoff = time(
            hour=int(config["shime_time_h"]),
            minute=int(config["shime_time_m"]),
        )
        now_time = datetime.now().time()
        if now_time >= cutoff:
            candidate += timedelta(days=1)

    return candidate


def positive_bags(value: str) -> int:
    try:
        bags = int(value)
    except ValueError as e:
        raise argparse.ArgumentTypeError("バッグ数は整数で指定してください。") from e

    if bags < 1:
        raise argparse.ArgumentTypeError("バッグ数は 1 以上で指定してください。")
    if bags > 10:
        raise argparse.ArgumentTypeError("バッグ数は 10 以下で指定してください。")

    return bags


def is_valid_profile(profile: Any) -> bool:
    if not isinstance(profile, dict):
        return False

    required_keys = [
        "customer_number",
        "last_name",
        "first_name",
        "postal_code",
        "address1",
        "phone",
        "email",
    ]
    for key in required_keys:
        value = profile.get(key)
        if not isinstance(value, str) or not value.strip():
            return False

    address2 = profile.get("address2", "")
    if not isinstance(address2, str):
        return False

    default_capsule_type = profile.get("default_capsule_type", "1")
    if not isinstance(default_capsule_type, str):
        return False

    return (
        is_valid_customer_number(normalize_customer_number(profile["customer_number"]))
        and is_valid_postal_code(profile["postal_code"])
        and bool(profile["last_name"].strip())
        and bool(profile["first_name"].strip())
        and bool(profile["address1"].strip())
        and is_valid_phone(profile["phone"])
        and is_valid_email(profile["email"].strip())
        and is_valid_capsule_type_code(default_capsule_type)
    )


def normalize_profile(profile: dict[str, Any]) -> dict[str, str]:
    default_capsule_type = normalize_capsule_type_code(profile.get("default_capsule_type", "1"))
    if default_capsule_type not in CAPSULE_TYPE_CODE_TO_LABEL:
        default_capsule_type = "1"

    return {
        "customer_number": normalize_customer_number(profile["customer_number"]),
        "last_name": profile["last_name"].strip(),
        "first_name": profile["first_name"].strip(),
        "postal_code": normalize_postal_code(profile["postal_code"]),
        "address1": profile["address1"].strip(),
        "address2": profile.get("address2", "").strip(),
        "phone": normalize_phone(profile["phone"]),
        "email": profile["email"].strip(),
        "default_capsule_type": default_capsule_type,
    }


def prompt_profile_value(
    label: str,
    default: str | None = None,
    required: bool = True,
    validator=None,
    normalizer=None,
    error_message: str | None = None,
) -> str:
    while True:
        prompt = f"{label}"
        if default:
            prompt += f" [{default}]"
        prompt += ": "
        value = input(prompt).strip()

        if not value:
            if default is not None:
                value = default
            elif not required:
                return ""

        if normalizer is not None:
            value = normalizer(value)

        if value:
            if validator is None or validator(value):
                return value
            print(error_message or f"{label} の形式が正しくありません。")


def capsule_type_prompt_default(code: str | None) -> str:
    normalized = normalize_capsule_type_code(code or "1")
    label = capsule_type_code_to_label(normalized)
    if label:
        return f"{normalized}:{label}"
    return "1:オリジナル"


def prompt_profile(profile_defaults: dict[str, str] | None = None) -> dict[str, Any]:
    defaults = profile_defaults or {}

    return {
        "customer_number": prompt_profile_value(
            "ネスプレッソのお客様番号",
            default=defaults.get("customer_number"),
            validator=is_valid_customer_number,
            normalizer=normalize_customer_number,
            error_message="お客様番号は7桁または8桁の数字で入力してください。7桁の場合は先頭に 0 を補って保存します。",
        ),
        "last_name": prompt_profile_value("姓", default=defaults.get("last_name")),
        "first_name": prompt_profile_value("名", default=defaults.get("first_name")),
        "postal_code": prompt_profile_value(
            "郵便番号",
            default=defaults.get("postal_code"),
            validator=is_valid_postal_code,
            normalizer=normalize_postal_code,
            error_message="郵便番号は7桁の数字で入力してください。",
        ),
        "address1": prompt_profile_value(
            "回収先住所 (都道府県から番地まで)",
            default=defaults.get("address1"),
        ),
        "address2": prompt_profile_value(
            "回収先住所 (アパート・マンション名と部屋番号)",
            default=defaults.get("address2"),
            required=False,
        ),
        "phone": prompt_profile_value(
            "電話番号",
            default=defaults.get("phone"),
            validator=is_valid_phone,
            normalizer=normalize_phone,
            error_message="電話番号は10桁または11桁の数字で入力してください。",
        ),
        "email": prompt_profile_value(
            "メールアドレス",
            default=defaults.get("email"),
            validator=is_valid_email,
            error_message="メールアドレスの形式で入力してください。",
        ),
        "default_capsule_type": prompt_profile_value(
            "カプセル種類のデフォルト値",
            default=capsule_type_prompt_default(defaults.get("default_capsule_type")),
            validator=is_valid_capsule_type_code,
            normalizer=normalize_capsule_type_code,
            error_message="カプセル種類は 1 / 2 / 3 のいずれかを入力してください。",
        ),
    }


def load_profile_from_keychain() -> dict[str, Any] | None:
    try:
        result = subprocess.run(
            [
                "security",
                "find-generic-password",
                "-s",
                KEYCHAIN_SERVICE,
                "-a",
                KEYCHAIN_ACCOUNT,
                "-w",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        print(
            "macOS の security コマンドが見つかりませんでした。Keychain を利用できません。",
            file=sys.stderr,
        )
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        stderr = (e.stderr or "").strip()
        if "could not be found" in stderr.lower():
            return None
        print(
            "Keychain からプロフィールを読み込めませんでした。",
            file=sys.stderr,
        )
        if stderr:
            print(stderr, file=sys.stderr)
        sys.exit(1)

    secret = result.stdout.strip()
    if not secret:
        return None

    try:
        profile = json.loads(secret)
    except json.JSONDecodeError:
        try:
            decoded_secret = binascii.unhexlify(secret).decode("utf-8")
            profile = json.loads(decoded_secret)
        except binascii.Error, UnicodeDecodeError, json.JSONDecodeError:
            return None

    return profile


def save_profile_to_keychain(profile: dict[str, Any]) -> None:
    secret = json.dumps(profile, ensure_ascii=False)
    log_info("プロフィールを macOS Keychain に保存します。")
    try:
        subprocess.run(
            [
                "security",
                "add-generic-password",
                "-U",
                "-s",
                KEYCHAIN_SERVICE,
                "-a",
                KEYCHAIN_ACCOUNT,
                "-w",
                secret,
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        log_info("プロフィールを macOS Keychain に保存しました。")
    except FileNotFoundError:
        log_error("macOS の security コマンドが見つかりませんでした。Keychain へ保存できません。")
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        log_error("Keychain へのプロフィール保存に失敗しました。")
        stderr = (e.stderr or "").strip()
        if stderr:
            print(stderr, file=sys.stderr)
        sys.exit(1)


def delete_profile_from_keychain() -> None:
    try:
        result = subprocess.run(
            [
                "security",
                "delete-generic-password",
                "-s",
                KEYCHAIN_SERVICE,
                "-a",
                KEYCHAIN_ACCOUNT,
            ],
            check=False,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        print(
            "macOS の security コマンドが見つかりませんでした。Keychain を操作できません。",
            file=sys.stderr,
        )
        sys.exit(1)

    if result.returncode not in (0, 44):
        print(
            "Keychain のプロフィール削除に失敗しました。",
            file=sys.stderr,
        )
        stderr = (result.stderr or "").strip()
        if stderr:
            print(stderr, file=sys.stderr)
        sys.exit(1)


def initialize_profile(
    reason: str | None = None, profile_defaults: dict[str, str] | None = None
) -> dict[str, Any]:
    if reason:
        print("プロフィールの再登録を開始します。")
        print(f"理由: {reason}")
    else:
        print("プロフィールが未登録のため、初期設定を開始します。")

    if profile_defaults:
        print("[] 内の値は現在の保存内容です。Enter でそのまま利用できます。")
    else:
        print("Enter のみで確定すると、その項目は空欄になります。")

    print("アパート・マンション名と部屋番号は、Enter のみで空欄にできます。")
    print("カプセル種類のデフォルト値は、次の数字で指定してください。")
    print("  1: オリジナル")
    print("  2: ヴァーチュオ")
    print("  3: オリジナルとヴァーチュオ")
    log_info("プロフィール入力を開始します。")

    profile = prompt_profile(profile_defaults)

    log_info("プロフィール入力が完了しました。")
    profile = normalize_profile(profile)
    save_profile_to_keychain(profile)
    print("プロフィールを macOS Keychain に保存しました。次回以降はこの設定を使用します。")
    return profile


def load_profile() -> dict[str, str]:
    profile = load_profile_from_keychain()
    if profile is None:
        return initialize_profile()

    normalized_profile = normalize_profile(profile)

    if not is_valid_profile(profile):
        return initialize_profile(
            reason="必須項目の不足、または形式不正があります。",
            profile_defaults=normalized_profile,
        )

    return normalized_profile


def default_collection_date() -> str:
    return resolve_min_collection_date().isoformat()


def ensure_collection_date_not_past(value: str) -> None:
    selected = date.fromisoformat(value)
    minimum = resolve_min_collection_date()
    if selected < minimum:
        print(
            f"回収希望日は {minimum.isoformat()} 以降の日付を指定してください。",
            file=sys.stderr,
        )
        sys.exit(1)


def split_postal_code(postal_code: str) -> tuple[str, str]:
    normalized = normalize_postal_code(postal_code)
    return normalized[:3], normalized[3:]


def split_phone(phone: str) -> tuple[str, str, str]:
    digits = normalize_phone(phone)
    if len(digits) == 11:
        return digits[:3], digits[3:7], digits[7:]
    if len(digits) == 10:
        if digits.startswith(("03", "06")):
            return digits[:2], digits[2:6], digits[6:]
        return digits[:3], digits[3:6], digits[6:]
    raise ValueError("電話番号の桁数が不正です。")


def to_fullwidth_ascii(text: str) -> str:
    translation = str.maketrans(
        {chr(ord("!") + i): chr(ord("！") + i) for i in range(ord("~") - ord("!") + 1)}
    )
    translation[ord(" ")] = ord("　")
    return text.translate(translation)


def normalize_for_remote(value: str) -> str:
    return to_fullwidth_ascii(value)


@dataclass
class SubmissionContext:
    profile: dict[str, str]
    date_iso: str
    time_label: str
    capsule_type_code: str
    bags: int


@dataclass
class PreviewResult:
    html: str
    values: dict[str, str]
    summary: list[tuple[str, str]]
    error_messages: list[str]
    is_error: bool


class HiddenInputParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.values: dict[str, str] = {}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "input":
            return
        attr_map = dict(attrs)
        if (attr_map.get("type") or "").lower() != "hidden":
            return
        name = attr_map.get("name")
        if not name:
            return
        self.values[name] = attr_map.get("value") or ""


class ErrorMessageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._parts: list[str] = []

    def handle_data(self, data: str) -> None:
        text = data.strip()
        if text:
            self._parts.append(text)

    def messages(self) -> list[str]:
        text = "\n".join(self._parts)
        candidates = []
        for line in text.splitlines():
            normalized = re.sub(r"\s+", " ", line).strip()
            if not normalized:
                continue
            if "入力エラー" in normalized or "修正" in normalized:
                candidates.append(normalized)
                continue
            if "エラー" in normalized or "ご入力" in normalized or "存在しません" in normalized:
                candidates.append(normalized)
        deduped: list[str] = []
        for item in candidates:
            if item not in deduped:
                deduped.append(item)
        return deduped


def build_preview_payload(context: SubmissionContext) -> dict[str, str]:
    zip1, zip2 = split_postal_code(context.profile["postal_code"])
    tel1_1, tel1_2, tel1_3 = split_phone(context.profile["phone"])
    y, m, d = context.date_iso.split("-")
    capsule_type_label = CAPSULE_TYPE_CODE_TO_LABEL[context.capsule_type_code]

    payload: dict[str, str] = {
        "survey1": context.profile["customer_number"],
        "name1": normalize_for_remote(context.profile["last_name"]),
        "name2": normalize_for_remote(context.profile["first_name"]),
        "zip1": zip1,
        "zip2": zip2,
        "address1": normalize_for_remote(context.profile["address1"]),
        "address2": normalize_for_remote(context.profile["address2"]),
        "tel1_1": tel1_1,
        "tel1_2": tel1_2,
        "tel1_3": tel1_3,
        "email": context.profile["email"],
        "email_check": context.profile["email"],
        "receipt_day_button": "1",
        "receipt_day1": y,
        "receipt_day2": m,
        "receipt_day3": d,
        "receipt_time": TIME_VALUE_MAP[context.time_label],
        "survey3": "はい",
        "free_select_answer3": "はい",
        "free_select_answer2": "はい",
        "free_select_answer1": capsule_type_label,
        "daisu": str(context.bags),
        "action": "input_check",
        "save": "確認画面に進む",
    }
    return payload


def http_post_form(url: str, data: dict[str, str]) -> tuple[str, str]:
    encoded = urllib.parse.urlencode(data).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=encoded,
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "nes_recycle/0.0.5",
            "Referer": FORM_URL,
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=HTTP_TIMEOUT) as response:
            body = response.read().decode("utf-8", errors="replace")
            return body, response.geturl()
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP エラー: {e.code}\n{body[:1000]}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"通信に失敗しました: {e}") from e


def parse_hidden_inputs(html_text: str) -> dict[str, str]:
    parser = HiddenInputParser()
    parser.feed(html_text)
    return parser.values


def extract_form_action(html_text: str, form_name: str) -> str | None:
    pattern = re.compile(
        rf"""<form[^>]*\bname=["']{re.escape(form_name)}["'][^>]*\baction=["']([^"']+)["']""",
        re.IGNORECASE,
    )
    match = pattern.search(html_text)
    if not match:
        return None
    return html.unescape(match.group(1)).strip()


def parse_error_messages(html_text: str) -> list[str]:
    parser = ErrorMessageParser()
    parser.feed(html_text)
    return parser.messages()


def html_to_text(value: str) -> str:
    text = html.unescape(value)
    text = text.replace("\u3000", " ")
    return re.sub(r"\s+", " ", text).strip()


def summarize_preview(values: dict[str, str]) -> list[tuple[str, str]]:
    postal_code = f"{values.get('zip1', '')}-{values.get('zip2', '')}".strip("-")
    phone = "-".join(
        [
            part
            for part in [
                values.get("tel1_1", ""),
                values.get("tel1_2", ""),
                values.get("tel1_3", ""),
            ]
            if part
        ]
    )
    receipt_time_value = values.get("receipt_time", "")
    time_label = next(
        (label for label, remote in TIME_VALUE_MAP.items() if remote == receipt_time_value),
        receipt_time_value or "指定なし",
    )
    date_text = "/".join(
        [
            values.get("receipt_day1", ""),
            values.get("receipt_day2", ""),
            values.get("receipt_day3", ""),
        ]
    ).strip("/")

    return [
        ("お客様番号", values.get("survey1", "")),
        ("氏名", f"{values.get('name1', '')} {values.get('name2', '')}".strip()),
        ("郵便番号", postal_code),
        ("住所1", values.get("address1", "")),
        ("住所2", values.get("address2", "")),
        ("電話番号", phone),
        ("メールアドレス", values.get("email", "")),
        ("回収希望日", date_text),
        ("回収希望時間帯", time_label),
        ("リカバリーバッグ使用", values.get("survey3", "")),
        ("純正カプセルのみ", values.get("free_select_answer3", "")),
        ("水漏れなし", values.get("free_select_answer2", "")),
        ("カプセル種類", values.get("free_select_answer1", "")),
        ("バッグ数", values.get("daisu", "")),
    ]


def build_preview(context: SubmissionContext) -> PreviewResult:
    payload = build_preview_payload(context)
    log_info("確認画面生成用の POST を送信します。")
    html_text, final_url = http_post_form(FORM_POST_URL, payload)
    log_info(f"確認画面生成レスポンス URL: {final_url}")

    hidden_values = parse_hidden_inputs(html_text)
    error_messages = parse_error_messages(html_text)
    is_error = bool(error_messages) and "入力エラー" in "\n".join(error_messages)

    if not hidden_values:
        raise RuntimeError(
            "確認画面の hidden input を抽出できませんでした。フォーム仕様が変更された可能性があります。"
        )

    return PreviewResult(
        html=html_text,
        values=hidden_values,
        summary=summarize_preview(hidden_values),
        error_messages=error_messages,
        is_error=is_error,
    )


def print_preview_summary(preview: PreviewResult) -> None:
    print("確認画面の主要項目:")
    for label, value in preview.summary:
        print(f"- {label}: {html_to_text(value)}")


def print_error_messages(messages: list[str]) -> None:
    if not messages:
        return
    print("フォーム側のメッセージ:")
    for message in messages:
        print(f"- {html_to_text(message)}")


def confirm_submission(non_interactive: bool) -> bool:
    if non_interactive:
        return True

    while True:
        answer = input("この内容で本送信しますか？ [y/N]: ").strip().lower()
        if answer in {"y", "yes"}:
            return True
        if answer in {"", "n", "no"}:
            return False
        print("y または n を入力してください。")


def build_submit_payload(preview_values: dict[str, str]) -> dict[str, str]:
    payload = dict(preview_values)
    payload["save"] = "上記の内容で登録します"
    if "site_key" not in payload:
        payload["site_key"] = ""
    if "pattern_data" not in payload:
        payload["pattern_data"] = payload.get("pattern_data", "1")
    return payload


def is_submit_success(html_text: str) -> bool:
    text = html_to_text(re.sub(r"<[^>]+>", " ", html_text))
    success_keywords = [
        "お申し込みありがとうございました",
        "お申込みありがとうございました",
        "受付が完了",
        "送信完了",
        "お申し込み完了",
        "お申込み完了",
        "使用済みカプセル回収受付完了",
        "受付番号",
    ]
    return any(keyword in text for keyword in success_keywords)


def submit_final(preview: PreviewResult) -> tuple[bool, str]:
    payload = build_submit_payload(preview.values)

    confirm_form_action = extract_form_action(preview.html, "newdoc")
    if confirm_form_action:
        submit_url = urllib.parse.urljoin(FORM_URL, confirm_form_action)
    else:
        submit_url = urllib.parse.urljoin(FORM_URL, "index.php?page=entryfinish")

    log_info(f"本送信用の POST を送信します: {submit_url}")
    html_text, final_url = http_post_form(submit_url, payload)
    log_info(f"本送信レスポンス URL: {final_url}")

    success = is_submit_success(html_text)
    if not success and "customer_finalcheck" in final_url:
        success = True

    return success, html_text


def run_http_workflow(profile: dict[str, str], args: argparse.Namespace) -> None:
    ensure_collection_date_not_past(args.date)

    context = SubmissionContext(
        profile=profile,
        date_iso=args.date,
        time_label=args.time,
        capsule_type_code=args.capsule_type,
        bags=args.bags,
    )

    preview = build_preview(context)

    if preview.is_error:
        print_error_messages(preview.error_messages)
        print_preview_summary(preview)
        sys.exit(1)

    print_preview_summary(preview)

    if args.preview_only:
        print("preview-only: 本送信は行いません。")
        return

    if not confirm_submission(non_interactive=args.yes):
        print("送信を中止しました。")
        return

    ok, final_html = submit_final(preview)
    if ok:
        print("本送信が完了した可能性があります。受信メールも確認してください。")
        return

    print("本送信後の成功判定ができませんでした。ブラウザや受信メールで結果を確認してください。")
    error_messages = parse_error_messages(final_html)
    if error_messages:
        print_error_messages(error_messages)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="ネスプレッソ回収フォームへ HTTP POST で確認画面生成・本送信を行います。プロフィールは macOS Keychain に保存します。"
    )
    parser.add_argument(
        "--reset-profile",
        action="store_true",
        help="保存済みプロフィールを破棄して再登録する",
    )
    parser.add_argument(
        "--date",
        type=parse_date,
        default=None,
        help="YYYY-MM-DD（省略時: フォームサイトが許可している最小日付を自動取得）",
    )
    parser.add_argument(
        "--time",
        default="午前",
        choices=TIME_CHOICES,
        help="指定なし / 午前 / 14時～16時 / 16時～18時 / 18時～21時",
    )
    parser.add_argument(
        "--capsule-type",
        type=parse_capsule_type_arg,
        default=None,
        help="1=オリジナル / 2=ヴァーチュオ / 3=オリジナルとヴァーチュオ（省略時は Keychain 保存値）",
    )
    parser.add_argument("--bags", type=positive_bags, default=1, help="1以上10以下のバッグ数")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="通信を行わず設定内容のみ確認する",
    )
    parser.add_argument(
        "--preview-only",
        action="store_true",
        help="確認画面の生成だけ行い、本送信は行わない",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="確認プロンプトを省略して本送信まで進む",
    )
    args = parser.parse_args()

    if args.reset_profile:
        print("保存済みプロフィールを破棄して再登録します。")
        existing_profile = load_profile_from_keychain()
        profile_defaults = (
            normalize_profile(existing_profile) if existing_profile is not None else None
        )
        delete_profile_from_keychain()
        profile = initialize_profile(
            reason="--reset-profile が指定されました。",
            profile_defaults=profile_defaults,
        )
    else:
        profile = load_profile()

    if args.capsule_type is None:
        args.capsule_type = profile["default_capsule_type"]

    if args.date is None:
        args.date = default_collection_date()

    if args.dry_run:
        print("dry-run: 通信は行いません。")
        print(
            json.dumps(
                {
                    "profile": masked_profile(profile),
                    "date": args.date,
                    "time": args.time,
                    "capsule_type": {
                        "code": args.capsule_type,
                        "label": capsule_type_code_to_label(args.capsule_type),
                    },
                    "bags": args.bags,
                    "workflow": "http-post",
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return

    try:
        run_http_workflow(profile, args)
    except KeyboardInterrupt:
        print("\n中断しました。", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        log_error(str(e))
        sys.exit(1)


if __name__ == "__main__":
    main()
