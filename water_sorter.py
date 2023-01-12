"""
water_sorter.py
A solver for the game Water Sort.

This solver uses BFS to find the shortest solution to a given game of
Water Sort.

Accepts the game info from stdin, with one tube per line, and the colors
in the tube separated by commas. An empty slot is specified by no color
name.

Example run:
  $ python water_sorter.py < level_colors.txt
"""

# =============================================================================

import sys
from collections import defaultdict
from queue import SimpleQueue as Queue

# =============================================================================


class PourException(Exception):
    """An error that occurs while trying to pour."""


# =============================================================================


class Tubes:
    """All the tubes."""

    # The number of colors in a single tube
    CAPACITY = 4
    # A placeholder value for when a color doesn't exist in a slot
    EMPTY = -1

    class Tube:
        """Representation of a tube."""

        def __init__(self, state):
            self._state = list(state)
            self._hash_value = None
            self._on_change()

        @classmethod
        def empty(cls):
            return cls(Tubes.EMPTY for _ in range(Tubes.CAPACITY))

        def _on_change(self):
            """Triggers updates to the object when it changes."""
            # update the hash
            self._hash_value = hash(tuple(self._state))

        def __iter__(self):
            return iter(self._state)

        def __eq__(self, other):
            if self is other:
                return True
            return self._state == other._state

        def __hash__(self):
            return self._hash_value

        def __getitem__(self, index):
            return self._state[index]

        def __setitem__(self, index, value):
            self._state[index] = value
            self._on_change()

        def copy(self):
            return self.__class__(self._state)

    def __init__(
        self, parent, move_from_parent, num_tubes, colors, indices, tubes
    ):
        self._parent = parent
        self._move_from_parent = move_from_parent
        self._num_tubes = num_tubes
        self._colors = colors
        self._indices = indices
        self._tubes = list(tubes)
        self._hash_value = None
        self._is_solved = False
        self._on_change()

    @classmethod
    def initialize(cls, tube_colors):
        index_to_color = {Tubes.EMPTY: ""}
        color_to_index = {}
        counts = defaultdict(lambda: 0)
        tubes = []
        for i, colors in enumerate(tube_colors):
            if len(colors) == 0:
                # assume to be empty tube
                tubes.append(Tubes.Tube.empty())
                continue
            if len(colors) != Tubes.CAPACITY:
                raise ValueError(
                    f"tube {i+1} must have {Tubes.CAPACITY} colors"
                )
            tube = []
            seen_color = False
            for color in colors:
                if color == "":
                    if seen_color:
                        raise ValueError(
                            f"tube {i+1} has an empty space under a color: "
                            f"{colors}"
                        )
                    tube.append(Tubes.EMPTY)
                    continue
                if isinstance(color, str):
                    color = color.title()
                seen_color = True
                counts[color] += 1
                if counts[color] > Tubes.CAPACITY:
                    raise ValueError(
                        f"color {color!r} appears more than {Tubes.CAPACITY} "
                        "times"
                    )
                if color not in color_to_index:
                    index = len(index_to_color)
                    index_to_color[index] = color
                    color_to_index[color] = index
                tube.append(color_to_index[color])
            tubes.append(Tubes.Tube(tube))
        for color, count in counts.items():
            if count < Tubes.CAPACITY:
                raise ValueError(
                    f"color {color!r} does not appear {Tubes.CAPACITY} times"
                )
        return cls(
            None, None, len(tubes), index_to_color, color_to_index, tubes
        )

    def __str__(self):
        rows = [[] for _ in range(2 + Tubes.CAPACITY)]
        for i, tube in enumerate(self._tubes):
            col = [str(i + 1), ""]
            for index in tube:
                col.append(str(self._colors[index]))
            width = max(len(c) for c in col)
            col[1] = "-" * width
            for r, row in enumerate(rows):
                row.append(col[r].center(width))
        return "\n".join("  ".join(row) for row in rows)

    def __repr__(self):
        tube_colors = tuple(
            tuple(self._colors[index] for index in tube)
            for tube in self._tubes
        )
        return str(tube_colors)

    def _check_solved(self):
        for tube in self._tubes:
            first, *rest = tube
            for color in rest:
                if color != first:
                    return False
        return True

    def _on_change(self):
        """Triggers updates to the object when it changes."""
        # update the hash
        self._hash_value = hash(tuple(hash(tube) for tube in self._tubes))
        # check if it's solved
        self._is_solved = self._check_solved()

    def __iter__(self):
        return iter(self._tubes)

    def __eq__(self, other):
        if self is other:
            return True
        return self._tubes == other._tubes

    def __hash__(self):
        return self._hash_value

    @property
    def parent(self):
        return self._parent

    @property
    def move_from_parent(self):
        return self._move_from_parent

    @property
    def num_tubes(self):
        return self._num_tubes

    @property
    def is_solved(self):
        return self._is_solved

    def copy(self, move_from_parent):
        return self.__class__(
            self,
            move_from_parent,
            self._num_tubes,
            # no need to copy the color and index dicts
            self._colors,
            self._indices,
            self._tubes,
        )

    def set(self, index, tube):
        self._tubes[index] = tube
        self._on_change()

    def pour(self, tube_from, tube_to):
        if tube_from == tube_to:
            raise PourException("cannot pour from and to same tube")
        # find the first non-empty, which is the color being poured
        i_from = 0
        while self._tubes[tube_from][i_from] == Tubes.EMPTY:
            i_from += 1
            if i_from >= Tubes.CAPACITY:
                raise PourException("cannot pour from empty tube")
        moving_color = self._tubes[tube_from][i_from]
        # find the first non-empty, which is where to pour into
        i_to = Tubes.CAPACITY - 1
        while self._tubes[tube_to][i_to] != Tubes.EMPTY:
            i_to -= 1
            if i_to < 0:
                raise PourException("cannot pour into full tube")
        if i_to == Tubes.CAPACITY - 1:
            # the entire tube is empty
            pass
        elif self._tubes[tube_to][i_to + 1] != moving_color:
            raise PourException("cannot pour on a different color")
        # pour colors
        new_from = self._tubes[tube_from].copy()
        new_to = self._tubes[tube_to].copy()
        while (
            i_from < Tubes.CAPACITY
            and i_to >= 0
            and new_from[i_from] == moving_color
        ):
            new_from[i_from] = Tubes.EMPTY
            new_to[i_to] = moving_color
            i_from += 1
            i_to -= 1
        if i_from == Tubes.CAPACITY:
            # poured a full tube, which is unnecessary
            raise PourException("no need to pour a full tube")
        new_tubes = self.copy((tube_from, tube_to))
        new_tubes.set(tube_from, new_from)
        new_tubes.set(tube_to, new_to)
        return new_tubes


