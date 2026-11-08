"""Local scout tooling: public dataset reads, offline reports, and approved JSON batches."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import httpx

from opportunities.config.rules import load_classification_rules
from opportunities.config.settings import Settings
from opportunities.manual_jobs import unique_json_object
from opportunities.pipeline.classification import Classifier
from opportunities.scout import ApprovalError, Research, assess, prepare_batches, render_report
from opportunities.scout_dataset import PublicDataset, PublicDatasetError, load_public_dataset
from opportunities.utils.paths import find_project_root
from opportunities.utils.time import utc_now

ROOT = find_project_root(Path(__file__))


def read_json(path: Path) -> object:
    """Bound local research inputs and reject duplicate keys."""
    with path.open("rb") as source:
        content = source.read(8 * 1024 * 1024 + 1)
    if len(content) > 8 * 1024 * 1024:
        raise ValueError("research input exceeds 8 MiB")
    return json.loads(content.decode("utf-8"), object_pairs_hook=unique_json_object)


def write_new(path: Path, content: str | bytes) -> None:
    """Refuse to overwrite earlier research or batch artifacts."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as output:
        output.write(content.encode("utf-8") if isinstance(content, str) else content)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("dataset", "report", "batches"))
    parser.add_argument(
        "--directory", type=Path, required=True, help="Ignored research run directory."
    )
    parser.add_argument(
        "--export", action="store_true", help="Use hash-checked public JSON fallback."
    )
    parser.add_argument(
        "--without-dataset", action="store_true", help="Report unknown novelty explicitly."
    )
    parser.add_argument(
        "--approved-ids", help="Comma-separated IDs explicitly approved by the user."
    )
    args = parser.parse_args(argv)
    if (
        (args.export and args.command != "dataset")
        or (args.without_dataset and args.command != "report")
        or (args.approved_ids is not None and args.command != "batches")
    ):
        return _fail(
            "[invalid_options] Use --export only with dataset, --without-dataset only with "
            "report, and --approved-ids only with batches."
        )
    if args.command == "batches" and args.approved_ids is None:
        return _fail(
            "[approval_required] Supply explicitly approved IDs; no dispatch is authorized."
        )
    directory: Path = args.directory
    dataset: PublicDataset | None
    try:
        output_name = {"dataset": "dataset.json", "report": "report.md"}.get(args.command)
        if output_name is not None:
            output_path = directory / output_name
            if output_path.exists() or output_path.is_symlink():
                raise FileExistsError("output already exists")
        if args.command == "dataset":
            with httpx.Client(timeout=20, trust_env=False, follow_redirects=False) as client:
                dataset = load_public_dataset(client, use_export=args.export)
            write_new(directory / "dataset.json", dataset.model_dump_json(indent=2) + "\n")
        else:
            research = Research.model_validate(read_json(directory / "research.json"))
            dataset = (
                None
                if args.without_dataset
                else PublicDataset.model_validate(read_json(directory / "dataset.json"))
            )
            classifier = Classifier(
                load_classification_rules(ROOT / "configs/categories.yml"), Settings().target_cycle
            )
            if args.command == "report":
                findings = assess(research, dataset, classifier)
                write_new(directory / "report.md", render_report(research, dataset, findings))
            else:
                approved = args.approved_ids.split(",") if args.approved_ids else []
                batches, skipped = prepare_batches(
                    research, dataset, approved, classifier=classifier, observed_at=utc_now()
                )
                # Validate all bytes and check existing destinations before writing the first batch.
                outputs = {
                    directory / f"batch-{index:02}.json": content
                    for index, content in enumerate(batches, 1)
                }
                if any(path.exists() or path.is_symlink() for path in outputs):
                    raise FileExistsError("batch output already exists")
                for path, content in outputs.items():
                    write_new(path, content)
                sys.stdout.write(json.dumps({"batches": len(batches), "skipped": skipped}) + "\n")
        return 0
    except ApprovalError:
        return _fail(
            "[invalid_approval] Select unique candidate IDs from this ledger that are not "
            "already in the published dataset."
        )
    except PublicDatasetError as exc:
        message = {
            "dataset_changed": "[dataset_changed] Preserve evidence; wait and retry at most once.",
            "export_required": "[export_required] Use dataset --export for a hash-checked read.",
            "http_429": "[http_429] Stop requests; respect the rate limit before a later attempt.",
        }.get(exc.code, "[invalid_public_data] Complete public data could not be verified.")
        return _fail(message)
    except httpx.TimeoutException:
        return _fail("[public_timeout] Public read timed out; no complete dataset saved.")
    except FileExistsError:
        return _fail("[output_exists] Preserve outputs and choose a new run directory.")
    except (OSError, ValueError, RecursionError, OverflowError, httpx.HTTPError):
        return _fail("[invalid_input_or_data] Check local inputs, public data, and output access.")


def _fail(message: str) -> int:
    # Only fixed messages reach this sink, never exception text or response contents.
    sys.stderr.write(f"Scout operation failed: {message} No canonical state accessed.\n")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
