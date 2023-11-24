import os
import hmac
import hashlib
from time import sleep
from openai import OpenAI
from github import Github
import re

# Set up OpenAI API client
client = OpenAI()
# Set up GitHub API client
gh = Github(os.environ.get("GITHUB_TOKEN"))


# Get the code changes from the PR
# gh_repo = gh.get_repo("pytorch/pytorch")
# gh_pr = gh_repo.get_pull(98916)

gh_repo = gh.get_repo("OpenRHINO/code-chat-reviewer")
gh_pr = gh_repo.get_pull(35)
gh_pr = gh_repo.get_pull(39)
# gh_pr = gh_repo.get_pull(38)
# gh_repo = gh.get_repo("OpenRHINO/RHINO-CLI")
# gh_pr = gh_repo.get_pull(58) #这里有很多exit(0)或exit(1)改为return err, 但是gpt-3.5-turbo生成的review中经常会弄反
# gh_pr = gh_repo.get_pull(46)


# gh_repo = gh.get_repo("kubernetes/kubernetes")
# gh_pr = gh_repo.get_pull(117245)

# gh_repo = gh.get_repo("ProgPanda/GPT-Assist")
# gh_pr = gh_repo.get_pull(8)

# Extract issue description from the PR body
ref_numbers = re.findall(r"#(\d+)", gh_pr.body)
# 确定每个引用是Issue还是PR，并收集Issue的描述
issues_description = ""
for ref_number in ref_numbers:
    issue_or_pr = gh_repo.get_issue(int(ref_number))
    if issue_or_pr.pull_request is None:  # 这意味着它是一个Issue
        issues_description += f"Issue #{ref_number}: {issue_or_pr.title}\n{issue_or_pr.body}\n\n"

# Extract the code changes from the PR
code_changes = []
for file in gh_pr.get_files():
    full_file_content = gh_repo.get_contents(file.filename, ref=gh_pr.head.sha).decoded_content.decode()
    code_changes.append({
        "filename": file.filename,
        "patch": file.patch,
        "full_content": full_file_content
    })

# Concatenate the changes into a single string
changes_str = "Title: " + gh_pr.title + "\n"
if gh_pr.body is not None:
    changes_str += "Body: " + gh_pr.body + "\n"
if issues_description != "":
    changes_str += "---------------Issues referenced---------------\n"
    changes_str += issues_description
for change in code_changes:
    changes_str += "---------------File changed---------------\n"
    changes_str += f"File: {change['filename']}\n\nPatch:\n{change['patch']}\n\nFull Content:\n{change['full_content']}\n"
# changes_str = preprocess_changes(changes_str)
# print(changes_str)



#--------------------------------------

thread = client.beta.threads.create()
print(thread.id)
message = client.beta.threads.messages.create(
    thread_id=thread.id,
    role="user",
    content=f"Review the following pull request. The patches are in standard `diff` format. Evaluate the pull request within the context of the referenced issues and full content of the code files.\n\n{changes_str}\n",
)

run = client.beta.threads.runs.create(
  thread_id=thread.id,
  assistant_id="asst_8Q4gf87T2848CdaH5v8Ry7XA",
  instructions="""
As an AI assistant with expertise in programming, your primary task is to review the pull request provided by the user. The code changes are presented in the standard `diff` format.

When generating your review, adhere to the following template:
**[Changes]**: Summarize the main changes made in the pull request in less than 50 words.
**[Suggestions]**: Provide any suggestions or improvements for the code. Focus on code quality, logic, potential bugs and performance problems. Refrain from mentioning document-related suggestions such as "I suggest adding some comments", etc.
**[Clarifications]**: (Optional) If there are parts of the pull request that are unclear or lack sufficient context, ask for clarification here. If not, this section can be omitted.
**[Conclusion]**: Conclude the review with an overall assessment.
**[Other]**: (Optional) If there are additional observations or notes, mention them here. If not, this section can be omitted.

"""
)
