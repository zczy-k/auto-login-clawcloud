# 文件名: login_script.py
import os
import pyotp
from playwright.sync_api import TimeoutError, sync_playwright
from playwright_stealth import Stealth


APP_URL = "https://ap-northeast-1.run.claw.cloud/"


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


def page_has_any_text(page, texts):
    for text in texts:
        if page.get_by_text(text).count() > 0:
            return True
    return False


def detect_post_password_error(page):
    if page_has_any_text(page, [
        "Incorrect username or password.",
        "用户名或密码错误",
        "密码错误",
        "Incorrect password",
        "Invalid username or password",
    ]):
        return "GitHub 用户名或密码错误"

    return None


def detect_post_2fa_error(page):
    if page_has_any_text(page, [
        "Invalid two-factor code",
        "Two-factor authentication failed",
        "验证码错误",
        "双重验证失败",
        "Incorrect code",
    ]):
        return "GitHub 2FA 验证码错误或已过期"

    return None


def detect_structure_issue(page):
    if "github.com" in page.url and not (
        page.locator("#login_field").count() > 0
        or page.locator("#password").count() > 0
        or page.locator("#app_totp").count() > 0
        or page.locator("#js-oauth-authorize-btn").count() > 0
    ):
        return "页面结构可能已变化，未识别到预期的 GitHub 登录/验证元素"

    if "claw.cloud" in page.url and page.locator("button.chakra-button:has-text('GitHub')").count() == 0:
        return "ClawCloud 登录页面结构可能已变化，未找到 GitHub 登录按钮"

    return None


def classify_final_failure(page, final_url):
    password_error = detect_post_password_error(page)
    if password_error:
        return password_error

    two_fa_error = detect_post_2fa_error(page)
    if two_fa_error:
        return two_fa_error

    structure_issue = detect_structure_issue(page)
    if structure_issue:
        return structure_issue

    if "signin" in final_url:
        return "最终跳转回登录页面，说明登录状态未建立，可能是账号信息错误或站点流程变化"

    if "github.com" in final_url:
        return f"流程最终仍停留在 GitHub 页面，可能是登录流程变化或校验未通过，当前 URL: {final_url}"

    return f"最终未跳转到预期控制台页面，当前 URL: {final_url}"


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

            page.goto(APP_URL)
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(3000)
            page.screenshot(path="01_home_page.png")
            print("📸 已截图: 01_home_page.png")

            print("🔍 [Step 2] 使用 JS 原生指令点击 GitHub 按钮...")
            try:
                login_button = page.locator("button.chakra-button:has-text('GitHub')")
                if login_button.count() == 0:
                    fail("ClawCloud 页面结构变化：未找到 GitHub 登录按钮", page)
                login_button.first.evaluate("el => el.click()")
                page.wait_for_timeout(3000)
                page.screenshot(path="02_after_click_github.png")
                print("📸 已截图: 02_after_click_github.png")
            except SystemExit:
                raise
            except Exception as e:
                fail(f"点击 GitHub 登录按钮失败，可能是页面结构变化或前端交互异常: {e}", page)

            print("⏳ [Step 3] 检查 GitHub 登录页...")
            try:
                page.wait_for_url(lambda url: "github.com" in url, timeout=15000)
            except TimeoutError as e:
                fail(f"点击 GitHub 后未跳转到 GitHub 登录页，可能是 ClawCloud 页面结构变化或登录入口失效: {e}", page)

            try:
                if "login" in page.url or page.locator("#login_field").count() > 0:
                    if page.locator("#login_field").count() == 0 or page.locator("#password").count() == 0:
                        fail("GitHub 登录页面结构变化：未找到用户名或密码输入框", page)
                    page.fill("#login_field", username)
                    page.fill("#password", password)
                    page.click("input[name='commit']")
                    page.wait_for_timeout(3000)
                page.screenshot(path="03_github_login.png")
                print("📸 已截图: 03_github_login.png")
            except SystemExit:
                raise
            except Exception as e:
                fail(f"未能进入或完成 GitHub 账号密码登录页，可能是页面结构变化: {e}", page)

            print("🔐 [Step 4] 检查 2FA 双重验证...")
            page.wait_for_timeout(3000)
            if "two-factor" in page.url or page.locator("#app_totp").count() > 0:
                if not totp_secret:
                    fail("检测到 GitHub 2FA 页面，但未配置 GH_2FA_SECRET", page)
                if page.locator("#app_totp").count() == 0:
                    fail("GitHub 2FA 页面结构变化：未找到验证码输入框", page)
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
                except SystemExit:
                    raise
                except Exception as e:
                    fail(f"填入或提交 2FA 验证码失败，可能是 2FA 页面结构变化: {e}", page)
            page.screenshot(path="04_after_2fa.png")
            print("📸 已截图: 04_after_2fa.png")

            print("⚠️ [Step 5] 检查授权请求...")
            if "authorize" in page.url.lower() or page.locator("#js-oauth-authorize-btn").count() > 0:
                try:
                    auth_btn = page.locator("button[name='authorize_app'], #js-oauth-authorize-btn, button:has-text('Authorize')")
                    if auth_btn.count() == 0:
                        fail("GitHub 授权页面结构变化：未找到 Authorize 按钮", page)
                    auth_btn.first.click(timeout=5000)
                    print("✅ 已点击授权(Authorize)按钮")
                    page.wait_for_timeout(4000)
                except SystemExit:
                    raise
                except Exception as e:
                    fail(f"点击授权按钮失败，可能是授权页面结构变化: {e}", page)
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
                fail(classify_final_failure(page, final_url), page)
        finally:
            browser.close()


if __name__ == "__main__":
    run_login()
