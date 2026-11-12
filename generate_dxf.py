#!/usr/bin/env python3
"""
Generate DXF cutting templates for paper/card size combinations.

Reads card and paper sizes from assets/layouts.json and computes card
positions dynamically using page_manager. Batch operations output to:
- cutting_templates/dxf/ (default variant)
- cutting_templates/borderless/dxf/ (borderless variant)

Usage:
    # Batch generation (uses standard directory structure)
    python generate_dxf.py batch              # Generate missing templates (default)
    python generate_dxf.py batch --all        # Regenerate all templates
    python generate_dxf.py batch --optimize   # Optimize orientations for all templates

    # Single file generation (custom output path)
    python generate_dxf.py single output.dxf --card_size poker --paper_size letter

    # List available sizes
    python generate_dxf.py list
"""

import json
from pathlib import Path

import click

import page_manager
import dxf_manager
import size_convert
from enums import Orientation, OrientationMode, Variant
from utilities import LayoutConfig, load_layout_config, template_name, resolve_card_size_alias, resolve_paper_size_alias, get_all_card_size_names, get_all_paper_size_names, find_best_orientation, resolve_cutting_templates_dir, extra_layout_paths, find_extra_layout_owner, BORDERLESS_INSET_MM, BORDERLESS_EXPANSION_MM

SCRIPT_DIR = Path(__file__).parent
CUTTING_TEMPLATES_DIR = resolve_cutting_templates_dir(SCRIPT_DIR / "cutting_templates")
OUTPUT_DIR = CUTTING_TEMPLATES_DIR / "dxf"
LAYOUTS_PATH = SCRIPT_DIR / "assets" / "layouts.json"


def borderless_fits_12x24_mat(paper_width: str, paper_height: str) -> bool:
    """Return True if the virtual borderless paper size fits within the 12x24 mat.

    Borderless templates expand each paper dimension by (10mm - inset) * 2. For papers that
    require the 12x24 mat, the virtual size must still fit within it (min dim ≤ 12in,
    max dim ≤ 24in) so that "Constrain Media to Cutting Mat" can remain ON in
    Silhouette Studio during conversion. See GitHub issue #136 for full details.

    This restriction will be lifted in the future by always leaving constrain OFF
    and assuming portrait mat orientation, which is consistent across all mat types.
    """
    virtual_w_in = (size_convert.size_to_mm(paper_width) + BORDERLESS_EXPANSION_MM) / 25.4
    virtual_h_in = (size_convert.size_to_mm(paper_height) + BORDERLESS_EXPANSION_MM) / 25.4
    return min(virtual_w_in, virtual_h_in) <= 12.0 and max(virtual_w_in, virtual_h_in) <= 24.0

layout_config = load_layout_config()
card_size_choices = get_all_card_size_names(layout_config)
paper_size_choices = get_all_paper_size_names(layout_config)


def generate_single_dxf(
    card_size: str,
    paper_size: str,
    variant: Variant,
    config: LayoutConfig,
    output_dir: Path,
) -> tuple[int, int, float]:
    """Generate a single DXF file for a paper/card/variant combination.

    Returns:
        (num_cols, num_rows, max_length_mm) tuple.
    """
    card_def = config.card_sizes[card_size]
    paper_def = config.paper_sizes[paper_size]
    layout_def = config.layouts[paper_size][card_size][variant.value]
    ppi = config.ppi

    # Use appropriate registration settings for variant
    if variant == Variant.BORDERLESS:
        variant_reg = config.defaults.registration.borderless
    else:
        variant_reg = config.defaults.registration.default

    orientation = layout_def.orientation
    version = layout_def.version

    total_length_mm = size_convert.size_to_mm(variant_reg.length) + page_manager.REG_PADDING_MM
    computed = page_manager.generate_layout(
        orientation=orientation,
        card_width=card_def.width,
        card_height=card_def.height,
        paper_width=paper_def.width,
        paper_height=paper_def.height,
        inset=variant_reg.inset,
        length=f"{total_length_mm}mm",
        ppi=ppi,
    )

    x_pos = computed.x_pos
    y_pos = computed.y_pos
    num_cols = len(x_pos)
    num_rows = len(y_pos)

    name = template_name(paper_size, card_size, variant, version)

    # Write to the specified output directory
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"{name}.dxf"

    dxf_manager.generate_dxf(
        card_def.width,
        card_def.height,
        card_def.radius or config.defaults.card_radius,
        x_pos,
        y_pos,
        ppi,
        output_path=str(output_file),
        shape=card_def.shape or "rectangle",
    )

    num_cards = num_cols * num_rows
    print(f"  {paper_size} + {card_size} ({variant}): {num_cols}x{num_rows} ({num_cards} cards), max_length={computed.max_length_mm}mm -> {output_file}")
    return num_cols, num_rows, computed.max_length_mm


