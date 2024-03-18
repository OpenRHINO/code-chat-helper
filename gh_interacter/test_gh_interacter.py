import unittest
from unittest.mock import patch
from gh_interacter import app  
import base64
import os

RHINO_API_KEY = os.getenv("RHINO_API_KEY")

class MockResponse:
    def __init__(self, json_data, status_code, text_data=None):
        self.json_data = json_data
        self.status_code = status_code
        self.text = text_data 

    def json(self):
        return self.json_data

class FlaskAppTestCase(unittest.TestCase):

    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

    @patch('requests.get')
    def test_require_api_key_decorator(self, mock_get):
        # 测试缺少 API 密钥的情况
        response = self.app.get('/pr_content')  # No API key
        self.assertEqual(response.status_code, 401)

        # 测试无效 API 密钥的情况
        response = self.app.get('/pr_content', headers={'X-Api-Key': 'valid_api_key'})
        self.assertEqual(response.status_code, 401)

        # 测试有效 API 密钥的情况
        response = self.app.get('/pr_content', headers={'X-Api-Key': RHINO_API_KEY})
        self.assertNotEqual(response.status_code, 401)  # 期望不是 401，因为我们提供了有效的 API 密钥

    @patch('requests.get')
    def test_pr_content_success(self, mock_get):
        # 模拟 GitHub API 返回的 PR 信息和 diff
        pr_response = MockResponse({
            'title': 'PR Title',
            'body': 'PR description here.',
            'head': {
                'ref': 'source_branch',
                'repo': {'full_name': 'user/source_repo'}
            },
            'diff_url': 'http://example.com/diff'
        }, 200)
        diff_response = MockResponse(None, 200, 'Diff content here.')

        mock_get.side_effect = [pr_response, diff_response]

        response = self.app.get('/pr_content?repo_full_name=user/repo&pr_number=1', headers={'X-Api-Key': RHINO_API_KEY})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['title'], 'PR Title')
        self.assertIn('Diff content here.', response.json['code_changes'])

    @patch('requests.get')
    def test_pr_content_missing_params(self, mock_get):
        # 测试缺少 repo_full_name 参数的情况
        response = self.app.get('/pr_content?pr_number=1', headers={'X-Api-Key': RHINO_API_KEY})
        self.assertEqual(response.status_code, 400)

        # 测试缺少 pr_number 参数的情况
        response = self.app.get('/pr_content?repo_full_name=user/repo', headers={'X-Api-Key': RHINO_API_KEY})
        self.assertEqual(response.status_code, 400)

    @patch('requests.get')
    def test_pr_content_pr_not_found(self, mock_get):
        # 模拟 PR 未找到的情况
        mock_get.return_value = MockResponse(None, 404)

        response = self.app.get('/pr_content?repo_full_name=user/repo&pr_number=999', headers={'X-Api-Key': RHINO_API_KEY})
        self.assertEqual(response.status_code, 404)

    @patch('requests.get')
    def test_pr_content_api_failure(self, mock_get):
        # 模拟 GitHub API 调用失败的情况
        mock_get.return_value = MockResponse(None, 500)

        response = self.app.get('/pr_content?repo_full_name=user/repo&pr_number=1', headers={'X-Api-Key': RHINO_API_KEY})
        self.assertEqual(response.status_code, 500)

    @patch('requests.get')
    def test_file_content_success(self, mock_get):
        # 模拟 GitHub API 返回的文件内容
        mock_get.return_value = MockResponse({
            'content': base64.b64encode(b'file content here').decode('utf-8')
        }, 200)

        response = self.app.get('/file_content?repo_full_name=user/repo&file_path=/path/to/file&branch_name=main', headers={'X-Api-Key': RHINO_API_KEY})
        self.assertEqual(response.status_code, 200)
        self.assertIn('file content here', response.json['content'])

    @patch('requests.get')
    def test_file_content_missing_params(self, mock_get):
        # 测试缺少 repo_full_name 参数的情况
        response = self.app.get('/file_content?file_path=/path/to/file&branch_name=main', headers={'X-Api-Key': RHINO_API_KEY})
        self.assertEqual(response.status_code, 400)

        # 测试缺少 file_path 参数的情况
        response = self.app.get('/file_content?repo_full_name=user/repo&branch_name=main', headers={'X-Api-Key': RHINO_API_KEY})
        self.assertEqual(response.status_code, 400)

    @patch('requests.get')
    def test_file_content_no_branch_found(self, mock_get):
        # 模拟未找到 main 或 master 分支的情况
        mock_get.side_effect = [MockResponse(None, 404), MockResponse(None, 404)]  # 先 main 后 master

        response = self.app.get('/file_content?repo_full_name=user/repo&file_path=/path/to/file', headers={'X-Api-Key': RHINO_API_KEY})
        self.assertEqual(response.status_code, 404)

    @patch('requests.get')
    def test_file_content_api_failure(self, mock_get):
        # 模拟 GitHub API 调用失败的情况
        mock_get.return_value = MockResponse(None, 500)

        response = self.app.get('/file_content?repo_full_name=user/repo&file_path=/path/to/file&branch_name=main', headers={'X-Api-Key': RHINO_API_KEY})
        self.assertEqual(response.status_code, 500)

    @patch('requests.get')
    def test_get_issue_info_success(self, mock_get):
        mock_get.return_value = MockResponse({
            'title': 'Issue Title',
            'body': 'Issue description here.'
        }, 200)

        response = self.app.get('/issue_info?repo_full_name=user/repo&issue_number=1', headers={'X-Api-Key': RHINO_API_KEY})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['title'], 'Issue Title')
        self.assertEqual(response.json['description'], 'Issue description here.')

    @patch('requests.get')
    def test_get_issue_info_missing_params(self, mock_get):
        response = self.app.get('/issue_info?repo_full_name=user/repo', headers={'X-Api-Key': RHINO_API_KEY})
        self.assertEqual(response.status_code, 400)

        response = self.app.get('/issue_info?issue_number=1', headers={'X-Api-Key': RHINO_API_KEY})
        self.assertEqual(response.status_code, 400)

    @patch('requests.get')
    def test_get_issue_info_api_failure(self, mock_get):
        mock_get.return_value = MockResponse(None, 404)
        response = self.app.get('/issue_info?repo_full_name=user/repo&issue_number=999', headers={'X-Api-Key': RHINO_API_KEY})
        self.assertEqual(response.status_code, 404)

    @patch('requests.post')
    def test_submit_pr_comment_success(self, mock_post):
        mock_post.return_value = MockResponse({'message': 'Comment created successfully'}, 201)
        response = self.app.post('/submit_pr_comment', json={
            'repo_full_name': 'user/repo',
            'pr_number': '1',
            'comment_body': 'This is a test comment'
        }, headers={'X-Api-Key': RHINO_API_KEY})
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json['message'], 'Comment created successfully')

    @patch('requests.post')
    def test_submit_pr_comment_missing_params(self, mock_post):
        response = self.app.post('/submit_pr_comment', json={
            'repo_full_name': 'user/repo',
            'pr_number': '1'
        }, headers={'X-Api-Key': RHINO_API_KEY})
        self.assertEqual(response.status_code, 400)

        response = self.app.post('/submit_pr_comment', json={
            'pr_number': '1',
            'comment_body': 'This is a test comment'
        }, headers={'X-Api-Key': RHINO_API_KEY})
        self.assertEqual(response.status_code, 400)

    @patch('requests.post')
    def test_submit_pr_comment_api_failure(self, mock_post):
        mock_post.return_value = MockResponse({'message': 'Failed to create comment'}, 400)
        response = self.app.post('/submit_pr_comment', json={
            'repo_full_name': 'user/repo',
            'pr_number': '1',
            'comment_body': 'This is a test comment'
        }, headers={'X-Api-Key': RHINO_API_KEY})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json['message'], 'Failed to create comment')

    @patch('requests.get')
    def test_repo_structure_success(self, mock_get):
        # 模拟检查分支存在的情况
        mock_get.side_effect = [
            MockResponse({'sha': 'dummy_sha'}, 200),  # 模拟获取最新提交SHA的响应
            MockResponse({  # 模拟获取目录树的响应
                'tree': [
                    {'path': 'dir1', 'type': 'tree'},
                    {'path': 'file1.txt', 'type': 'blob'}
                ]
            }, 200)
        ]

        response = self.app.get('/repo_structure?repo_full_name=user/repo&branch_name=main',headers={'X-Api-Key': RHINO_API_KEY})
        self.assertEqual(response.status_code, 200)
        json_data = response.get_json()
        self.assertIn('dir1', json_data['directories'])
        self.assertIn('file1.txt', json_data['files'])

    @patch('requests.get')
    def test_repo_structure_missing_params(self, mock_get):
        # 测试缺少 repo_full_name 参数的情况
        response = self.app.get('/repo_structure?branch_name=main', headers={'X-Api-Key': RHINO_API_KEY})
        self.assertEqual(response.status_code, 400)

        # 测试 repo_full_name 格式错误的情况
        response = self.app.get('/repo_structure?repo_full_name=invalid&branch_name=main', headers={'X-Api-Key': RHINO_API_KEY})
        self.assertEqual(response.status_code, 400)

    @patch('requests.get')
    def test_repo_structure_no_branch_found(self, mock_get):
        # 模拟未找到 main 或 master 分支的情况
        mock_get.side_effect = [MockResponse(None, 404), MockResponse(None, 404)]  # 先 main 后 master

        response = self.app.get('/repo_structure?repo_full_name=user/repo', headers={'X-Api-Key': RHINO_API_KEY})
        self.assertEqual(response.status_code, 404)

    @patch('requests.get')
    def test_repo_structure_api_failure(self, mock_get):
        # 模拟 GitHub API 调用失败的情况
        mock_get.return_value = MockResponse(None, 500)

        response = self.app.get('/repo_structure?repo_full_name=user/repo&branch_name=main', headers={'X-Api-Key': RHINO_API_KEY})
        self.assertEqual(response.status_code, 500)

if __name__ == '__main__':
    unittest.main()
