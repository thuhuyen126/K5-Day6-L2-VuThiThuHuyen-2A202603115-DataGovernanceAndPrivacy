
from pathlib import Path

import pandas as pd

from src.common.context import RunContext
from src.pipeline import load, process


root = Path("fixtures/t02_raw_qc")

ctx = RunContext(
    track="t02",
    input_dir=root,
    output_dir=Path("out/process_check"),
    config={
        "params": {
            "budget": 20,
            "dev_split": "dev",
            "min_group_size": 10,
        }
    },
    seed=42,
    rng=__import__("numpy").random.default_rng(42),
)

print("===== LOAD =====")
data = load(ctx)
print("Loaded images:", len(data["images"]))

print("\n===== PROCESS =====")
scored = process(ctx, data)

print("Processed images:", len(scored))
print("Columns:", scored.columns.tolist())

print("\n===== SCORE SUMMARY =====")
print(
    scored[
        ["blur_score", "dark_score", "score"]
    ].describe().round(4)
)

print("\n===== TOP 10 SUSPICIOUS IMAGES =====")
print(
    scored.nlargest(10, "score")[
        ["image_id", "camera_id", "light", "split",
         "blur_score", "dark_score", "score"]
    ].to_string(index=False)
)

print("\n===== VALIDATION =====")
print("Unique image IDs:", scored["image_id"].is_unique)
print("All scores finite:", bool(scored["score"].map(pd.notna).all()))
print("Score range:", scored["score"].min(), "to", scored["score"].max())
print("Pipeline stats:", ctx.stats)
