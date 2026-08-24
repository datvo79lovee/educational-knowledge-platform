"""Developer guidance for the canonical API entrypoint."""


def main() -> None:
    """Point direct module execution to the documented Uvicorn command."""

    print(
        "Run the API with: python -m uvicorn src.search_api.app:app "
        "--host 127.0.0.1 --port 8000"
    )


if __name__ == "__main__":
    main()
