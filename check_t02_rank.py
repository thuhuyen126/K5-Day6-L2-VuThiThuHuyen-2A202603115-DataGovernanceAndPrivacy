
from pathlib import Path

import pandas as pd
import numpy as np

from src.common.context import RunContext
from src.pipeline import load, process, rank


root = Path("fixtures/t02_raw_qc")

ctx = RunContext(
    track="t02",
    input_dir=root,
    output_dir=Path("out/rank_check"),
    config={
        "params": {
            "budget": 20,
            "dev_split": "dev",
            "min_group_size": 10,
        }
    },
    seed=42,
    rng=np.random.default_rng(42),
)

data = load(ctx)
scored = process(ctx, data)
queue = rank(ctx, scored)

print("===== RANK VALIDATION =====")
print("Queue rows:", len(queue))
print("Unique item IDs:", queue["item_id"].is_unique)
print("Columns:", queue.columns.tolist())

print("\n===== TOP 10 QUEUE =====")
print(queue.head(10).to_string(index=False))

print("\n===== SCORE ORDER =====")
print("Descending:", queue["score"].is_monotonic_decreasing)

print("\n===== SAVED FILE =====")
output_file = ctx.output_dir / "review_queue.csv"
print("Exists:", output_file.is_file())

saved = pd.read_csv(output_file)
print("Saved rows:", len(saved))
print("Saved columns:", saved.columns.tolist())

print("\n===== T02 OUTPUT CONTRACT =====")
print("Has item_id:", "item_id" in saved.columns)
print("Has score:", "score" in saved.columns)

print(
    "Queue IDs match scored IDs:",
    set(queue["item_id"]) == set(
        scored.nlargest(20, "score")["image_id"].astype(str)
    )
)
