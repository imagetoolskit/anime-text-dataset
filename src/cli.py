import sys

COMMANDS = (
    "discover", "dedup", "backfill", "refill", "enrich", "entities", "normalize",
    "relationships", "descriptions", "qa", "instructions", "franchise", "rag",
    "validate", "split", "export", "checksums", "report",
)

HELP = (
    "usage: python -m src.cli <command> [options]\n"
    "commands: " + " | ".join(COMMANDS) + "\n"
    "Full reference: docs/COMMANDS.md\n"
    "License tiers are assigned by scripts/license_tiers.py before export."
)


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        print(HELP)
        return 2
    if argv[0] in ("-h", "--help", "help"):
        print(HELP)
        return 0
    cmd = argv[0]
    if cmd == "discover":
        from .pipeline.discover import main as run
        return run(argv)
    if cmd == "dedup":
        from .pipeline.dedup import run as run
        return run()
    if cmd == "backfill":
        from .pipeline.backfill import run as run
        return run()
    if cmd == "refill":
        from .pipeline.refill import main as run
        return run(argv)
    if cmd == "enrich":
        from .pipeline.enrich import main as run
        return run(argv)
    if cmd == "entities":
        from .pipeline.entities import run as run
        return run()
    if cmd == "normalize":
        from .pipeline.normalize import run as run
        return run()
    if cmd == "relationships":
        from .pipeline.relationships import run as run
        return run()
    if cmd == "descriptions":
        from .pipeline.descriptions import run as run
        return run()
    if cmd == "qa":
        from .pipeline.qa import run as run
        return run()
    if cmd == "instructions":
        from .pipeline.instructions import run as run
        return run()
    if cmd == "franchise":
        from .pipeline.franchise import run as run
        return run()
    if cmd == "rag":
        from .pipeline.rag import run as run
        return run()
    if cmd == "validate":
        from .validate.validators import main as run
        return run(argv)
    if cmd == "split":
        from .pipeline.split import run as run
        return run()
    if cmd == "export":
        from .pipeline.export import main as run
        return run(argv)
    if cmd == "checksums":
        from .pipeline.checksums import run as run
        return run()
    if cmd == "report":
        from .validate.report import run as run
        return run()
    print(f"unknown command: {cmd}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
