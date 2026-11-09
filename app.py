#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Katabump Auto Renew
SeleniumBase UC mode + نوتیف تلگرام فارسی
مناسب GitHub Actions با xvfb-run
"""

import os
import sys
import time
import requests
from seleniumbase import SB

EMAIL = os.environ.get("KATABUMP_EMAIL") or os.environ.get("EMAIL") or ""
PASSWORD = os.environ.get("KATABUMP_PASSWORD") or os.environ.get("PASSWORD") or ""
SERVER_ID = os.environ.get("SERVER_ID", "d1712508").strip()
TG_BOT_TOKEN = os.environ.get("TG_BOT_TOKEN", "").strip()
TG_CHAT_ID = os.environ.get("TG_CHAT_ID", "").strip()
HEADLESS = os.environ.get("HEADLESS", "false").lower() == "true"

LOGIN_URL = "https://control.katabump.com/auth/login"
SERVER_URL = f"https://control.katabump.com/server/{SERVER_ID}"

if not EMAIL or not PASSWORD:
    print("❌ KATABUMP_EMAIL / KATABUMP_PASSWORD (یا EMAIL / PASSWORD) تنظیم نشده")
    sys.exit(1)


def send_telegram(msg: str):
    if not TG_BOT_TOKEN or not TG_CHAT_ID:
        print("⚠️ تلگرام تنظیم نشده — رد شد")
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage",
            json={"chat_id": TG_CHAT_ID, "text": msg},
            timeout=10,
        )
        print("✅ نوتیف تلگرام ارسال شد")
    except Exception as e:
        print(f"❌ تلگرام: {e}")


def masked_email(email: str) -> str:
    if "@" not in email:
        return email[:2] + "****"
    name, domain = email.split("@", 1)
    if len(name) > 4:
        return f"{name[:2]}****{name[-2:]}@{domain}"
    return f"{name}@{domain}"


def now_tehran() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(time.time() + 3.5 * 3600))


def notify(status: str, extra: str = "", error: str = ""):
    lines = [
        "🎮 اعلان تمدید Katabump",
        "",
        status,
        f"👤 حساب: {masked_email(EMAIL)}",
        f"🖥️ سرور: {SERVER_ID}",
    ]
    if extra:
        lines.append(extra)
    if error:
        lines.append(f"⚠️ خطا: {error}")
    lines.append(f"⏱️ زمان اجرا: {now_tehran()}")
    send_telegram("\n".join(lines))


def main():
    print("#" * 32)
    print("  Katabump Auto Renew")
    print("#" * 32)

    with SB(uc=True, headless=HEADLESS, locale_code="en-US") as sb:
        try:
            print("🔄 ورود به صفحه لاگین Katabump...")
            sb.open(LOGIN_URL)
            sb.wait_for_ready_state_complete()
            sb.sleep(3)

            print("🔑 وارد کردن اطلاعات...")
            # چند سلکتور پشتیبان
            filled = False
            for user_sel in [
                'input[name="username"]',
                'input[name="email"]',
                'input[type="email"]',
                'input[type="text"]',
            ]:
                try:
                    if sb.is_element_visible(user_sel):
                        sb.input(user_sel, EMAIL)
                        filled = True
                        break
                except Exception:
                    continue

            if not filled:
                raise Exception("فیلد ایمیل/نام‌کاربری پیدا نشد")

            pass_filled = False
            for pass_sel in ['input[name="password"]', 'input[type="password"]']:
                try:
                    if sb.is_element_visible(pass_sel):
                        sb.input(pass_sel, PASSWORD)
                        pass_filled = True
                        break
                except Exception:
                    continue

            if not pass_filled:
                raise Exception("فیلد پسورد پیدا نشد")

            sb.sleep(1)
            clicked_login = False
            for btn in ['button[type="submit"]', 'input[type="submit"]', 'button:contains("Login")', 'button:contains("Sign in")']:
                try:
                    if sb.is_element_visible(btn):
                        sb.click(btn)
                        clicked_login = True
                        break
                except Exception:
                    continue

            if not clicked_login:
                raise Exception("دکمه ورود پیدا نشد")

            print("⏳ صبر بعد از لاگین...")
            sb.sleep(6)
            sb.wait_for_ready_state_complete()

            current_url = sb.get_current_url()
            print(f"📝 URL فعلی: {current_url}")

            if "login" in current_url.lower() or "auth" in current_url.lower():
                try:
                    sb.save_screenshot("login_fail.png")
                except Exception:
                    pass
                print("❌ لاگین ناموفق")
                notify("❌ ورود ناموفق", error="هنوز در صفحه لاگین هستید. Secrets را بررسی کنید.")
                sys.exit(1)

            print("✅ لاگین موفق")
            print(f"🌐 رفتن به سرور {SERVER_ID}...")
            sb.open(SERVER_URL)
            sb.wait_for_ready_state_complete()
            sb.sleep(4)

            # جستجوی دکمه Renew
            renew_selectors = [
                'button:contains("Renew")',
                'a:contains("Renew")',
                'button:contains("تمدید")',
                'a:contains("تمدید")',
                '[class*="renew" i]',
            ]

            renew_btn = None
            for sel in renew_selectors:
                try:
                    if sb.is_element_visible(sel):
                        text = (sb.get_text(sel) or "").strip().lower()
                        # اگر شمارش معکوس داشت، تمدید نکن
                        if "renew in" in text or "in " in text and ":" in text:
                            print(f"⏳ هنوز وقت تمدید نیست: {text}")
                            notify("⏳ هنوز زمان تمدید نرسیده", extra=f"متن دکمه: {text}")
                            return
                        renew_btn = sel
                        break
                except Exception:
                    continue

            if not renew_btn:
                print("ℹ️ دکمه Renew پیدا نشد یا فعال نیست")
                try:
                    sb.save_screenshot("no_renew.png")
                except Exception:
                    pass
                notify(
                    "ℹ️ دکمه Renew فعال نیست",
                    extra="سرور الان نیاز به تمدید ندارد یا سلکتور تغییر کرده است.",
                )
                return

            print(f"🟢 کلیک روی Renew: {renew_btn}")
            sb.click(renew_btn)
            sb.sleep(4)

            try:
                sb.save_screenshot("after_renew.png")
            except Exception:
                pass

            print("✅ کلیک Renew انجام شد")
            notify("✅ تمدید ارسال شد", extra="دکمه Renew با موفقیت کلیک شد.")

        except Exception as e:
            print(f"❌ خطا: {e}")
            try:
                sb.save_screenshot("error.png")
            except Exception:
                pass
            notify("❌ خطا در اجرای اسکریپت", error=str(e)[:300])
            sys.exit(1)

        print("🏁 تمام")


if __name__ == "__main__":
    main()
