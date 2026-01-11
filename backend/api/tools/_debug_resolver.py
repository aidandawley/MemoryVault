# backend/api/tools/_debug_resolver.py
from backend.api.tools.tag_similarity import CategoryIndex
from backend.api.tools.tag_resolver import resolve_tags


def main():
    # pretend these are your “top categories so far”
    categories = ["wedding", "ceremony", "reception", "dance", "friends", "family"]
    index = CategoryIndex(categories)
    index.rebuild()

    # pretend these are tags from ONE image (or a small batch)
    tags = [
        # strong wedding matches
        "bride and groom",
        "first dance",

        # deterministic alias -> match
        "dancing",

        # likely gray-area cluster tests
        "party",
        "wedding party",
        "reception party",

        # learn_new=True tests
        "soccer game",     # should become NEW (soccer)
        "soccer",          # should now MATCH soccer
        "soccer match",    # should also MATCH soccer (or be close)

        # more NEW category creation tests
        "football game",   # should normalize -> football (new unless already present)
        "basketball game", # should normalize -> basketball (new unless already present)

        # clearly unrelated -> NEW
        "sunset",
    ]

    results = resolve_tags(tags, index, top_k=3, learn_new=True)

    for r in results:
        print("—" * 80)
        print(f"raw:         {r.raw}")
        print(f"normalized:   {r.normalized}")
        print(f"action:       {r.action}")
        print(f"chosen:       {r.chosen}")
        print(f"conf:         {r.confidence:.3f}")
        print(f"margin:       {r.margin:.3f}")
        print(f"topk:         {r.topk}")
        top1 = r.topk[0] if len(r.topk) >= 1 else None
        top2 = r.topk[1] if len(r.topk) >= 2 else None
        print(f"top1/top2:    {top1} | {top2}")

    print("—" * 80)
    print("final categories:", index.categories)


if __name__ == "__main__":
    main()