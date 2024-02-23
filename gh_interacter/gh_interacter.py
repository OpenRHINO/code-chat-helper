from functools import wraps
from flask import Flask, request, jsonify, abort
import requests
import base64
import os

app = Flask(__name__)

RHINO_API_KEY = os.getenv("RHINO_API_KEY")

def require_api_key(view_function):
    @wraps(view_function)
    def decorated_function(*args, **kwargs):
        if request.headers.get('X-Api-Key') and request.headers.get('X-Api-Key') == RHINO_API_KEY:
            return view_function(*args, **kwargs)
        else:
            abort(401)  # Unauthorized access
    return decorated_function

def check_branch_exists(repo_full_name, branch_name):
    github_api_url = f"https://api.github.com/repos/{repo_full_name}/branches/{branch_name}"
    response = requests.get(github_api_url)
    return response.status_code == 200

@app.route('/pr_content', methods=['GET'])
@require_api_key
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
    # 获取PR的源分支和源仓库
    source_branch = pr_content.get('head', {}).get('ref')
    source_repo = pr_content.get('head', {}).get('repo', {}).get('full_name')
    
    return jsonify({
        'title': pr_content.get('title'),
        'body': pr_content.get('body'),
        'source_branch': source_branch,
        'source_repo': source_repo,      
        'code_changes': diff_response.text  # 注意，这可能是一个很大的字符串
    })

@app.route('/file_content', methods=['GET'])
@require_api_key
def get_file_content():
    repo_full_name = request.args.get('repo_full_name')
    file_path = request.args.get('file_path')
    branch_name = request.args.get('branch_name')
    if not branch_name:
        # 检查是否存在 main 或 master 分支
        if check_branch_exists(repo_full_name, "main"):
            branch_name = "main"
        elif check_branch_exists(repo_full_name, "master"):
            branch_name = "master"
        else:
            return jsonify({'code': 404, 'message': 'No main or master branch found'}), 404

    if not repo_full_name or not file_path:
        return jsonify({'code': 400, 'message': 'Missing repo_full_name or file_path'}), 400

    github_api_url = f"https://api.github.com/repos/{repo_full_name}/contents/{file_path}?ref={branch_name}"
    response = requests.get(github_api_url)

    if response.status_code != 200:
        return jsonify({'code': response.status_code, 'message': f'Failed to fetch file content from {branch_name} branch'}), response.status_code

    file_content_encoded = response.json().get('content')
    if file_content_encoded is None:
        return jsonify({'code': 500, 'message': 'No content found in the response'}), 500

    # 对Base64编码的内容进行解码
    file_content_decoded = base64.b64decode(file_content_encoded).decode('utf-8')
    return jsonify({'content': file_content_decoded})

@app.route('/issue_info', methods=['GET'])
@require_api_key
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
@require_api_key
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

@app.route('/repo_structure', methods=['GET'])
@require_api_key
def get_repo_structure():
    repo_full_name = request.args.get('repo_full_name')
    branch_name = request.args.get('branch_name') 

    if not branch_name:
        # 检查是否存在 main 或 master 分支
        if check_branch_exists(repo_full_name, "main"):
            branch_name = "main"
        elif check_branch_exists(repo_full_name, "master"):
            branch_name = "master"
        else:
            return jsonify({'code': 404, 'message': 'No main or master branch found'}), 404
        
    if not repo_full_name or '/' not in repo_full_name or len(repo_full_name.split('/')) != 2:
        return jsonify({'code': 400, 'message': 'Invalid or missing repo_full_name'}), 400

    # 获取最新提交的 SHA
    commits_url = f"https://api.github.com/repos/{repo_full_name}/commits/{branch_name}"
    commits_response = requests.get(commits_url)

    if commits_response.status_code != 200:
        return jsonify({'code': commits_response.status_code, 'message': 'Failed to get latest commit', 'details': commits_response.json()}), commits_response.status_code

    latest_commit_sha = commits_response.json().get('sha')
    if not latest_commit_sha:
        return jsonify({'code': 404, 'message': 'Latest commit SHA not found'}), 404

    # 获取目录树
    trees_url = f"https://api.github.com/repos/{repo_full_name}/git/trees/{latest_commit_sha}?recursive=1"
    trees_response = requests.get(trees_url)

    if trees_response.status_code != 200:
        return jsonify({'code': trees_response.status_code, 'message': 'Failed to get repository tree', 'details': trees_response.json()}), trees_response.status_code

    tree = trees_response.json().get('tree', [])
    repo_structure = {'directories': [], 'files': []}

    for item in tree:
        if item['type'] == 'tree':
            repo_structure['directories'].append(item['path'])
        elif item['type'] == 'blob':
            repo_structure['files'].append(item['path'])

    return jsonify(repo_structure)

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000)
