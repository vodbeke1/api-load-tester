import requests
import time
import os
import json
from threading import Thread
from queue import Queue
from copy import copy
import yaml
import sys

TEST_CASE_PATH = "test_json_/"
URL = "http://127.0.0.1/api"

if os.path.exists("config.yaml"):
    with open("config.yaml") as f:
        config = yaml.load(f, Loader=yaml.FullLoader)
    URL = config.get("url") or URL
    TEST_CASE_PATH = config.get("test_case_path") or TEST_CASE_PATH


class Timer:
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, type, value, traceback):
        self.end_time = time.time()
    
    def time(self):
        return self.end_time-self.start_time



class Summary:
    def __init__(self):
        self.counter = {}
        self.record = {"index": None,
                        "test_case": None,
                        "outcome": None,
                        "status_code": None,
                        "exception": None,
                        "time": None}
        self.time_count = 0
        self.time_total = 0
        self.time_max = float("-inf")
        self.time_min = float("inf")

        self._summary = {"total": {"success": 0, "failure": 0},
                        "time": {"mean": None, "max": self.time_max, "min": self.time_min},
                        "status_code": {"none": 0},
                        "exception": {"none": 0}}
        self.records = []
        self.index = 0

        
    
    def __str__(self):
        return str(self.counter)

    def get_record(self):
        return copy(self.record)

    def get_index(self):
        self.index += 1
        return int(self.index)

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
        self._summary["total"][record["outcome"]] += 1
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
            if self._summary[name].get(record[name]) is None:
                self._summary[name][record[name]] = 0
            self._summary[name][record[name]] += 1
        else:
            self._summary[name]["none"] += 1

    def collect_summary(self):
        self._summary["time"]["max"] = self.time_max
        self._summary["time"]["min"] = self.time_min
    
    def summary(self):
        """
        Return copy of summary dict
        """
        self.collect_summary()
        return self._summary

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
        self.c = 0
        self._c = 0.1

    def __str__(self):
        return self.name

    def record(self, **kwargs):
        self.counter.count(**kwargs)
    
    def test_request(self, test, json_):
        exception = None
        status_code = None
        time_ = None
        try:
            with Timer() as t:
                r = requests.post(url=URL, json=json_, timeout=self.timeout)
                status_code = str(r.status_code)
            time_ = t.time()
        except Exception as e:
            exception = e
        
        outcome = "failure"
        if status_code == "200":
            outcome = "success"

        self.record(
            test_case=test,
            outcome=outcome,
            status_code=status_code,
            exception=exception,
            time=time_
            )

    @staticmethod
    def timer(f):
        def new_func(*args, **kwargs):
            start_time = time.time()
            f(*args, **kwargs)
            return time.time()-start_time
        return new_func
    
    def clear(self, space):
        print(space*" ", end="\r")

    def tracker(self):
        self.c += 1
        self.clear(100)
        if self.c != self.test_count:
            print(f"{self.c}/{self.test_count}"+(self.c % 5) * ".", end="\r")
        else:
            print(f"{self.c}/{self.test_count}")

    @staticmethod
    def end_msg(f):
        def new_func(*args, **kwargs):
            f(*args, **kwargs)
            print("Testing complete")
        return new_func

    def summary(self):
        print(self.counter.summary())


class SingleThreadTest(ApiTest):
    def __init__(self, test_count, name=None, **kwargs):
        super().__init__(test_count, **kwargs)
        self.name = (name or "Single_thread_test")
    
    @ApiTest.timer
    def _run(self):
        for i in range(self.test_count):
            self.tracker()
            test = (i % self.case_count) + 1
            with open(f"{self.path}test_{test}.json") as f:
                json_ = json.load(f)
            self.test_request(test=test, json_=json_)

    @ApiTest.end_msg
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
            self.tracker()
            self.test_request(test=item["test"], json_=item["json_"])
            self.q.task_done()

    @ApiTest.timer
    def _run(self):
        for _ in range(self.threads):
            t = Thread(target=self.worker)
            t.daemon = True
            t.start()
        self.q.join()

    @ApiTest.end_msg
    def run(self):
        self.prep_queue()
        self.test_time = self._run()

if __name__ == "__main__":
    single_thread_test = SingleThreadTest(test_count=2, name="my_test")
    #single_thread_test = MultiThreadTest(test_count=2000, threads=10, name="my_test")
    single_thread_test.run()
    print(single_thread_test.counter.time_max)
    single_thread_test.summary()
