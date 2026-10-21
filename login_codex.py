"""Sign Codex in with your ChatGPT account so the GPT player can run.

Run once: python login_codex.py
"""

from openai_codex import Codex

with Codex() as codex:
    account = codex.account()
    if account.account is not None:
        print("Codex is already signed in.")
    else:
        login = codex.login_chatgpt_device_code()
        print(f"Open {login.verification_url} and enter the code: {login.user_code}")
        login.wait()
        print("Signed in. Start the app with: python app.py")
