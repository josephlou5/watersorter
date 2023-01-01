# Water Sorter

A solver for the game [Water Sort](https://apps.apple.com/app/id1514542157).

## Files

### `water_sorter.py`

Solves a given game using BFS to find the shortest path to a solved solution
(all tubes full of the same color). It accepts the game info from stdin, with
one tube per line, and the colors in the tube separated by commas. An empty slot
is specified by no color name.

You can find an example input at [`levels/level183.txt`](levels/level183.txt)
(the level I was on when I wrote this).

### `water_identifier.py`

Extracts the colors from a screenshot of the game. Prints the tube colors in the
format required for `water_sorter.py`, so the output can be piped as the input
to `water_sorter.py`.

### `colors.json`

To make the output of `water_identifier.py` easier to read, the RGB values of
colors can be given names in `colors.json`, where the keys are the color names
and the values are arrays of length 3. Any new colors seen in
`water_identifier.py` will be added to `colors.json`, where the user may rename
them as they please.
