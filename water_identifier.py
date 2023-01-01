"""
water_identifier.py
Extracts the colors from a screenshot of the game Water Sort.

Analyzes the pixels of the given screenshot to extract the game color
information, which could be used as input to `water_sorter.py` to solve
the given game.

Example run:
  $ python water_identifier.py level.png | python water_sorter.py
"""

# =============================================================================

import itertools
import json
import sys
from collections import defaultdict
from enum import Enum
from pathlib import Path

from PIL import Image

# =============================================================================

DEBUG = False

# =============================================================================

COLORS_FILE = Path('colors.json')


def read_colors_file():
    colors = {}
    data = json.loads(COLORS_FILE.read_bytes())
    for color, rgb in data.items():
        invalid_rgb_value_msg = f'invalid rgb value for color "{color}"'
        rgb = tuple(rgb)
        if len(rgb) != 3:
            raise ValueError(f'{invalid_rgb_value_msg}: not length 3')
        for val in rgb:
            if not isinstance(val, int):
                raise ValueError(f'{invalid_rgb_value_msg}: not ints')
            if not _in_range(val, (0, 255)):
                raise ValueError(
                    f'{invalid_rgb_value_msg}: not in range [0, 255]')
        if rgb in colors:
            raise ValueError(f'rgb value {rgb} is repeated in colors file')
        colors[rgb] = color
    return colors


# maps: rgb value -> color name
COLORS = read_colors_file()

# =============================================================================

BACKGROUND_CUTOFF = 40
TUBE_BORDER_GRAY_RANGE = (185, 190)
SAME_COLOR_ERROR = 3
TUBE_MIN_WIDTH = 125

# =============================================================================


def _in_range(value, range_):
    return range_[0] <= value <= range_[1]


def is_background(rgb):
    return all(val <= BACKGROUND_CUTOFF for val in rgb)


def is_border(rgb):
    return all(_in_range(val, TUBE_BORDER_GRAY_RANGE) for val in rgb)


def same_color(rgb1, rgb2):
    return all(
        abs(val1 - val2) <= SAME_COLOR_ERROR for val1, val2 in zip(rgb1, rgb2))


def avg_color(colors):
    avg = [0, 0, 0]
    if len(colors) == 0:
        return avg
    for rgb in colors:
        for i in range(3):
            avg[i] += rgb[i]
    for i in range(3):
        avg[i] /= len(colors)
    return tuple(avg)


# =============================================================================


def show_image_from_array(colors):
    """Show the given 2D array of RGB values as an image.
    For debugging purposes.
    """
    height = len(colors)
    width = len(colors[0])
    im = Image.new('RGB', (width, height))
    flattened = []
    for row in colors:
        for rgb in row:
            if rgb is None:
                flattened.append((0, 0, 0))
            else:
                flattened.append(rgb)
    im.putdata(flattened)
    im.show()


# =============================================================================


class PixelType(Enum):
    """The pixel types."""
    BACKGROUND = 1
    BORDER = 2
    COLOR = 3

    @classmethod
    def from_rgb(cls, rgb):
        if is_background(rgb):
            return cls.BACKGROUND
        if is_border(rgb):
            return cls.BORDER
        return cls.COLOR


def group_by_type(row):
    """Groups the pixels into PixelTypes.
    Yields the pixel type, the start column index, and a list of all the
    pixels in the group.
    """
    for pixel_type, group in itertools.groupby(
            enumerate(row), key=lambda x: PixelType.from_rgb(x[1])):
        index_pixels = list(group)
        c, _ = index_pixels[0]
        pixels = [pixel for _, pixel in index_pixels]
        yield pixel_type, c, pixels


# =============================================================================


def load_image_colors(filename):
    """Loads the given file image and returns its colors as a 2D array
    of RGB values.
    """
    with Image.open(filename) as im:
        im.load()
    pixels = iter(im.getdata())
    colors = []
    for _ in range(im.height):
        row = []
        for _ in range(im.width):
            rgb = next(pixels)
            row.append(rgb)
        colors.append(row)
    return colors


def crop_borders(colors):
    """Processes the colors to include only the rows between the first
    and last occurrence of border pixels.
    """
    # technically this step may be unnecessary, since `extract_tubes()`
    # already disregards any rows without border pixels
    width = len(colors[0])
    first_border_row = None
    last_border_row = None
    for r, row in enumerate(colors):
        first_border_col = None
        last_border_col = None
        for pixel_type, c, pixels in group_by_type(row):
            # there must be at least 5 consecutive border pixels to be
            # considered an actual border
            if pixel_type == PixelType.BORDER and len(pixels) > 5:
                if first_border_col is None:
                    first_border_col = c
                last_border_col = c
        if first_border_col is None:
            continue
        # the daily challenge calendar icon uses border colors, so
        # account for that case
        if first_border_col < width / 2 < last_border_col:
            # row has border pixels
            if first_border_row is None:
                first_border_row = r
            last_border_row = r
    if first_border_row is not None:
        return colors[first_border_row:last_border_row + 1]
    return colors


