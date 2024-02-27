import os
import openai
from github import Github
from datetime import datetime
from tqdm import tqdm
import time

# Set up OpenAI API client
openai.api_key = os.environ.get("OPENAI_API_KEY")

# Set up GitHub API client
gh = Github(os.environ.get("GITHUB_TOKEN"))

def get_repo_files(repo_full_name, branch):
    start_time = time.time()  # 开始计时

    gh_repo = gh.get_repo(repo_full_name)
    contents = gh_repo.get_contents("", ref=branch)

    files_data = []

    while contents:
        file_content = contents.pop(0)
        if file_content.type == "dir":
            contents.extend(gh_repo.get_contents(file_content.path, ref=branch))
        elif file_content.type == "file":
            try:
                decoded_content = file_content.decoded_content.decode('utf-8')
                file_data = {"path": file_content.path, "content": decoded_content}
                files_data.append(file_data)
            except UnicodeDecodeError:
                print(f"Skipping non-text or binary file: {file_content.path}")

    end_time = time.time()  # 结束计时
    print(f"获取仓库文件耗时: {end_time - start_time:.2f}秒")
    return files_data

def analyze_project_with_gpt(files_data):
    start_time = time.time()  # 开始计时

    chat_history = [
        {"role": "system", "content": "You are an expert in computer science and software development, particularly skilled in code analysis. Your expertise includes understanding complex software architectures, identifying key functionalities within a codebase, and explaining the purpose and functionality of individual files within a project."},
        {"role": "user", "content": "I have a collection of files from a software project. Based on your expertise, I need a comprehensive analysis that includes: 1) An evaluation of the project's overall objective and the problems it aims to solve or the services it intends to provide. 2) A detailed breakdown of the project's main functionalities, with insights into how these functionalities are implemented within the codebase. 3) An overview of each file within the project, highlighting its specific role and contribution to the project's functionality. Please ensure that the analysis is thorough and understandable, even for individuals with limited technical background."}
    ]
    for file in files_data:
        chat_history.append({"role": "user", "content": f"File: {file['path']}\nContent: {file['content']}"})

    response = openai.ChatCompletion.create(
        model="gpt-4-0125-preview",
        messages=chat_history
    )
    # Get GPT's response in English
    analysis_result_in_english = response.choices[0].message['content']
    # Translate GPT's response to Chinese
    analysis_result_in_chinese = translate_to_chinese(analysis_result_in_english)
    end_time = time.time()  # 结束计时
    print(f"项目分析耗时: {end_time - start_time:.2f}秒")
    return analysis_result_in_english, analysis_result_in_chinese


def translate_to_chinese(text):
    translate_messages = [
        {"role": "system", "content": "You are a highly skilled translator capable of translating English text into Chinese with high accuracy."},
        {"role": "user", "content": f"Translate the following text into Chinese:\n\n{text}"}
    ]
    translated_response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",  # Use an appropriate chat model, gpt-3.5-turbo is suggested here as an example
        messages=translate_messages
    )
    return translated_response.choices[0]['message']['content'].strip()

def save_markdown_file(repo_full_name, branch, analysis_results, files_data):
    start_time = time.time()  # 开始计时

    timestamp_str = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    filename = f"project_analysis_{timestamp_str}.md"

    analysis_result_in_english, analysis_result_in_chinese = analysis_results

    markdown_content = f"# Project Analysis: {repo_full_name} (Branch: {branch})\n\n## GPT Analysis (English)\n{analysis_result_in_english}\n\n## GPT Analysis (Chinese)\n{analysis_result_in_chinese}\n\n## Files Overview\n"
    for file in files_data:
        markdown_content += f"- `{file['path']}`\n"

    with open(filename, "w") as md_file:
        md_file.write(markdown_content)

    print(f"Project analysis saved to {filename}")

    end_time = time.time()  # 结束计时
    print(f"保存分析结果耗时: {end_time - start_time:.2f}秒")


def main():
    steps = ["获取文件", "分析项目", "保存结果"]
    with tqdm(total=len(steps), desc="总进度") as pbar:
        repo_full_name = "unravel11/code-chat-helper"  # Replace with your target GitHub repository
        branch = "main"  # Replace with your target branch if different from "main"

        pbar.set_description("正在获取文件")
        files_data = get_repo_files(repo_full_name, branch)
        pbar.update(1)

        pbar.set_description("正在分析项目")
        analysis_result = analyze_project_with_gpt(files_data)
        pbar.update(1)

        pbar.set_description("正在保存结果")
        save_markdown_file(repo_full_name, branch, analysis_result, files_data)
        pbar.update(1)

        print("项目分析完成")

if __name__ == "__main__":
    main()