@click.group()
def cli():
    """Generate DXF cutting templates from layouts.json."""
    pass


@cli.command()
@click.argument("output_file", type=click.Path())
@click.option("--card_size", type=click.Choice(card_size_choices, case_sensitive=False), help="Card size. Cannot be combined with --card_height/--card_width.")
@click.option("--paper_size", type=click.Choice(paper_size_choices, case_sensitive=False), help="Paper size. Cannot be combined with --paper_height/--paper_width.")
@click.option("--card_height", type=str, default=None, help="Card length (height) as a size string (e.g. '88mm', '3.5in'). Requires --card_width. Cannot be combined with --card_size.")
@click.option("--card_width", type=str, default=None, help="Card width as a size string (e.g. '63mm', '2.5in'). Requires --card_height. Cannot be combined with --card_size.")
@click.option("--card_radius", type=str, default=None, help="Card corner radius as a size string (e.g. '3mm'). Overrides the default radius for the card size. Defaults to 3mm when using --card_height/--card_width.")
@click.option("--card_name", type=str, default=None, help="Override the card label used for the output filename and --save.")
@click.option("--paper_height", type=str, default=None, help="Paper length (longer dimension) as a size string (e.g. '11in', '297mm'). Requires --paper_width. Cannot be combined with --paper_size.")
@click.option("--paper_width", type=str, default=None, help="Paper width (shorter dimension) as a size string (e.g. '8.5in', '210mm'). Requires --paper_height. Cannot be combined with --paper_size.")
@click.option("--paper_name", type=str, default=None, help="Override the paper label used for the output filename and --save.")
@click.option("--variant", type=click.Choice(["default", "borderless"], case_sensitive=False), default="default", show_default=True, help="Template variant.")
@click.option("--orientation", type=click.Choice([e.value for e in OrientationMode], case_sensitive=False), default=OrientationMode.OPTIMIZE.value, show_default=True, help="Page orientation: optimize (auto-select), landscape, or portrait.")
@click.option("--save", is_flag=True, help="Save new card/paper sizes and layout combination to assets/layouts.json.")
def single(output_file, paper_size, card_size, card_height, card_width, card_radius, paper_height, paper_width, card_name, paper_name, variant, orientation, save):
    """Generate a single DXF file with full control over output path."""
    config = load_layout_config()

    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Validate card dimension options
    has_card_size = card_size is not None
    has_card_dims = card_height is not None or card_width is not None

    if has_card_size and has_card_dims:
        raise click.UsageError("Cannot use --card_size together with --card_height or --card_width.")
    if card_height is not None and card_width is None:
        raise click.UsageError("--card_height requires --card_width.")
    if card_width is not None and card_height is None:
        raise click.UsageError("--card_width requires --card_height.")

    # Validate paper dimension options
    has_paper_size = paper_size is not None
    has_paper_dims = paper_height is not None or paper_width is not None

    if has_paper_size and has_paper_dims:
        raise click.UsageError("Cannot use --paper_size together with --paper_height or --paper_width.")
    if paper_height is not None and paper_width is None:
        raise click.UsageError("--paper_height requires --paper_width.")
    if paper_width is not None and paper_height is None:
        raise click.UsageError("--paper_width requires --paper_height.")

    if not has_card_size and not has_card_dims:
        raise click.UsageError("Provide --card_size or (--card_height and --card_width).")
    if not has_paper_size and not has_paper_dims:
        raise click.UsageError("Provide --paper_size or (--paper_height and --paper_width).")

    # Resolve aliases
    if has_card_size:
        card_size = resolve_card_size_alias(config, card_size)
    if has_paper_size:
        paper_size = resolve_paper_size_alias(config, paper_size)

    # Resolve card parameters
    if has_card_size:
        card_def = config.card_sizes[card_size]
        resolved_card_width = card_def.width
        resolved_card_height = card_def.height
        resolved_card_radius = card_radius if card_radius is not None else (card_def.radius or config.defaults.card_radius)
        resolved_card_shape = card_def.shape or "rectangle"
        card_label = card_size
    else:
        resolved_card_width = card_width
        resolved_card_height = card_height
        resolved_card_radius = card_radius if card_radius is not None else config.defaults.card_radius
        resolved_card_shape = "rectangle"
        card_label = f"{card_width}x{card_height}"

    # Resolve paper parameters (stored as landscape: longer dim = width)
    if has_paper_size:
        paper_def = config.paper_sizes[paper_size]
        resolved_paper_width = paper_def.width
        resolved_paper_height = paper_def.height
        paper_label = paper_size
    else:
        pl_mm = size_convert.size_to_mm(paper_height)
        pw_mm = size_convert.size_to_mm(paper_width)
        if pl_mm >= pw_mm:
            resolved_paper_width = paper_height
            resolved_paper_height = paper_width
        else:
            resolved_paper_width = paper_width
            resolved_paper_height = paper_height
        paper_label = f"{paper_width}x{paper_height}"

    # Apply name overrides
    if card_name is not None:
        card_label = card_name
    if paper_name is not None:
        paper_label = paper_name

    # Determine version for the output filename
    version = 1

    # Try to look up existing layout definition
    if paper_size and card_size:
        paper_layouts = config.layouts.get(paper_size, {})
        card_variants = paper_layouts.get(card_size, {})
        if variant in card_variants:
            version = card_variants[variant].version

    # Select appropriate registration settings for variant
    if variant == "borderless":
        reg = config.defaults.registration.borderless
    else:
        reg = config.defaults.registration.default
    ppi = config.ppi

    total_length_mm = size_convert.size_to_mm(reg.length) + page_manager.REG_PADDING_MM

    card_w_px = size_convert.size_to_pixel(resolved_card_width, ppi)
    card_h_px = size_convert.size_to_pixel(resolved_card_height, ppi)
    preferred = Orientation.PORTRAIT if card_w_px == card_h_px else Orientation.LANDSCAPE

    try:
        template_inset = reg.inset

        resolved_orientation, computed = find_best_orientation(
            OrientationMode(orientation),
            resolved_card_width,
            resolved_card_height,
            resolved_paper_width,
            resolved_paper_height,
            inset=template_inset,
            length=f"{total_length_mm}mm",
            ppi=ppi,
            preferred=preferred,
        )
    except ValueError as e:
        raise click.UsageError(str(e))

    x_pos = computed.x_pos
    y_pos = computed.y_pos
    num_cols = len(x_pos)
    num_rows = len(y_pos)

    dxf_manager.generate_dxf(
        resolved_card_width,
        resolved_card_height,
        resolved_card_radius,
        x_pos,
        y_pos,
        ppi,
        output_path=str(output_path),
        shape=resolved_card_shape,
    )

    num_cards = num_cols * num_rows
    print(f"  {paper_label} + {card_label} ({variant}): {num_cols}x{num_rows} ({num_cards} cards), max_length={computed.max_length_mm}mm -> {output_path}")

    if save:
        # Prefer the extra file that already defines this card size (or, failing that, this
        # paper size), so a layout lands alongside the size it's for rather than an unrelated
        # file when more than one extra layout file is in use. Falls back to the last extra
        # file, then this repo's own layouts.json, so opt-in extra sizes stay out of it.
        extra_paths = extra_layout_paths()
        save_path = (
            find_extra_layout_owner('card_sizes', card_label)
            or find_extra_layout_owner('paper_sizes', paper_label)
            or (extra_paths[-1] if extra_paths else LAYOUTS_PATH)
        )

        if save_path.exists():
            with open(save_path, 'r') as f:
                raw_config = json.load(f)
        else:
            raw_config = {}
        raw_config.setdefault("card_sizes", {})
        raw_config.setdefault("paper_sizes", {})
        raw_config.setdefault("layouts", {})

        changed = False

        # Existence checks use `config` (the already-merged view loaded at the top of this
        # command) rather than raw_config, since raw_config may be just a delta file that
        # doesn't redefine sizes already present in the base layouts.json or an earlier delta.
        if card_label not in config.card_sizes:
            raw_config["card_sizes"][card_label] = {
                "width": resolved_card_width,
                "height": resolved_card_height,
                "radius": resolved_card_radius,
            }
            print(f"  Saved new card size '{card_label}': {resolved_card_width} x {resolved_card_height}, radius {resolved_card_radius}")
            changed = True

        if paper_label not in config.paper_sizes:
            raw_config["paper_sizes"][paper_label] = {
                "width": resolved_paper_width,
                "height": resolved_paper_height,
            }
            print(f"  Saved new paper size '{paper_label}': {resolved_paper_width} x {resolved_paper_height}")
            changed = True

        # Check if layout exists for this paper/card/variant combination
        layout_exists = (
            paper_label in config.layouts
            and card_label in config.layouts.get(paper_label, {})
            and variant in config.layouts[paper_label].get(card_label, {})
        )

        if not layout_exists:
            if paper_label not in raw_config["layouts"]:
                raw_config["layouts"][paper_label] = {}
            if card_label not in raw_config["layouts"][paper_label]:
                raw_config["layouts"][paper_label][card_label] = {}
            raw_config["layouts"][paper_label][card_label][variant] = {
                "orientation": resolved_orientation.value,
                "version": version,
                "num_rows": num_rows,
                "num_cols": num_cols,
                "registration": {"length": f"{computed.max_length_mm}mm"},
            }
            print(f"  Saved new layout '{paper_label}' + '{card_label}' ({variant})")
            changed = True

        if changed:
            save_path.parent.mkdir(parents=True, exist_ok=True)
            with open(save_path, 'w') as f:
                json.dump(raw_config, f, indent=4)
                f.write('\n')
        else:
            print("  No new entries to save.")

    print("Done!")


