import csv


with open("error-codes.csv", "r") as f:
    reader = csv.DictReader(f, skipinitialspace=True)
    codes = [
        {
            "start_range": int(row["start_range"], base=16),
            "end_range": int(row["end_range"], base=16),
            "name": row["name"].strip(),
        }
        for row in reader
    ]

def intersects(a, b):
    return a["start_range"] <= b["end_range"] and a["end_range"] >= b["start_range"]

if __name__ == "__main__":
    for code in codes:
        if code["start_range"] > code["end_range"]:
            print(f"invalid range: \"{code['name']}\" has start greater than end")
            exit(1)

    for (idx, code) in enumerate(codes):
        for other in codes[:idx]:
            if intersects(code, other):
                print(f"overlapping ranges: \"{code['name']}\" intersects with \"{other['name']}\"")
                exit(1)

    print("no errors found")