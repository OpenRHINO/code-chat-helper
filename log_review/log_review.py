import datetime
import json
import os
import openai
import requests
import subprocess
import logging
import time
from kubernetes import config, client


class JsonFormatter(logging.Formatter):
    def format(self, record):
        log_entry = {
            "asctime": self.formatTime(record, self.datefmt),
            "levelname": record.levelname,
            "message": record.getMessage(),
        }
        return json.dumps(log_entry)


# Set up logging
def setup_logging():
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    logHandler = logging.StreamHandler()
    formatter = JsonFormatter()
    logHandler.setFormatter(formatter)
    logger.addHandler(logHandler)
    return logger


def get_log(pod_name, namespace, since_seconds=3600 * 12):
    config.load_kube_config()
    v1 = client.CoreV1Api()
    log = v1.read_namespaced_pod_log(
        name=pod_name,
        namespace=namespace,
        since_seconds=since_seconds,
    )
    return log


def log_preprocess(log):
    log = log.split("\n")
    log = [json.loads(item) for item in log if item != ""]
    return log


# count how many tokens in each chunk
def count_tokens(log, chunk_size):
    tokens = 0
    for i in range(0, len(log), chunk_size):
        chunk = log[i : i + chunk_size]
        # count how many tokens in each chunk
        tokens += len(chunk.split(" "))

    return tokens


def get_gpt_log_review(
    log,
    chunk_size,
    model="gpt-3.5-turbo",
    max_tokens=100,
    temperature=0.8,
    n=1,
    max_tokens_per_chunk=4096,
):
    report_parts = []
    for i in range(0, len(log), chunk_size):
        chunk = log[i : i + chunk_size]

        messages = [
            {
                "role": "system",
                "content": "You are a sophisticated AI model with programming expertise. Analyze the following system logs with json format, if there are errors, please indicate when it happens. Provide a summary info less than 50 words.",
            },
            {"role": "user", "content": json.dumps(chunk)},
        ]

        tokens = len(json.dumps(chunk))
        if tokens > max_tokens_per_chunk:
            print(
                f"The {i}th chunk with {tokens} tokens exceeds max tokens per chunk {max_tokens_per_chunk}"
            )
            break

        # sleep for 25 seconds to avoid openai api limit
        if model != "gpt-4":
            if i % 2 == 0:
                time.sleep(40)

        completion = openai.ChatCompletion.create(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            n=n,
        )
        report_parts.append(completion["choices"][0]["message"]["content"].strip())

    summary_messages = [
        {
            "role": "system",
            "content": "Here are some chunks of summary info for the logs. Please review and provide a summary for the whole log less than 50 words.",
        },
        {"role": "user", "content": "\n".join(report_parts)},
    ]
    summary_completion = openai.ChatCompletion.create(
        model=model,
        messages=summary_messages,
        max_tokens=max_tokens,
        temperature=temperature,
        n=n,
    )
    # output summary log review
    final_report = summary_completion["choices"][0]["message"]["content"].strip()
    return final_report


def main():
    pod_name = "pr-review-gpt-84bd75766-wfz57"
    namespace = "gpt-assist"
    openai.api_key = os.environ["OPENAI_API_KEY"]
    logger = setup_logging()
    log = get_log(pod_name, namespace, since_seconds=3600 * 6)
    log = log_preprocess(log)
    report = get_gpt_log_review(log, chunk_size=5)
    logger.info(f"k8s log review: {report}")


if __name__ == "__main__":
    main()
