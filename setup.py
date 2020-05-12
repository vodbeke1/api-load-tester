import os

DIR = (
    "log/",
    "test_json/"
)

for d in DIR:
    if not os.path.exists(d):
        os.makedirs(d)
