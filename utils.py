import requests
import gzip
import json

def get_and_decompress(link):
    headers = {"User-Agent": "MTG Query 0.1"}

    # Fetch download link, then download the actual data
    r = requests.get(link, headers=headers)
    r = requests.get(r.json()["jsonl_download_uri"], headers=headers)

    # Decompress and decode
    content = gzip.decompress(r.content).decode()

    # Convert from JSON Lines to List of JSON
    return [json.loads(line) for line in content.split("\n")[:-1]]


def load_json_file(filename):
    with open(filename, "r") as f:
        return json.load(f)


def save_json_file(obj, filename):
    with open(filename, "w") as f:
        json.dump(obj, f)


def flatten_list(x):
    found_list = True
    while found_list:
        found_list = False
        flat = []
        for item in x:
            if type(item) == list:
                flat.extend(item)
                found_list = True
            else:
                flat.append(item)
        x = flat
    return x
