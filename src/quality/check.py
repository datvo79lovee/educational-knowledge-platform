import json


FILE_PATH = "data/bronze/video_metadata_raw.jsonl"


def load_jsonl(file_path):

    records = []

    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            records.append(json.loads(line))
    
    return records


def inspect_sample(records):

    sample = records[0]

    print("Video ID:")
    print(sample["id"])

    print()

    print("Published At:")
    print(sample["snippet"]["publishedAt"])

    print()

    print("Duration:")
    print(sample["contentDetails"]["duration"])

    print()
    for record in records[:20]:
        print(record["contentDetails"]["duration"])
    print("View Count:")
    print(sample["statistics"]["viewCount"])
    value = sample["statistics"]["viewCount"]

    print(value)
    print(type(value))
    print(type(sample["snippet"]["publishedAt"]))

def main():

    records = load_jsonl(FILE_PATH)

    inspect_sample(records)

    
if __name__ == "__main__":
    main()