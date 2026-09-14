import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def main() -> None:
    parser = argparse.ArgumentParser(description="Render a labeled BetterQuesting quest-line layout.")
    parser.add_argument("quest_line_dir", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--scale", type=float, default=2.0)
    args = parser.parse_args()

    nodes = []
    for path in args.quest_line_dir.glob("*.json"):
        if path.name == "QuestLine.json":
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        nodes.append(
            {
                "name": path.name.split("-")[0],
                "x": data["x:3"],
                "y": data["y:3"],
                "w": data["sizeX:3"],
                "h": data["sizeY:3"],
            }
        )

    max_x = max(node["x"] + node["w"] for node in nodes) + 30
    max_y = max(node["y"] + node["h"] for node in nodes) + 30
    image = Image.new("RGB", (int(max_x * args.scale), int(max_y * args.scale)), "#f7f0d7")
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default(size=max(10, int(10 * args.scale)))

    for node in nodes:
        x0 = int(node["x"] * args.scale)
        y0 = int(node["y"] * args.scale)
        x1 = int((node["x"] + node["w"]) * args.scale)
        y1 = int((node["y"] + node["h"]) * args.scale)
        draw.rectangle((x0, y0, x1, y1), outline="#263238", width=max(2, int(args.scale)))
        label = node["name"][:18]
        draw.text((x0 + 3, y0 + 3), label, fill="#111820", font=font)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    image.save(args.output)


if __name__ == "__main__":
    main()