@cli.command()
@click.option("--all", "generate_all", is_flag=True, help="Regenerate all DXF files for every paper/card/variant combination.")
@click.option("--optimize", "optimize_all", is_flag=True, help="Generate DXF files for all combinations, optimizing orientation for maximum cards.")
def batch(generate_all, optimize_all):
    """Batch generate DXF files to cutting_templates/ directory structure.

    By default, generates only missing templates. Use --all to regenerate
    everything, or --optimize to re-optimize orientations for all layouts.
    """
    config = load_layout_config()
    out = OUTPUT_DIR

    if generate_all and optimize_all:
        raise click.UsageError("Provide at most one of: --all or --optimize")

    if optimize_all:
        generate_all_optimized(config, out)
        return

    # --all or --new
    with open(LAYOUTS_PATH, 'r') as f:
        raw_config = json.load(f)

    generated = 0
    skipped = 0
    errors = 0
    error_list = []
    print(f"Generating DXF files to: {out} and {out.parent / 'borderless' / 'dxf'}")
    print()

    # Iterate over all paper/card/variant combinations
    for ps, cards in config.layouts.items():
        for cs, variants in cards.items():
            for variant_str, layout_def in variants.items():
                variant = Variant(variant_str)
                name = template_name(ps, cs, variant, layout_def.version)

                # Determine output directory based on variant
                if variant == Variant.BORDERLESS:
                    variant_dir = out.parent / "borderless" / "dxf"
                else:
                    variant_dir = out

                check_file = variant_dir / f"{name}.dxf"

                if not generate_all and check_file.exists():
                    skipped += 1
                    continue

                # For borderless templates on papers that need the 12x24 mat, skip if the
                # virtual paper size (+13mm each dimension) would exceed the 12x24 mat.
                # When the virtual size exceeds the mat, "Constrain Media to Cutting Mat"
                # must be disabled to enter the dimensions — but disabling constrain causes
                # the 12x24 mat to ignore landscape orientation (GitHub issue #136).
                # TODO (#136): Remove this restriction once all templates use unconstrained
                # mode with portrait mat orientation.
                if variant == Variant.BORDERLESS:
                    paper_def = config.paper_sizes[ps]
                    actual_max_in = max(
                        size_convert.size_to_mm(paper_def.width),
                        size_convert.size_to_mm(paper_def.height),
                    ) / 25.4
                    if actual_max_in > 12.0 and not borderless_fits_12x24_mat(paper_def.width, paper_def.height):
                        print(f"  Skipping {ps} + {cs} (borderless): virtual paper size exceeds 12x24 mat (see issue #136)")
                        skipped += 1
                        continue

                try:
                    num_cols, num_rows, ml_mm = generate_single_dxf(cs, ps, variant, config, variant_dir)
                    raw_config["layouts"][ps][cs][variant_str]["num_rows"] = num_rows
                    raw_config["layouts"][ps][cs][variant_str]["num_cols"] = num_cols
                    raw_config["layouts"][ps][cs][variant_str]["registration"] = {"length": f"{ml_mm}mm"}
                    generated += 1
                except Exception as e:
                    print(f"  Error: {ps} + {cs} ({variant}): {e}")
                    error_list.append((f"{ps} + {cs} ({variant})", e))
                    errors += 1

    if error_list:
        print(f'Errors: {error_list}')

    with open(LAYOUTS_PATH, 'w') as f:
        json.dump(raw_config, f, indent=4)
        f.write('\n')

    print()
    summary = f"Generated {generated} DXF files ({errors} errors)"
    if not generate_all:
        summary += f", skipped {skipped} existing"
    print(summary)


