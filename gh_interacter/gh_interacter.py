from flask import Flask, request, jsonify
import requests
import base64
import os

app = Flask(__name__)

@app.route('/pr_content', methods=['GET'])
def get_pr_content():
    repo_full_name = request.args.get('repo_full_name')
    pr_number = request.args.get('pr_number')

    if not repo_full_name or not pr_number:
        return jsonify({'code': 400, 'message': 'Missing repo_full_name or pr_number'}), 400

    # 获取PR的基本信息
    github_api_url = f"https://api.github.com/repos/{repo_full_name}/pulls/{pr_number}"
    response = requests.get(github_api_url)

    if response.status_code == 404:
        return jsonify({'code': 404, 'message': 'Pull Request not found'}), 404
    elif response.status_code != 200:
        return jsonify({'code': response.status_code, 'message': 'Unexpected error occurred'}), response.status_code

    # 获取PR的diff
    diff_url = response.json().get('diff_url')
    if not diff_url:
        return jsonify({'code': 500, 'message': 'Failed to get diff URL'}), 500

    diff_response = requests.get(diff_url, headers={'Accept': 'application/vnd.github.v3.diff'})

    if diff_response.status_code != 200:
        return jsonify({'code': diff_response.status_code, 'message': 'Failed to get PR diff'}), diff_response.status_code

    # 返回PR的基本信息和diff
    pr_content = response.json()
    return jsonify({
        'title': pr_content.get('title'),
        'body': pr_content.get('body'),
        'code_changes': diff_response.text  # 注意，这可能是一个很大的字符串
    })

@app.route('/file_content', methods=['GET'])
def get_file_content():
    repo_full_name = request.args.get('repo_full_name')
    file_path = request.args.get('file_path')

    if not repo_full_name or not file_path:
        return jsonify({'code': 400, 'message': 'Missing repo_full_name or file_path'}), 400

    github_api_url = f"https://api.github.com/repos/{repo_full_name}/contents/{file_path}"
    response = requests.get(github_api_url)

    if response.status_code != 200:
        return jsonify({'code': response.status_code, 'message': 'Failed to fetch file content'}), response.status_code

    file_content_encoded = response.json().get('content')
    if file_content_encoded is None:
        return jsonify({'code': 500, 'message': 'No content found in the response'}), 500

    # 对Base64编码的内容进行解码
    file_content_decoded = base64.b64decode(file_content_encoded).decode('utf-8')
    return jsonify({'content': file_content_decoded})

@app.route('/issue_info', methods=['GET'])
def get_issue_info():
    repo_full_name = request.args.get('repo_full_name')
    issue_number = request.args.get('issue_number')

    if not repo_full_name or not issue_number:
        return jsonify({'code': 400, 'message': 'Missing repo_full_name or issue_number'}), 400

    github_api_url = f"https://api.github.com/repos/{repo_full_name}/issues/{issue_number}"
    response = requests.get(github_api_url)

    if response.status_code != 200:
        return jsonify({'code': response.status_code, 'message': 'Failed to fetch issue info'}), response.status_code

    issue_info = response.json()
    return jsonify({
        'title': issue_info.get('title'),
        'description': issue_info.get('body')
    })

@app.route('/submit_pr_comment', methods=['POST'])
def submit_pr_comment():
    token = os.environ.get('GITHUB_TOKEN')
    if not token:
        return jsonify({'code': 401, 'message': 'GitHub access token is not set'}), 401

    repo_full_name = request.json.get('repo_full_name')
    pr_number = request.json.get('pr_number')
    comment_body = request.json.get('comment_body')

    if not repo_full_name or not pr_number or not comment_body:
        return jsonify({'code': 400, 'message': 'Missing required parameters'}), 400

    comment_url = f"https://api.github.com/repos/{repo_full_name}/issues/{pr_number}/comments"
    headers = {
        'Authorization': f'token {token}',
        'Accept': 'application/vnd.github.v3+json'
    }
    data = {
        'body': comment_body
    }
    response = requests.post(comment_url, headers=headers, json=data)

    if response.status_code != 201:
        return jsonify({'code': response.status_code, 'message': 'Failed to create comment'}), response.status_code

    return jsonify({'message': 'Comment created successfully'}), 201

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000)