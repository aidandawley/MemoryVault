# backend/api/tools/_debug_similarity.py

from backend.api.tools.tag_similarity import CategoryIndex
# 👇 this must exist in tag_similarity.py (the code you said you added at the bottom)
from backend.api.tools.tag_similarity import decide_resolution

CATEGORIES = [
    "wedding",
    "ceremony",
    "reception",
    "dance",
    "family",
    "friends",
]

TEST_TAGS = [
    "dancing",
    "first dance",
    "bride and groom",
    "party",
    "soccer game",
]

def main():
    idx = CategoryIndex(CATEGORIES)
    idx.rebuild()

    for tag in TEST_TAGS:
        mr = idx.match_tag(tag, top_k=3)
        decision = decide_resolution(mr, idx.categories)

        print("—" * 60)
        print(f"input:      {mr.input_tag}")
        print(f"normalized: {mr.normalized_tag}")
        print(f"topk:       {mr.topk}")
        print(f"decision:   action={decision.action} chosen={decision.chosen} "
              f"conf={decision.confidence:.3f} margin={decision.margin:.3f}")

if __name__ == "__main__":
    main()