def extract_tubes(colors):
    """Extracts and returns the colors in the tubes."""
    all_tubes = []

    if DEBUG:
        testing = [[(0, 0, 0) for _ in row] for row in colors]
        unique_colors = {}
        index_to_color = {}

    # the start row index of the line being processed
    processing_line = None
    # the start index of the tubes being processed in `all_tubes`
    line_tube_start_index = 0
    # all the colors that appear in the given slot
    line_slot_colors = []
    # transitions between slots have a more transparent row right above
    # the proper color. so we use this flag to skip those
    slot_transition_transparent = True

    for r, row in enumerate(colors):
        # the tube index in the current line
        line_tube_index = 0
        in_tube = False

        seen_border = False
        slot_transition = False
        for pixel_type, c, pixels in group_by_type(row):
            if pixel_type == PixelType.BACKGROUND:
                pass
            elif pixel_type == PixelType.BORDER:
                if len(pixels) > 10:
                    # row of tube tops
                    seen_border = True
                    if processing_line is None:
                        # first row of new line
                        processing_line = r
                        line_tube_start_index = len(all_tubes)
                        line_slot_colors = []
                    if processing_line == r:
                        # add the tubes
                        if DEBUG:
                            # highlight the top of the tubes in red
                            for cc in range(len(pixels)):
                                testing[r][c + cc] = (255, 0, 0)
                        all_tubes.append([])
                        line_slot_colors.append(defaultdict(lambda: 0))
                elif len(pixels) > 3:
                    # side border
                    seen_border = True
                    if DEBUG:
                        # highlight the borders in white
                        for cc in range(len(pixels)):
                            testing[r][c + cc] = (255, 255, 255)
                    if in_tube:
                        # exiting tube
                        in_tube = False
                        line_tube_index += 1
                    else:
                        # entering tube
                        in_tube = True
            elif pixel_type == PixelType.COLOR:
                if not in_tube:
                    # likely a background
                    continue
                if len(pixels) < TUBE_MIN_WIDTH:
                    # at the bottom of a tube, which can be ignored
                    continue
                # count up the colors in this slot
                for rgb in pixels:
                    line_slot_colors[line_tube_index][rgb] += 1

                avg_rgb = avg_color(pixels)
                if r > 0:
                    above_rgb = avg_color(colors[r - 1][c:c + len(pixels)])
                    if is_border(above_rgb):
                        # first row inside the tube
                        pass
                    elif same_color(avg_rgb, above_rgb):
                        # same color; do nothing
                        pass
                    else:
                        # on a slot transition
                        slot_transition = True
                        if DEBUG:
                            # keep track of the slot transition
                            for cc in range(len(pixels)):
                                testing[r][c + cc] = None

        if not seen_border:
            # entire row is background pixels
            # reset the line of tubes we're looking at
            processing_line = None
            continue

        if DEBUG:
            # highlight the left side with blue: this row saw a border
            for c in range(3):
                testing[r][c] = (0, 0, 255)

        if slot_transition:
            # toggle between the transparent versions of the colors
            if slot_transition_transparent:
                slot_transition_transparent = False
                # clear slot colors
                for slot_colors in line_slot_colors:
                    slot_colors.clear()
                continue
            slot_transition_transparent = True

            if DEBUG and len(line_slot_colors) > 0:
                print('slot transition at row', r)
                # highlight the left side with cyan
                for c in range(3):
                    testing[r][c] = (0, 255, 255)

            draw_color_c = 0
            for i, slot_colors in enumerate(line_slot_colors):
                if len(slot_colors) == 0:
                    # empty slot
                    all_tubes[line_tube_start_index + i].append(None)
                    continue
                # find the most popular color in this slot
                best_rgb = None
                best_count = 0
                for rgb, count in slot_colors.items():
                    if count > best_count:
                        best_rgb = rgb
                        best_count = count
                if DEBUG:
                    if best_rgb not in unique_colors:
                        index = len(unique_colors)
                        unique_colors[best_rgb] = index
                        index_to_color[index] = best_rgb
                all_tubes[line_tube_start_index + i].append(best_rgb)
                # reset colors
                slot_colors.clear()

                if DEBUG:
                    saw_none = False
                    for c in range(draw_color_c, len(colors[0])):
                        if testing[r][c] is None:
                            saw_none = True
                            testing[r][c] = best_rgb
                        elif saw_none:
                            draw_color_c = c
                            break

    if DEBUG:
        show_image_from_array(testing)

        # print colors with ids rather than rgbs to make it easier to
        # read
        print('all colors:', index_to_color)
        print('all tubes:')
        for i, tube in enumerate(all_tubes):
            print(i, len(tube), [unique_colors[rgb] for rgb in tube])

        # show a tiny version of the tubes just to double check
        tube_colors = [[(0, 0, 0)
                        for _ in range(2 * len(all_tubes) - 1)]
                       for _ in range(len(all_tubes[0]))]
        for i, tube in enumerate(all_tubes):
            for j, rgb in enumerate(tube):
                if rgb is None:
                    continue
                tube_colors[j][2 * i] = rgb
        show_image_from_array(tube_colors)

    return all_tubes


# =============================================================================


def main():
    _, *args = sys.argv
    if len(args) == 0:
        print('Missing filename')
        sys.exit(1)
    filename = args[0]

    if DEBUG:
        print('WARNING: debug mode is on, so the output cannot be used as '
              'input to `water_sorter.py`')

    colors = crop_borders(load_image_colors(filename))
    tube_colors = extract_tubes(colors)

    if len(tube_colors) == 0:
        print('Could not extract the colors from the screenshot')
        sys.exit(1)

    # convert the rgb colors to their names
    added_color = False
    color_names = set(COLORS.values())
    for tube in tube_colors:
        tube_color_names = []
        for rgb in tube:
            if rgb is None:
                tube_color_names.append('')
                continue
            if rgb not in COLORS:
                added_color = True
                i = 0
                while True:
                    name = f'newColor{i}'
                    if name not in color_names:
                        break
                    i += 1
                color_names.add(name)
                COLORS[rgb] = name
            tube_color_names.append(COLORS[rgb])
        print(','.join(tube_color_names))

    if added_color:
        # write the new color names to the colors file
        data = {color: rgb for rgb, color in COLORS.items()}
        COLORS_FILE.write_text(json.dumps(data, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
