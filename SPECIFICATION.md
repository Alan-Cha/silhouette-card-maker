# SCM PDF and Cutting Template Specification

This document describes how Silhouette Card Maker (SCM) generates PDFs and cutting templates for card production.

## Purpose

This specification enables third-party PDF generators to create PDFs that are compatible with SCM's cutting templates. By following this specification, external tools can produce PDFs that align precisely with SCM's cut paths, ensuring that users can:

- Utilize custom card artwork with their preferred tools
- Trust that their PDFs will align correctly with SCM's templates
- Rely on stable, documented template behavior across SCM versions

### Attribution for Template Usage

When distributing or sharing SCM cutting templates, it is **strongly recommended** that you:

1. **Reference the source**: Clearly indicate that the template is sourced from [Silhouette Card Maker (SCM)](https://alan-cha.github.io/silhouette-card-maker/)
2. **Provide a link**: Include a link to the [SCM project repository](https://github.com/Alan-Cha/silhouette-card-maker-testing)
3. **Preserve filenames**: Keep the original SCM filename to enable users to match templates with their [source](https://github.com/Alan-Cha/silhouette-card-maker/tree/main/cutting_templates)
4. **Suggest the Discord**: The [SCM Discord](https://discord.gg/jhsKmAgbXc) is an important resource for debugging cutting issues.

**Why this matters:**
- Helps users find documentation and support for the template format
- Enables users to verify template authenticity and specification compliance
- Maintains the connection between templates and this specification
- Supports the open-source project that created the templates

While the MIT license does not legally require this attribution for generated outputs, following these practices benefits the entire SCM user community and ensures transparency about template origins.

## Overview

SCM creates print-ready PDFs and cutting templates optimized for double-sided card printing and precision cutting with Silhouette cutting machines. The system prioritizes alignment accuracy and accommodates machine calibration variations.

## Core Layout Principles

All calculated layouts for supported paper and card size combinations are stored in [layouts.json](https://github.com/Alan-Cha/silhouette-card-maker/blob/main/assets/layouts.json). This file contains:

- **Paper sizes**: Physical dimensions of supported paper types (letter, legal, tabloid, A4, A3, arch_b)
- **Card sizes**: Dimensions and corner radius for standard card types
- **Layout configurations**: For each paper/card combination:
  - `orientation`: Page orientation (portrait or landscape)
  - `num_rows` and `num_cols`: Grid dimensions (number of cards per axis)
  - `registration.length`: Optimized registration mark length for this layout
  - `version`: Version number to track layout changes over time
- **Defaults**: Default corner radius (3mm) and registration mark parameters (inset, thickness, length)

This file serves as the authoritative reference for SCM's template specifications and enables third-party tools to replicate SCM's layouts exactly.

### 1. Page Centering

**Cards are centered in the middle of the page.**

**Motivation**: Essential for double-sided card alignment. The back side of a double-sided print is mirrored relative to the front. If cards are offset from the center, this offset doubles between front and back sides due to mirroring. Centering eliminates this alignment issue entirely.

**Duplex printing orientation**: SCM produces PDFs optimized for **long-edge flip** (also called "flip on long edge" or "long-edge binding"), where the paper flips along its longer edge when printing the back side. Using this orientation is recommended for best compatibility with SCM templates, though not strictly required.

### 2. Uniform Grid Orientation

**All cards on a page are laid out in the same orientation (all portrait or all landscape).**

**Motivation**: Accommodates slight X/Y axis calibration discrepancies in cutting machines. If landscape and portrait cards were mixed, calibration errors would cause them to have different physical dimensions after cutting.

### 3. Orientation Optimization

**The page orientation (portrait/landscape) is optimized to maximize the number of cards that fit within the cutting area.**

**Implementation**: The system tries both portrait and landscape page orientations and selects the one that yields the highest card count while respecting registration mark exclusion zones.

## Card Spacing and Bleed

### Card Distance

Cards are positioned **1.25 mm** apart (center to center of the gap), defined as `CARD_DISTANCE = "1.25mm"` in [page_manager.py](page_manager.py)

The maximum bleed is half the card distance, which is **0.625 mm**.

### Corner Radius

The default corner radius of cards is 3 mm.

If you prefer to use a different corner radius, you can [create a new template](#creating-custom-templates). Because the other parameters are the same, you do not need to make changes to the PDF generator, simply use a new template to cut.

## Registration Marks

Registration marks enable the Silhouette cutting machine to align the cutting template with the printed page.

### Registration Mark Shape and Size

Each registration mark has a precisely defined shape:

**L-shaped mark**: Two perpendicular lines meeting at a corner
- **Horizontal arm**: Extends horizontally inward from the corner by `length` mm
- **Vertical arm**: Extends vertically inward from the corner by `length` mm
- **Line thickness**: `thickness` mm (consistent across both arms)
- **Corner position**: The meeting point of the arms is positioned `inset` mm from both paper edges

**Square mark** (THREE-mark pattern only, top-left corner):
- **Dimensions**: 5 mm × 5 mm filled black square
- **Border thickness**: Rendered with a black border of `thickness` mm around the filled square
- **Corner position**: The center of the square is positioned `inset` mm from both paper edges (same as L-marks)

### Registration Mark Dimensions

Default registration mark parameters are defined in [layouts.json](https://github.com/Alan-Cha/silhouette-card-maker/blob/main/assets/layouts.json):

| Parameter | Default | Description |
|-----------|---------|-------------|
| Length | 5.0 mm | Length of each arm of the L-shape (default when not optimized) |
| Thickness | 1.0 mm | Line thickness of the registration marks |
| Inset | 10.0 mm | Distance from paper edge to registration marks |

**Per-layout optimization**: Each specific layout in [layouts.json](https://github.com/Alan-Cha/silhouette-card-maker/blob/main/assets/layouts.json) specifies an optimized `registration.length` value that maximizes registration mark size while maintaining the required clearance from cards and bleed areas. These optimized values vary by paper size and card layout.

### Registration Mark Patterns and Arrangement

SCM supports two registration patterns. The arrangement of marks depends on both the pattern and the page orientation.

#### THREE-Mark Registration Pattern

**Machine compatibility**: Used by all Silhouette cutting machines except the Cameo 5 Alpha.

**Mark placement** (described clockwise from top-left):

- **Landscape orientation**: **L** → short edge → **Square** → long edge → **L**
- **Portrait orientation**: **L** → long edge → **Square** → short edge → **L**

#### FOUR-Mark Registration Pattern

**Machine compatibility**: Introduced and used by the Silhouette Cameo 5 Alpha machine.

**Mark placement**: L-shaped marks at all four corners

## Creating Custom Templates

SCM provides scripts for generating custom cutting templates that follow this specification:

- **[generate_dxf.py](generate_dxf.py)**: Generates DXF cutting templates from layout specifications
- **[dxf_to_studio3.py](dxf_to_studio3.py)**: Converts DXF files to Silhouette Studio format

For a complete walkthrough of the template generation process, see the [Template Generation Tutorial](https://alan-cha.github.io/silhouette-card-maker/miscellaneous/template/).

### Important: Naming Custom Templates

**If you create a modified version of an existing SCM template, please use an entirely different name.**

For example, if you modify `letter-standard-v6.studio3` to use a different corner radius, **DO NOT** name it `letter-standard-v7.studio3` — this could be confused with an official SCM template.

## Design Rationale

The SCM layout system prioritizes:

1. **Print alignment accuracy**: Centered layouts minimize the impact of printer feed variations
2. **Cutting accuracy**: Uniform orientation prevents calibration errors from affecting card dimensions
3. **Machine compatibility**: Registration mark specifications match Silhouette's requirements
4. **Predictability**: Deterministic layout algorithm with explicit failure modes rather than silent degradation
5. **Simplicity**: One orientation per page simplifies template generation and troubleshooting
