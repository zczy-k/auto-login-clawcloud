# 文件名: login_script.py
import os
import pyotp
from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth


def set_result(status, reason, final_url=""):
    with open("login_result.txt", "w", encoding="utf-8") as f:
        f.write(f"STATUS={status}\n")
        f.write(f"REASON={reason}\n")
        f.write(f"FINAL_URL={final_url}\n")


def fail(reason, page=None, exit_code=1):
    final_url = ""
    if page is not None:
        try:
            final_url = page.url
            page.screenshot(path="06_final_result.png")
            print("📸 已截图: 06_final_result.png")
        except Exception as screenshot_error:
            print(f"⚠️ 保存最终截图失败: {screenshot_error}")
    set_result("failure", reason, final_url)
    print(f"😭😭😭 登录失败: {reason}")
    raise SystemExit(exit_code)


def run_login():
    username = os.environ.get("GH_USERNAME")
    password = os.environ.get("GH_PASSWORD")
    totp_secret = os.environ.get("GH_2FA_SECRET")

    if not username or not password:
        set_result("failure", "未设置 GH_USERNAME 或 GH_PASSWORD 环境变量")
        print("❌ 错误: 未设置账号密码环境变量。")
        raise SystemExit(1)

    print("🚀 [Step 1] 访问 ClawCloud...")
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            args=["--disable-blink-features=AutomationControlled"]
        )
        context = browser.new_context(viewport={"width": 1920, "height": 1080})
        page = context.new_page()

        try:
            Stealth().apply_stealth_sync(page)

            page.goto("https://ap-northeast-1.run.claw.cloud/")
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(3000)
            page.screenshot(path="01_home_page.png")
            print("📸 已截图: 01_home_page.png")

            print("🔍 [Step 2] 使用 JS 原生指令点击 GitHub 按钮...")
            try:
                login_button = page.locator("button.chakra-button:has-text('GitHub')")
                if login_button.count() == 0:
                    fail("未找到 ClawCloud 页面上的 GitHub 登录按钮", page)
                login_button.first.evaluate("el => el.click()")
                page.wait_for_timeout(3000)
                page.screenshot(path="02_after_click_github.png")
                print("📸 已截图: 02_after_click_github.png")
            except SystemExit:
                raise
            except Exception as e:
                fail(f"点击 GitHub 登录按钮失败: {e}", page)

            print("⏳ [Step 3] 检查 GitHub 登录页...")
            try:
                page.wait_for_url(lambda url: "github.com" in url, timeout=15000)
                if "login" in page.url:
                    page.fill("#login_field", username)
                    page.fill("#password", password)
                    page.click("input[name='commit']")
                    page.wait_for_timeout(3000)
                page.screenshot(path="03_github_login.png")
                print("📸 已截图: 03_github_login.png")
            except Exception as e:
                fail(f"未能进入或完成 GitHub 账号密码登录页: {e}", page)

            print("🔐 [Step 4] 检查 2FA 双重验证...")
            page.wait_for_timeout(3000)
            if "two-factor" in page.url or page.locator("#app_totp").count() > 0:
                if not totp_secret:
                    fail("检测到 GitHub 2FA 页面，但未配置 GH_2FA_SECRET", page)
                try:
                    token = pyotp.TOTP(totp_secret).now()
                    page.fill("#app_totp", token)
                    print("✅ 已填入 6 位验证码")
                    try:
                        page.locator("button:has-text('Verify')").click(timeout=3000)
                        print("✅ 已主动点击 Verify 验证按钮")
                    except Exception:
                        pass
                    page.wait_for_timeout(4000)
                except Exception as e:
                    fail(f"填入或提交 2FA 验证码失败: {e}", page)
            page.screenshot(path="04_after_2fa.png")
            print("📸 已截图: 04_after_2fa.png")

            print("⚠️ [Step 5] 检查授权请求...")
            if "authorize" in page.url.lower() or page.locator("#js-oauth-authorize-btn").count() > 0:
                try:
                    auth_btn = page.locator("button[name='authorize_app'], #js-oauth-authorize-btn, button:has-text('Authorize')")
                    if auth_btn.count() == 0:
                        fail("检测到授权页面，但未找到 Authorize 按钮", page)
                    auth_btn.first.click(timeout=5000)
                    print("✅ 已点击授权(Authorize)按钮")
                    page.wait_for_timeout(4000)
                except SystemExit:
                    raise
                except Exception as e:
                    fail(f"点击授权按钮失败: {e}", page)
            page.screenshot(path="05_after_authorize.png")
            print("📸 已截图: 05_after_authorize.png")

            print("⏳ [Step 6] 等待最终跳转结果 (15秒)...")
            page.wait_for_timeout(15000)
            final_url = page.url
            page.screenshot(path="06_final_result.png")
            print("📸 已截图: 06_final_result.png")

            is_success = False
            if page.get_by_text("App Launchpad").count() > 0 or "console" in final_url or "private-team" in final_url:
                is_success = True
            elif "signin" not in final_url and "github.com" not in final_url:
                is_success = True

            if is_success:
                set_result("success", "登录成功", final_url)
                print("🎉🎉🎉 登录成功！")
            else:
                fail(f"最终未跳转到预期控制台页面，当前 URL: {final_url}", page)
        finally:
            browser.close()


if __name__ == "__main__":
    run_login()