# =============================================================================


def _bfs(start_tubes):
    """Performs BFS at the given start tubes state.
    Returns the final solved state, which has parent links up to the
    starting position, or None if unsolvable.
    """
    if start_tubes.is_solved:
        return start_tubes
    seen = set()
    queue = Queue()
    queue.put(start_tubes)
    while not queue.empty():
        tubes = queue.get()
        # attempt all possible moves
        for tube_from in range(tubes.num_tubes):
            for tube_to in range(tubes.num_tubes):
                try:
                    poured = tubes.pour(tube_from, tube_to)
                except PourException:
                    # can't pour or bad pour, so skip
                    continue
                if poured.is_solved:
                    return poured
                if poured not in seen:
                    seen.add(poured)
                    queue.put(poured)
    return None


class Game:
    """Defines a game of Water Sort."""

    def __init__(self, tube_colors):
        self._tubes = Tubes.initialize(tube_colors)
        self._solved = False
        self._steps = None
        self._num_moves = None

    def __str__(self):
        return str(self._tubes)

    def __repr__(self):
        return f"Game({repr(self._tubes)})"

    @property
    def tubes(self):
        return self._tubes

    def solve(self):
        if self._solved:
            return
        print("Solving...")
        solved = _bfs(self._tubes)
        if solved is None:
            raise RuntimeError("Could not find a solution for the given game")
        # retrieve steps by walking up the parent tree
        steps = []
        tubes = solved
        while tubes is not None:
            steps.append(tubes)
            tubes = tubes.parent
        # save steps in proper order
        self._steps = list(reversed(steps))
        # `steps` includes the start, so subtract 1
        self._num_moves = len(self._steps) - 1
        self._solved = True

    def print_moves(self):
        if not self._solved:
            self.solve()
        start, *steps = self._steps
        print("Start:")
        print(start)
        for i, step in enumerate(steps):
            print()
            tube_from, tube_to = step.move_from_parent
            print(f"Step {i+1}: Pour tube {tube_from+1} into tube {tube_to+1}")
            print(step)
        print()
        print("Num moves:", self._num_moves)


# =============================================================================


def main():
    tube_colors = []
    for line in sys.stdin:
        line = line.strip()
        if line == "":
            tube_colors.append([])
            continue
        tube_colors.append([color.strip() for color in line.split(",")])
    if len(tube_colors) == 0:
        print("No tube colors given")
        return

    game = Game(tube_colors)
    try:
        game.solve()
    except RuntimeError as e:
        print(e)
        sys.exit(1)
    game.print_moves()


if __name__ == "__main__":
    main()
