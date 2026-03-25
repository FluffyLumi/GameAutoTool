import json
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def save_actions(actions, filename="actions.json"):
    file_path = os.path.join(BASE_DIR, filename)
    with open(file_path, "w") as f:
        json.dump(actions, f, indent=2)

def load_actions(filename="actions.json"):
    file_path = os.path.join(BASE_DIR, filename)
    with open(file_path, "r") as f:
        return json.load(f)

if __name__ == '__main__':
    print(load_actions())