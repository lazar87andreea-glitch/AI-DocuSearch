import argparse
import json
from src.pipeline import build_pipeline, answer_question


def main():
    parser = argparse.ArgumentParser(description="Demo Document Processing Agent")
    parser.add_argument("file", help="Path to PDF or DOCX file")
    parser.add_argument("question", help="Question to ask the document")
    args = parser.parse_args()
    pipeline = build_pipeline(args.file)
    result = answer_question(pipeline, args.question)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
