import json
import os
import openai
import logging
import time
from kubernetes import config, client


# The JsonFormatter class formats log records into JSON format
class JsonFormatter(logging.Formatter):
    # The format method takes a log record and returns it as a JSON formatted string.
    def format(self, record):
        log_entry = {
            "asctime": self.formatTime(record, self.datefmt),
            "levelname": record.levelname,
            "message": record.getMessage(),
        }
        return json.dumps(log_entry)


class KubernetesLogAnalyzer:
    # The __init__ method initializes an instance of KubernetesLogAnalyzer.
    def __init__(
        self,
        namespaces=None,
        error_strings=[],
        model="gpt-4",
        chunk_size=20,
        max_tokens=100,
        temperature=0.8,
        n=1,
        max_tokens_per_chunk=4096,
        since_seconds=3600 * 24,
        is_in_cluster=True,
    ):
        self.namespaces = namespaces
        self.error_strings = error_strings
        self.model = model
        self.chunk_size = chunk_size
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.n = n
        self.max_tokens_per_chunk = max_tokens_per_chunk
        self.logger = self.setup_logging()
        self.since_seconds = since_seconds
        self.is_in_cluster = is_in_cluster

        if self.is_in_cluster:
            config.load_incluster_config()  # load kube config from service account
        else:
            config.load_kube_config()  # load kube config from ~/.kube/config

        self.v1 = client.CoreV1Api()

        assert (
            "OPENAI_API_KEY" in os.environ
        ), "OPENAI_API_KEY not found in environment variables"
        openai.api_key = os.environ["OPENAI_API_KEY"]

    # The setup_logging method sets up the configuration for the logger.
    def setup_logging(self):
        logger = logging.getLogger()
        logger.setLevel(logging.INFO)

        logHandler = logging.StreamHandler()
        formatter = JsonFormatter()
        logHandler.setFormatter(formatter)
        logger.addHandler(logHandler)
        return logger

    # The get_pod_names method retrieves the names of all pods in a given namespace.
    def get_pod_names(self, namespace):
        try:
            pods = self.v1.list_namespaced_pod(namespace)
            return pods
        except Exception as e:
            self.logger.error(f"Failed to get pod names: {e}")
            raise

    # The get_log method retrieves the log of a specified pod.
    def get_log(self, pod_name, namespace, container_name):
        log = self.v1.read_namespaced_pod_log(
            name=pod_name,
            namespace=namespace,
            since_seconds=self.since_seconds,
            container=container_name,
        )
        return log

    # The filter_flask_logs method filters out the logs of the Flask application.
    # (assume all other logs are in json format)
    def filter_flask_logs(self, logs):
        filtered_logs = []
        for log in logs.split("\n"):
            try:
                json.loads(log)
                filtered_logs.append(log)
            except json.JSONDecodeError:
                continue
        return filtered_logs

    # The filter_http_error_logs method filters out logs containing specified error strings
    # and returns the count of errors and the filtered logs.
    def filter_http_error_logs(self, log_lines):
        error_count = 0
        filtered_logs = []
        for log in log_lines:
            log_json = json.loads(log)
            if any(
                error_str in log_json["message"] for error_str in self.error_strings
            ):
                error_count += 1
            else:
                filtered_logs.append(log)
        return error_count, filtered_logs

    # The get_openai_completion method uses the GPT model from OpenAI to analyze the logs and returns an analysis report.
    def get_openai_completion(self, messages):
        try:
            completion = openai.ChatCompletion.create(
                model=self.model,
                messages=messages,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                n=self.n,
            )
            return completion
        except openai.error.OpenAIError as e:
            self.logger.error(f"Failed to get openai completion: {e}")
            raise

    # The get_pr_log_review method uses the GPT model from OpenAI to analyze the logs and returns an analysis report.
    def get_log_review(self, log):
        report_parts = []
        for i in range(0, len(log), self.chunk_size):
            chunk = log[i : i + self.chunk_size]

            messages = [
                {
                    "role": "system",
                    "content": "You are a sophisticated AI model with programming expertise. Analyze the following system logs with json format, if there are errors, please indicate when it happens. Provide a summary info less than 200 words.",
                },
                {"role": "user", "content": json.dumps(chunk)},
            ]

            tokens = len(json.dumps(chunk))
            if tokens > self.max_tokens_per_chunk:
                print(
                    f"The {i}th chunk with {tokens} tokens exceeds max tokens per chunk {self.max_tokens_per_chunk}"
                )
                break

            # sleep for 40 seconds to avoid openai api limit
            if self.model != "gpt-4":
                if i % 2 == 0:
                    time.sleep(40)
            try:
                completion = self.get_openai_completion(messages)
                report_parts.append(
                    completion["choices"][0]["message"]["content"].strip()
                )
            except openai.error.OpenAIError as e:
                self.logger.error(f"Failed to get chunked log review: {e}")
                raise

        summary_messages = [
            {
                "role": "system",
                "content": "Here are some chunks of summary info for the logs. Please review and provide a summary for the whole log less than 200 words.",
            },
            {"role": "user", "content": "\n".join(report_parts)},
        ]
        try:
            summary_completion = self.get_openai_completion(summary_messages)
            # output summary log review
            final_report = summary_completion["choices"][0]["message"][
                "content"
            ].strip()
        except openai.error.OpenAIError as e:
            self.logger.error(f"Failed to get final log review: {e}")
            return None
        return final_report

    # The analyze method is responsible for collecting, filtering, analyzing logs, and logging the results.
    def analyze_pr_review_logs(self):
        log = ""

        # get all namespaces in the cluster if namespaces is not specified
        if self.namespaces is None:
            self.namespaces = [
                ns.metadata.name for ns in self.v1.list_namespace().items
            ]

        for namespace in self.namespaces:
            pods = self.get_pod_names(namespace=namespace)
            if len(pods.items) == 0:
                self.logger.info(f"No pods found in namespace {namespace}")
                continue
            for pod in pods.items:
                for container in pod.spec.containers:
                    log += self.get_log(
                        pod_name=pod.metadata.name,
                        namespace=namespace,
                        container_name=container.name,
                    )

        log = self.filter_flask_logs(log)
        error_count, log = self.filter_http_error_logs(log)

        report = self.get_log_review(log)

        self.logger.info(
            f"{error_count} lines of log with http bad request were removed, k8s log review: {report}."
        )


def main():
    namespaces = ["gpt-assist"]

    error_strings = [
        "code 400",
        "HTTPStatus.BAD_REQUEST",
        "404 -",
    ]
    analyzer = KubernetesLogAnalyzer(
        namespaces=namespaces,
        error_strings=error_strings,
        model="gpt-4",
        chunk_size=100,
    )

    analyzer.analyze_pr_review_logs()


if __name__ == "__main__":
    main()
