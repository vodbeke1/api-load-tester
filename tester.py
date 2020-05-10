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
        self.record = {"index": None,
                        "test_case": None,
                        "outcome": None,
                        "status_code": None,
                        "exception": None,
                        "time": None}
        self.summary = {"total": {"success": 0, "failure": 0},
                        "time": {"mean": None, "max": None, "min": None},
                        "status_code": {"none": 0},
                        "exception": {}}
        self.records = []
        self.index = 0

        self.time_count = 0
        self.time_total = 0
        self.time_max = 0
        self.time_min = 0
    
    def __str__(self):
        return str(self.counter)

    def get_record(self):
        return copy(self.record)

    def get_index(self):
        self.index += 1
        return int(self.index)
    
    def get_summary(self):
        return copy(self.summary)

    def count(self, **kwargs):
        r = self.get_record()
        r["index"] = self.get_index()
        r["test_case"] = kwargs.get("test_case")
        r["outcome"] = kwargs.get("outcome")
        r["status_code"] = kwargs.get("status_code")
        r["exception"] = kwargs.get("exception")
        r["time"] = kwargs.get("time")
        
        self.records.append(r)
        self._aggregate(r)
    
    def _aggregate(self, record):
        # total
        self.summary["total"][record["outcome"]] += 1
        # time
        if record["time"] is not None:
            self.time_count += 1
            self.time_total += record["time"]
            if record["time"] > self.time_max:
                self.time_max = record["time"]
            if record["time"] < self.time_min:
                self.time_min = record["time"]
        
        # status_code
        self.update_record(record, "status_code")
        
        # exception
        self.update_record(record, "exception")
    
    def aggregate(self):
        for r in self.records:
            self._aggregate(r)
    
    def update_record(self, record, name):
        if record[name] is not None:
            if self.summary[name].get(record[name], True):
                self.summary[name][record[name]] = 0
            self.summary[name][record[name]] += 1
        else:
            self.summary[name]["none"] += 1

    def count_time(self, counter, test, time):
        pass



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

    def record(self, **kwargs):
        self.counter.count(**kwargs)
    
    def test_request(self, test, json_):
        e = None
        status_code = None
        time_ = None
        try:
            time_ = time.time()
            r = requests.post(url=URL, json=json_, timeout=self.timeout)
            status_code = str(r.status_code)
            time_ = time.time() - time_
        except Exception as e:
            pass
        
        outcome = "failure"
        if status_code == "200":
            outcome == "success"

        self.record(test_case=test, outcome=outcome, exception=e, time=time_)
    
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
