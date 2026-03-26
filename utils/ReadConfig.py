import json
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def save_actions(actions, filename="actions.json"):
    file_path = os.path.join(BASE_DIR, filename)
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(actions, f, indent=2, ensure_ascii=False)


def load_actions(filename="actions.json"):
    file_path = os.path.join(BASE_DIR, filename)
    if not os.path.exists(file_path):
        return []
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


if __name__ == "__main__":
    print(load_actions())
