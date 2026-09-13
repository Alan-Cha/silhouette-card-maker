import size_convert
from utilities import load_layout_config


def format_number(n):
    rounded = round(n, 3)
    if rounded == int(rounded):
        return str(int(rounded))
    return f"{rounded:.3f}".rstrip("0").rstrip(".")


def generate_tables():
    config = load_layout_config()

    paper_order = ["letter", "legal", "tabloid", "a4", "a3", "arch_b"]

    def card_size_sort_key(name):
        card = config.card_sizes[name]
        w_mm = size_convert.size_to_mm(card.width)
        h_mm = size_convert.size_to_mm(card.height)
        return (-max(w_mm, h_mm), -min(w_mm, h_mm), name)

    priority = ["standard", "poker", "bridge"]
    card_order_alpha = [c for c in priority if c in config.card_sizes] + sorted(
        (c for c in config.card_sizes if c not in priority), key=lambda n: (n[0].isdigit(), n)
    )
    card_order_by_size = sorted(config.card_sizes.keys(), key=card_size_sort_key)

    # Table 1: Default layouts (alphabetical card order)
    print("| Format |", " | ".join(f"`{p}`" for p in paper_order), "|")
    print("|---|" + "---|" * len(paper_order))

    for card in card_order_alpha:
        cells = []
        for paper in paper_order:
            layout = config.layouts.get(paper, {}).get(card, {}).get("default")
            if layout:
                cells.append(f"{layout.num_cols}x{layout.num_rows} ({layout.num_cols * layout.num_rows})")
            else:
                cells.append("❌")
        print(f"| `{card}` | {' | '.join(cells)} |")

    print()

    # Table 1b: Borderless template benefits vs default
    print("| Format |", " | ".join(f"`{p}`" for p in paper_order), "|")
    print("|---|" + "---|" * len(paper_order))

    borderless_unsupported = {"a3", "arch_b"}

    for card in card_order_alpha:
        cells = []
        for paper in paper_order:
            if paper in borderless_unsupported:
                cells.append("N/A")
                continue
            default = config.layouts.get(paper, {}).get(card, {}).get("default")
            borderless = config.layouts.get(paper, {}).get(card, {}).get("borderless")
            if default and borderless:
                improvement = (borderless.num_cols * borderless.num_rows) - (default.num_cols * default.num_rows)
                cell = f"{borderless.num_cols}x{borderless.num_rows} ({improvement:+d})"
                cells.append(f"**{cell}**" if improvement > 0 else cell)
            else:
                cells.append("N/A")
        print(f"| `{card}` | {' | '.join(cells)} |")

    print()

    # Table 2: Card sizes (largest first)
    print("| Card size | Inches | Millimeters | Aspect Ratio | Notes |")
    print("| --- | --- | --- | --- | --- |")

    for card in card_order_by_size:
        info = config.card_sizes[card]

        w_in = size_convert.size_to_in(info.width)
        h_in = size_convert.size_to_in(info.height)
        w_mm = size_convert.size_to_mm(info.width)
        h_mm = size_convert.size_to_mm(info.height)

        in_str = f"{format_number(min(w_in, h_in))} x {format_number(max(w_in, h_in))}"
        mm_str = f"{format_number(min(w_mm, h_mm))} x {format_number(max(w_mm, h_mm))}"

        if info.width.endswith("in"):
            in_str = f"**{in_str}**"
        else:
            mm_str = f"**{mm_str}**"

        aspect = min(w_mm, h_mm) / max(w_mm, h_mm)
        notes = "<br>".join(f"AKA `{a}`" for a in (info.aliases or []))

        print(f"| `{card}` | {in_str} | {mm_str} | {aspect:.4f} | {notes} |")

    print()

    # Table 3: Paper sizes
    print("| Paper size | Inches | Millimeters | Notes |")
    print("| --- | --- | --- | --- |")

    for paper in paper_order:
        info = config.paper_sizes[paper]

        w_in = size_convert.size_to_in(info.width)
        h_in = size_convert.size_to_in(info.height)
        w_mm = size_convert.size_to_mm(info.width)
        h_mm = size_convert.size_to_mm(info.height)

        in_str = f"{format_number(min(w_in, h_in))} x {format_number(max(w_in, h_in))}"
        mm_str = f"{format_number(min(w_mm, h_mm))} x {format_number(max(w_mm, h_mm))}"

        if info.width.endswith("in"):
            in_str = f"**{in_str}**"
        else:
            mm_str = f"**{mm_str}**"

        notes = "<br>".join(f"AKA `{a}`" for a in (info.aliases or []))

        print(f"| `{paper}` | {in_str} | {mm_str} | {notes} |")


if __name__ == "__main__":
    generate_tables()
