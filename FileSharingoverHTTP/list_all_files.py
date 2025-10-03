import os

def list_all_files(base_dir):
    result = []
    for root, dirs, files in os.walk(base_dir):
        for file in files:
            abs_path = os.path.abspath(os.path.join(root, file))
            result.append(abs_path)
    return result

if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    all_files = list_all_files(script_dir)
    txt_path = os.path.join(script_dir, "all_files.txt")
    with open(txt_path, "w", encoding="utf-8") as f:
        for path in all_files:
            f.write(path + "\n")
