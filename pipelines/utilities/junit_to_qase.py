#!/usr/bin/python
import os
import sys
from urllib.parse import urlencode
from datetime import date
import requests
from bs4 import BeautifulSoup


def collect_test_results(test_cases):

    test_results = []

    for test_case in test_cases:

        test_result = {
            "case": "",
            "case_id": "",
            "suite": "",
            "suite_id": "",
            "skipped": "",
            "failure": ""
        }

        test_suite = test_case.get("classname")
        test_result['suite'] = test_suite.split(".")[-1]

        test_result['case'] = test_case.get("name").split("[")[0]

        skipped = test_case.findChildren("skipped", recursive=False)
        if len(skipped) > 0:
            test_result['skipped'] = skipped[0].get("message")

        failure = test_case.findChildren("failure", recursive=False)
        if len(failure) > 0:
            test_result['failure'] = failure[0].get("message")
            test_result['failure'] += '\n\n' + failure[0].get_text()

        test_results.append(test_result)

    return test_results


def get_suite_id(suite_name):

    print(f"getting suite {suite_name}")

    query_string = urlencode({ "search": suite_name })
    headers = {
        "accept": "application/json",
        "Token": qase_token
    }
    url = f"https://api.qase.io/v1/suite/{qase_project}?{query_string}"

    resp = requests.get(url, headers=headers)
    res = resp.json()
    if res["result"]["count"] > 0:
        id = res["result"]["entities"][0]["id"]
        print(f"got suite {suite_name} with id {id}")
        return id
    else:
        print(f"missed suite {suite_name}")
        return None


def add_missing_suite(suite_name):

    print(f"adding missing suite {suite_name}")

    payload = {
        "title": suite_name,
        "parent_id": parent_suite_id
    }
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "Token": qase_token
    }
    url = f"https://api.qase.io/v1/suite/{qase_project}"

    resp = requests.post(url, json=payload, headers=headers)
    res = resp.json()
    print(f"added suite {suite_name} with id {res['result']['id']}")
    return res["result"]["id"]


def get_suites_id_and_add_missing_suites(test_results):
    for result in test_results:
        result["suite_id"] = get_suite_id(result["suite"])
        if not result["suite_id"]:
            result["suite_id"] = add_missing_suite(result["suite"])


def get_case_id(case_name):

    print(f"getting case {case_name}")

    query_string = urlencode({ "search": case_name })
    headers = {
        "accept": "application/json",
        "Token": qase_token
    }
    url = f"https://api.qase.io/v1/case/{qase_project}?{query_string}"

    resp = requests.get(url, headers=headers)
    res = resp.json()
    if res["result"]["count"] > 0:
        id = res["result"]["entities"][0]["id"]
        print(f"got case {case_name} with id {id}")
        return id
    else:
        print(f"missed case {case_name}")
        return None


def add_missing_case(case_name, parent_suite_id):

    print(f"adding missing case {case_name} under parent suite {parent_suite_id}")

    if len(case_name) > 128:
        case_name = case_name[:127]

    payload = {
        "title": case_name,
        "suite_id": parent_suite_id,
        "automation": 2
    }
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "Token": qase_token
    }
    url = f"https://api.qase.io/v1/case/{qase_project}"

    resp = requests.post(url, json=payload, headers=headers)
    res = resp.json()
    print(f"added case {case_name} with id {res['result']['id']}")
    return res["result"]["id"]


def get_test_cases_id_and_add_missing_test_cases(test_results):
    for result in test_results:
        result["case_id"] = get_case_id(result["case"])
        if not result["case_id"]:
            result["case_id"] = add_missing_case(result["case"], result["suite_id"])


def create_test_run(job_name, test_results):

    test_cases_id = []
    for result in test_results:
        test_cases_id.append(result["case_id"])

    payload = {
        "cases": test_cases_id,
        "title": job_name
    }
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "Token": qase_token
    }
    url = f"https://api.qase.io/v1/run/{qase_project}"

    resp = requests.post(url, json=payload, headers=headers)
    res = resp.json()
    return res["result"]["id"]


def update_test_run_results(test_run_id, test_results):

    print(f"updating test run {test_run_id} results")

    arr = []
    for test_result in test_results:
        obj = {}
        obj["case_id"] = test_result["case_id"]
        if test_result["skipped"]:
            obj["comment"] = test_result["skipped"]
            obj["status"] = "skipped"
        elif test_result["failure"]:
            obj["stacktrace"] = test_result["failure"]
            obj["status"] = "failed"
        else:
            obj["status"] = "passed"
        arr.append(obj)

    payload = { "results": arr }
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "Token": qase_token
    }
    url = f"https://api.qase.io/v1/result/{qase_project}/{test_run_id}/bulk"

    resp = requests.post(url, json=payload, headers=headers)
    res = resp.json()
    if res["status"] == True:
        print(f"updating test run {test_run_id} succeeded")
    else:
        print(f"failed to update test run {test_run_id}: {res}")


def complete_test_run(test_run_id):

    print(f"completing test run {test_run_id}")

    headers = {
        "accept": "application/json",
        "Token": qase_token
    }
    url = f"https://api.qase.io/v1/run/{qase_project}/{test_run_id}/complete"

    resp = requests.post(url, headers=headers)
    res = resp.json()
    if res["status"] == True:
        print(f"completing test run {test_run_id} succeeded")
    else:
        print(f"failed to complete test run {test_run_id}: {res}")


# collect required global variables
qase_token = os.getenv("QASE_TOKEN", "")
qase_project = os.getenv("QASE_PROJECT", "LH")
parent_suite_id = ""

if __name__ == "__main__":

    if len(sys.argv) <= 1:
        raise Exception("Report filename not provided")
    else:
        report_filename = sys.argv[1]

    with open(report_filename, 'r') as f:
        file = f.read()
        soup = BeautifulSoup(file, 'lxml-xml')

    # decide it's a pytest or robot report
    test_suites = soup.find_all("testsuite")
    if test_suites[0].get("name") == "pytest":
        test_type = "pytest"
        # if it's a pytest report, missing suites will be added under
        # parent suite e2e-pytest (id=58)
        parent_suite_id = 58 # e2e-pytest
    else:
        test_type = "robot"
        # TODO
        # the folder structure of robot test hasn't been
        # well-defined in qase
        parent_suite_id = None
        raise Exception(f"Unsupported test_type = {test_type}")
    print(f"test_type = {test_type}")

    # collect test results dict from test cases xml
    test_cases = soup.find_all("testcase")
    test_results = collect_test_results(test_cases)

    # get suites id and add missing suites
    get_suites_id_and_add_missing_suites(test_results)

    # get test cases id and add missing test cases
    get_test_cases_id_and_add_missing_test_cases(test_results)

    # create test run
    today = date.today()
    job_name = f"{os.getenv('JOB_NAME', 'longhorn-regression-test')}-{today}"
    test_run_id = create_test_run(job_name, test_results)
    print(f"test_run_id = {test_run_id}")

    # update test results to test run
    update_test_run_results(test_run_id, test_results)

    # complete test run
    complete_test_run(test_run_id)
