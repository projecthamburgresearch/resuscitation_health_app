import argparse
import json
import sys
from typing import Any, Dict, List


def load_json(file_path: str) -> Dict[str, Any]:
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: file not found: {file_path}")
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"Error: invalid JSON: {file_path}")
        sys.exit(1)


def dump(payload: Any) -> None:
    print(json.dumps(payload, indent=2, ensure_ascii=True))


def cmd_element(args: argparse.Namespace) -> None:
    data = load_json(args.scan_file)
    elements = data.get("elements", [])
    matches: List[Dict[str, Any]] = []

    for el in elements:
        label = str(el.get("label", ""))
        tag = str(el.get("tag", "")).lower()
        element_id = str(el.get("id", ""))

        if args.label and label != args.label:
            continue
        if args.contains and args.contains.lower() not in label.lower():
            continue
        if args.tag and tag != args.tag.lower():
            continue
        if args.element_id and element_id != args.element_id:
            continue

        matches.append(
            {
                "index": el.get("index"),
                "sourceIndex": el.get("sourceIndex"),
                "id": el.get("id"),
                "label": el.get("label"),
                "tag": el.get("tag"),
                "box": el.get("box"),
                "geometry": el.get("geometry"),
                "typography": el.get("typography"),
                "colorPhysics": el.get("colorPhysics"),
            }
        )

    if args.limit is not None:
        matches = matches[: args.limit]

    if not matches:
        print("Error: no matching element found")
        sys.exit(1)

    if args.first:
        dump(matches[0])
    else:
        dump({"count": len(matches), "matches": matches})


def transition_matches(shot: Dict[str, Any], args: argparse.Namespace) -> bool:
    if shot.get("category") != "dynamic":
        return False

    stage = str(shot.get("transitionStage", "")).lower()
    if args.stage != "both" and stage != args.stage:
        return False

    transition = shot.get("transition") or {}
    slug = str(transition.get("slug", ""))
    from_id = str(transition.get("fromId", ""))
    to_id = str(transition.get("toId", ""))

    if args.transition_slug and slug != args.transition_slug:
        return False
    if args.contains and args.contains.lower() not in slug.lower():
        return False

    if args.card_id:
        card_id = args.card_id
        before = ((shot.get("beforeSnapshot") or {}).get("currentId"))
        after = ((shot.get("afterSnapshot") or {}).get("currentId"))
        values = {from_id, to_id, str(before or ""), str(after or "")}
        if card_id not in values:
            return False

    return True


def cmd_transition(args: argparse.Namespace) -> None:
    data = load_json(args.bundle_file)
    screenshots = data.get("screenshots", [])

    matches = [shot for shot in screenshots if transition_matches(shot, args)]

    if args.limit is not None:
        matches = matches[: args.limit]

    if not matches:
        print("Error: no matching dynamic transitions found")
        sys.exit(1)

    compact = []
    for shot in matches:
        transition = shot.get("transition") or {}
        compact.append(
            {
                "transitionIndex": shot.get("transitionIndex"),
                "transitionStage": shot.get("transitionStage"),
                "viewport": shot.get("viewport"),
                "transition": {
                    "slug": transition.get("slug"),
                    "fromId": transition.get("fromId"),
                    "toId": transition.get("toId"),
                    "type": transition.get("type"),
                    "optionIndex": transition.get("optionIndex"),
                    "optionLabel": transition.get("optionLabel"),
                },
                "beforeCurrentId": ((shot.get("beforeSnapshot") or {}).get("currentId")),
                "afterCurrentId": ((shot.get("afterSnapshot") or {}).get("currentId")),
                "file": shot.get("file"),
                "splitMap": ((shot.get("split") or {}).get("mapFile")),
                "ok": shot.get("ok"),
                "error": shot.get("error"),
            }
        )

    dump({"count": len(compact), "matches": compact})


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Query scan telemetry and dynamic transition bundle artifacts."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    element = sub.add_parser("element", help="Query scan elements")
    element.add_argument("scan_file", type=str, help="Path to scan JSON")
    element.add_argument("--label", type=str, help="Exact label match")
    element.add_argument("--contains", type=str, help="Case-insensitive label contains")
    element.add_argument("--tag", type=str, help="Exact tag match")
    element.add_argument("--element-id", type=str, help="Exact id match")
    element.add_argument("--first", action="store_true", help="Return only first match")
    element.add_argument("--limit", type=int, help="Limit number of matches")
    element.set_defaults(func=cmd_element)

    transition = sub.add_parser("transition", help="Query dynamic transition screenshots")
    transition.add_argument("bundle_file", type=str, help="Path to bundle_manifest.json")
    transition.add_argument(
        "--stage",
        type=str,
        default="both",
        choices=["before", "after", "both"],
        help="Filter by transition stage",
    )
    transition.add_argument("--transition-slug", type=str, help="Exact transition slug match")
    transition.add_argument("--contains", type=str, help="Case-insensitive slug contains")
    transition.add_argument("--card-id", type=str, help="Match from/to/current card id")
    transition.add_argument("--limit", type=int, help="Limit number of matches")
    transition.set_defaults(func=cmd_transition)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
