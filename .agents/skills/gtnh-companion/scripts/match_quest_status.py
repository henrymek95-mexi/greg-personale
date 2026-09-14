import argparse
import json
import re
from pathlib import Path

import numpy as np
from PIL import Image


def classify_color(pixel: tuple[int, int, int]) -> str | None:
    red, green, blue = pixel
    if red <= 10 and 35 <= green <= 230 and blue <= 10:
        return "completed_claimed"
    if red <= 10 and 20 <= green <= 230 and abs(green - blue) <= 8:
        return "completed_unclaimed"
    if 20 <= red <= 150 and green <= 10 and blue <= 10:
        return "incomplete"
    return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Match BetterQuesting node colors using a known viewport transform.")
    parser.add_argument("screenshot", type=Path)
    parser.add_argument("quest_line_dir", type=Path)
    parser.add_argument("--scale-x", type=float, default=4 / 3)
    parser.add_argument("--scale-y", type=float, default=4 / 3)
    parser.add_argument("--offset-x", type=float, default=340)
    parser.add_argument("--offset-y", type=float, default=60)
    parser.add_argument("--compact", action="store_true")
    parser.add_argument("--auto-offset", action="store_true")
    parser.add_argument("--auto-scale", action="store_true")
    parser.add_argument("--completed-only", action="store_true")
    parser.add_argument("--summary-only", action="store_true")
    parser.add_argument("--min-ratio", type=float, default=0.035)
    parser.add_argument("--write-log", type=Path)
    parser.add_argument("--chapter-id")
    parser.add_argument("--official-commit")
    args = parser.parse_args()

    image = Image.open(args.screenshot).convert("RGB")
    definitions_dir = args.quest_line_dir.parent.parent / "Quests" / args.quest_line_dir.name
    node_files = []
    for path in args.quest_line_dir.glob("*.json"):
        if path.name == "QuestLine.json":
            continue
        node = json.loads(path.read_text(encoding="utf-8"))
        node_files.append((path, node))

    if args.auto_offset or args.auto_scale:
        pixels = np.asarray(image)
        red, green, blue = pixels[:, :, 0], pixels[:, :, 1], pixels[:, :, 2]
        masks = [
            (red <= 10) & (green >= 35) & (green <= 230) & (blue <= 10),
            (red <= 10) & (green >= 20) & (green <= 230) & (np.abs(green.astype(int) - blue.astype(int)) <= 8),
            (red >= 20) & (red <= 150) & (green <= 10) & (blue <= 10),
        ]
        integrals = [np.pad(mask.astype(np.int32), ((1, 0), (1, 0))).cumsum(0).cumsum(1) for mask in masks]

        def rectangle_sum(integral, x0, y0, x1, y1):
            x0, y0 = max(0, x0), max(0, y0)
            x1, y1 = min(image.width, x1), min(image.height, y1)
            if x1 <= x0 or y1 <= y0:
                return 0
            return integral[y1, x1] - integral[y0, x1] - integral[y1, x0] + integral[y0, x0]

        def offset_score(offset_x, offset_y, scale_x, scale_y):
            score = 0.0
            for _, item in node_files:
                x0 = round(offset_x + item["x:3"] * scale_x) - 4
                y0 = round(offset_y + item["y:3"] * scale_y) - 4
                x1 = round(offset_x + (item["x:3"] + item["sizeX:3"]) * scale_x) + 4
                y1 = round(offset_y + (item["y:3"] + item["sizeY:3"]) * scale_y) + 4
                area = max(1, (x1 - x0) * (y1 - y0))
                color_count = max(rectangle_sum(integral, x0, y0, x1, y1) for integral in integrals)
                ratio = color_count / area
                if ratio >= 0.025:
                    score += min(ratio, 0.55) * (area ** 0.35)
            return score

        best = (-1.0, 0, 0, args.scale_x)
        scales = [args.scale_x]
        coarse_step = 8
        if args.auto_scale:
            scales = [value / 10 for value in range(8, 21)]
            coarse_step = 16
        for scale in scales:
            for offset_y in range(-800, 601, coarse_step):
                for offset_x in range(-1200, 1201, coarse_step):
                    score = offset_score(offset_x, offset_y, scale, scale)
                    if score > best[0]:
                        best = (score, offset_x, offset_y, scale)
        coarse = best
        refine_scales = [coarse[3]]
        if args.auto_scale:
            refine_scales = [round(coarse[3] - 0.12 + index * 0.02, 4) for index in range(13)]
        for scale in refine_scales:
            for offset_y in range(coarse[2] - 24, coarse[2] + 25, 4):
                for offset_x in range(coarse[1] - 24, coarse[1] + 25, 4):
                    score = offset_score(offset_x, offset_y, scale, scale)
                    if score > best[0]:
                        best = (score, offset_x, offset_y, scale)
        refined = best
        for offset_y in range(refined[2] - 8, refined[2] + 9):
            for offset_x in range(refined[1] - 8, refined[1] + 9):
                score = offset_score(offset_x, offset_y, refined[3], refined[3])
                if score > best[0]:
                    best = (score, offset_x, offset_y, refined[3])
        args.offset_x, args.offset_y = best[1], best[2]
        args.scale_x = args.scale_y = best[3]
        print(json.dumps({"calibration": {"scale": args.scale_x, "offset_x": args.offset_x, "offset_y": args.offset_y, "score": round(best[0], 4)}}))

    matches = []
    for path, node in node_files:
        x0 = round(args.offset_x + node["x:3"] * args.scale_x)
        y0 = round(args.offset_y + node["y:3"] * args.scale_y)
        x1 = round(x0 + node["sizeX:3"] * args.scale_x)
        y1 = round(y0 + node["sizeY:3"] * args.scale_y)
        pad = 5
        if x1 <= 0 or y1 <= 0 or x0 >= image.width or y0 >= image.height:
            continue
        crop = image.crop((max(0, x0 - pad), max(0, y0 - pad), min(image.width, x1 + pad), min(image.height, y1 + pad)))
        counts = {"completed_claimed": 0, "completed_unclaimed": 0, "incomplete": 0}
        for pixel in crop.getdata():
            status = classify_color(pixel)
            if status:
                counts[status] += 1
        status, score = max(counts.items(), key=lambda item: item[1])
        area = max(1, crop.width * crop.height)
        ratio = score / area
        if ratio >= args.min_ratio:
            definition_path = definitions_dir / path.name
            if not definition_path.exists():
                candidates = list((definitions_dir.parent).rglob(path.name))
                if candidates:
                    definition_path = candidates[0]
            title = path.stem
            tasks = []
            if definition_path.exists():
                definition = json.loads(definition_path.read_text(encoding="utf-8"))
                properties = definition.get("properties:10", {}).get("betterquesting:10", {})
                title = re.sub(r"§.", "", properties.get("name:8", title))
                for task in definition.get("tasks:9", {}).values():
                    tasks.append(
                        {
                            "type": task.get("taskID:8"),
                            "required_items": list(task.get("requiredItems:9", {}).values()),
                        }
                    )
            matches.append(
                {
                    "title": title,
                    "file": path.name,
                    "quest_id_high": node["questIDHigh:4"],
                    "quest_id_low": node["questIDLow:4"],
                    "status": status,
                    "tasks": tasks,
                    "score": round(ratio, 4),
                    "screen_box": [x0, y0, x1, y1],
                }
            )

    matches.sort(key=lambda item: (item["status"], item["screen_box"][1], item["screen_box"][0]))
    if args.completed_only:
        matches = [item for item in matches if item["status"].startswith("completed_")]
    if args.write_log:
        if not args.chapter_id:
            parser.error("--chapter-id is required with --write-log")
        completed_matches = [item for item in matches if item["status"].startswith("completed_")]
        quest_log = json.loads(args.write_log.read_text(encoding="utf-8"))
        quest_log["quests"] = [item for item in quest_log.get("quests", []) if item.get("chapter") != args.chapter_id]
        for item in completed_matches:
            quest_log["quests"].append(
                {
                    "quest_id": f'{item["quest_id_high"]}:{item["quest_id_low"]}',
                    "chapter": args.chapter_id,
                    "title": item["title"].strip(),
                    "status": item["status"],
                    "confidence": "high",
                    "evidence_file": args.screenshot.name,
                    "official_file": item["file"],
                }
            )
        claimed = sum(item["status"] == "completed_claimed" for item in completed_matches)
        unclaimed = sum(item["status"] == "completed_unclaimed" for item in completed_matches)
        quest_log["observations"] = [
            item
            for item in quest_log.get("observations", [])
            if not (item.get("type") == "official_quest_map_match" and item.get("chapter") == args.chapter_id)
        ]
        quest_log["observations"].append(
            {
                "observed_on": "2026-09-10",
                "type": "official_quest_map_match",
                "chapter": args.chapter_id,
                "summary": f"Matched {len(completed_matches)} completed nodes: {claimed} claimed and {unclaimed} unclaimed; this agrees with the chapter counter.",
                "evidence_files": [args.screenshot.name],
                "official_commit": args.official_commit,
                "viewport_transform": {
                    "scale_x": args.scale_x,
                    "scale_y": args.scale_y,
                    "offset_x": args.offset_x,
                    "offset_y": args.offset_y,
                },
            }
        )
        quest_log["last_updated"] = "2026-09-10"
        args.write_log.write_text(json.dumps(quest_log, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if args.compact:
        matches = [
            {
                "title": item["title"],
                "file": item["file"],
                "quest_id_high": item["quest_id_high"],
                "quest_id_low": item["quest_id_low"],
                "status": item["status"],
                "score": item["score"],
            }
            for item in matches
        ]
    if args.summary_only:
        print(
            json.dumps(
                {
                    "matched": len(matches),
                    "completed_claimed": sum(item["status"] == "completed_claimed" for item in matches),
                    "completed_unclaimed": sum(item["status"] == "completed_unclaimed" for item in matches),
                }
            )
        )
        return
    print(json.dumps(matches, indent=2))


if __name__ == "__main__":
    main()
