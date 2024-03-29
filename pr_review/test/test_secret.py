import requests
import json
import hmac
import hashlib
import os

# Replace these variables with your own values
url = os.environ.get("TEST_REVIEW_ENDPOINT", "http://127.0.0.1:8080/review_pr")
secret = os.environ.get("WEBHOOK_SECRET")

# test sample #1
# payload = {
#     "action": "opened",
#     "pull_request": {
#         "title": "Add new status ImageError to fix #25",
#         "body": "添加了一个新的状态ImageError，当镜像拉取失败时更新到该状态。",
#         "number": 37
#     },
#     "repository": {
#         "full_name": "OpenRHINO/RHINO-Operator"
#     }
# }

# test sample #2
# payload = {
#     "action": "opened",
#     "pull_request": {
#         "title": "json added",
#         "body": "convert logging info to json format",
#         "number": 8
#     },
#     "repository": {
#         "full_name": "ProgPanda/GPT-Assist"
#     }
# }

# test sample #3
payload = {
    "action": "opened",
        "pull_request": {
          "number": 2,
          "title": "Sample Pull Request",
          "body": "This is a sample pull request."
        },
        "repository": {
          "full_name": "LI-Mingyu/cndev-tutorial"
        }
}


headers = {
    "Content-Type": "application/json",
    "X-GitHub-Event": "pull_request"
}

def create_signature(payload, secret):
    hmac_obj = hmac.new(secret.encode(), json.dumps(
        payload).encode(), hashlib.sha256)
    return f"sha256={hmac_obj.hexdigest()}"


# Add the correct signature
headers["X-Hub-Signature-256"] = create_signature(payload, secret)

# Send the request
response = requests.post(url, json=payload, headers=headers)
print(response.status_code)
print(response.text)