@cli.command()
def list():
    """List available card and paper sizes."""
    config = load_layout_config()

    print("Card sizes:")
    for name in sorted(config.card_sizes.keys()):
        card = config.card_sizes[name]
        aliases = f" (aliases: {', '.join(card.aliases)})" if card.aliases else ""
        print(f"  {name}: {card.width} x {card.height}{aliases}")

    print()
    print("Paper sizes:")
    for name in sorted(config.paper_sizes.keys()):
        paper = config.paper_sizes[name]
        aliases = f" (aliases: {', '.join(paper.aliases)})" if paper.aliases else ""
        print(f"  {name}: {paper.width} x {paper.height}{aliases}")


def generate_all_optimized(config: LayoutConfig, out: Path):
    """Generate DXF files for all paper/card/variant combinations, optimizing orientation.

    Iterates over every paper_size × card_size × variant combination from layouts.json.
    For existing layouts, re-optimizes orientation and bumps the version if
    it changes. For missing combinations, creates a new layout entry at v1.
    """
    with open(LAYOUTS_PATH, 'r') as f:
        raw_config = json.load(f)

    generated = 0
    added = 0
    errors = 0
    updated = 0
    error_list = []
    print(f"Optimizing orientations and generating DXF files to: {out}")
    print()

    # Iterate over all paper/card/variant combinations
    for paper_size, cards in config.layouts.items():
        paper_def = config.paper_sizes[paper_size]

        for card_size, variants in cards.items():
            card_def = config.card_sizes[card_size]

            for variant_str, layout_def in variants.items():
                variant = Variant(variant_str)
                # For borderless templates on papers that need the 12x24 mat, skip if the
                # virtual paper size (+13mm each dimension) would exceed the 12x24 mat.
                # See batch() and GitHub issue #136 for full explanation.
                # TODO (#136): Remove this restriction once all templates use unconstrained
                # mode with portrait mat orientation.
                if variant == Variant.BORDERLESS:
                    actual_max_in = max(
                        size_convert.size_to_mm(paper_def.width),
                        size_convert.size_to_mm(paper_def.height),
                    ) / 25.4
                    if actual_max_in > 12.0 and not borderless_fits_12x24_mat(paper_def.width, paper_def.height):
                        print(f"  Skipping {paper_size} + {card_size} (borderless): virtual paper size exceeds 12x24 mat (see issue #136)")
                        continue

                try:
                    # Use appropriate registration settings for variant
                    if variant == Variant.BORDERLESS:
                        variant_reg = config.defaults.registration.borderless
                    else:
                        variant_reg = config.defaults.registration.default

                    ppi = config.ppi
                    total_length_mm = size_convert.size_to_mm(variant_reg.length) + page_manager.REG_PADDING_MM

                    version = layout_def.version

                    # Prefer landscape page for all cards (both square and non-square)
                    preferred = Orientation.LANDSCAPE

                    try:
                        best_orientation, best_computed = find_best_orientation(
                            OrientationMode.OPTIMIZE,
                            card_def.width,
                            card_def.height,
                            paper_def.width,
                            paper_def.height,
                            inset=variant_reg.inset,
                            length=f"{total_length_mm}mm",
                            ppi=ppi,
                            preferred=preferred,
                        )
                    except ValueError:
                        print(f"  {paper_size} + {card_size} ({variant}): no valid layout in either orientation, skipping")
                        continue

                    best_count = len(best_computed.x_pos) * len(best_computed.y_pos)
                    num_cols = len(best_computed.x_pos)
                    num_rows = len(best_computed.y_pos)

                    # Check if orientation or layout changed
                    if (best_orientation != layout_def.orientation
                            or num_cols != layout_def.num_cols
                            or num_rows != layout_def.num_rows):
                        version += 1
                        updated += 1

                    # Update layout definition
                    raw_config["layouts"][paper_size][card_size][variant_str]["orientation"] = best_orientation.value
                    raw_config["layouts"][paper_size][card_size][variant_str]["version"] = version
                    raw_config["layouts"][paper_size][card_size][variant_str]["num_rows"] = num_rows
                    raw_config["layouts"][paper_size][card_size][variant_str]["num_cols"] = num_cols
                    raw_config["layouts"][paper_size][card_size][variant_str]["registration"] = {"length": f"{best_computed.max_length_mm}mm"}

                    name = template_name(paper_size, card_size, variant, version)

                    # Determine output directory based on variant
                    if variant == Variant.BORDERLESS:
                        variant_dir = out.parent / "borderless" / "dxf"
                    else:
                        variant_dir = out
                    variant_dir.mkdir(parents=True, exist_ok=True)
                    output_file = variant_dir / f"{name}.dxf"

                    dxf_manager.generate_dxf(
                        card_def.width, card_def.height, card_def.radius or config.defaults.card_radius,
                        best_computed.x_pos, best_computed.y_pos, ppi,
                        output_path=str(output_file),
                        shape=card_def.shape or "rectangle",
                    )

                    print(f"  {paper_size} + {card_size} ({variant}): {num_cols}x{num_rows} ({best_count} cards), max_length={best_computed.max_length_mm}mm -> {output_file}")
                    generated += 1

                except Exception as e:
                    print(f"  Error: {paper_size} + {card_size} ({variant}): {e}")
                    error_list.append((f"{paper_size} + {card_size} ({variant})", e))
                    errors += 1

    if error_list:
        print(f'Errors: {error_list}')

    with open(LAYOUTS_PATH, 'w') as f:
        json.dump(raw_config, f, indent=4)
        f.write('\n')

    print()
    summary = f"Generated {generated} DXF files ({errors} errors)"
    if added > 0:
        summary += f", added {added} new layouts"
    if updated > 0:
        summary += f", updated {updated} orientations"
    print(summary)


if __name__ == "__main__":
    cli()
