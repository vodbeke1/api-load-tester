import requests
import time
import os
import json
from threading import Thread
from queue import Queue
from copy import copy

TEST_CASE_PATH = "test_json/"
URL = "http://127.0.0.1/api"

class Summary:
    SCENARIOS = (
        "status_code",
        "timeout",
        "total"
    )
    def __init__(self):
        self.counter = {}
        self.skeleton = {}
    
        for s in self.SCENARIOS:
            self.counter[s] = {}
            self.counter[s]["total"] = {}
            self.counter[s]["test_cases"] = {}

        self.counter["timeout"]["total"] = 0
        self.counter["total"]["success"] = 0
        self.counter["total"]["failure"] = 0
    
    def __str__(self):
        return str(self.counter)
    
    def count(self, test, response, exception):
        if self.counter["test_cases"].get(test, True):
            self.counter["test_cases"][test] = copy(self.skeleton)

        for c in (self.counter["summary"], self.counter["test_cases"][test]):
            if response is not None:
                status_code = str(response.status_code)
                self.count_status_code(c, status_code)
            elif exception is not None:
                self.count_exception(c, exception)
            else:
                raise Exception("Either 'response' or 'exception' needs to be not None")
    
    def count_total(self, type, count_type):
        self.counter[count_type]["total"][type] += 1
    
    def count_status_code(self, collector, status_code):
        if str(status_code) == "200":
            self.count_total("success")
        else:
            self.count_total("failure")
        
        if self.counter["summary"]["status_code"].get(str(status_code), True):
            self.counter["summary"]["status_code"][str(status_code)] = 1
        else:
            self.counter["summary"]["status_code"][str(status_code)] += 1
    
    def count_exception(self, collector, exception):
        self.count_total("failure")
        if collector["status_code"].get(str(exception), True):
            collector["status_code"][str(exception)] = 1
        else:
            collector[count_type]["status_code"][str(exception)] += 1


class ApiTest:
    def __init__(self, test_count, timeout=10, path=TEST_CASE_PATH):
        self.counter = Summary()
        self.timeout = timeout
        self.path = path
        self.test_cases = os.listdir(path)
        self.case_count = len(self.test_cases)
        self.test_time = None
        self.name = "test"
        self.test_count = test_count

    def __str__(self):
        return self.name

    def record(self, test, response=None, exception=None):
        self.counter.count(response, exception)
    
    def test_request(self, test, json_):
        try:
            r = requests.post(url=URL, json=json_, timeout=self.timeout)
            self.record(test, response=r)
        except Exception as e:
            self.record(test, exception=e)
    
    @staticmethod
    def timer(f):
        def new_func(*args, **kwargs):
            start_time = time.time()
            f(*args, **kwargs)
            return time.time()-start_time
        return new_func


class SingleThreadTest(ApiTest):
    def __init__(self, test_count, name=None, **kwargs):
        super().__init__(test_count, **kwargs)
        self.name = (name or "Single_thread_test")
    
    @ApiTest.timer
    def _run(self):
        for i in range(self.test_count):
            test = (i % self.case_count) + 1
            with open(f"{self.path}test_{test}.json") as f:
                json_ = json.load(f)
            self.test_request(test=test, json_=json_)
    
    def run(self):
        self.test_time = self._run()

class MultiThreadTest(ApiTest):
    def __init__(self, test_count, threads, name=None,**kwargs):
        super().__init__(test_count, **kwargs)
        self.q = Queue()
        self.threads = threads
        self.name = (name or "Multi_thread_test")
    
    def prep_queue(self):
        for i in range(self.test_count):
            test = (i % self.case_count) + 1
            item = {}
            item["test"] = test
            with open(f"{self.path}test_{test}.json") as f:
                item["json_"] = json.load(f)
            
            self.q.put(item)
    
    def worker(self):
        while True:
            item = self.q.get()
            self.test_request(test=item["test"], json_=item["json_"])
            self.q.task_done()

    @ApiTest.timer
    def _run(self):
        for _ in range(self.threads):
            t = Thread(target=self.worker)
            t.daemon = True
            t.start()
        self.q.join()

    def run(self):
        self.prep_queue()
        self.test_time = self._run()
