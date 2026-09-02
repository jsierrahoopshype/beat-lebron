# Beat LeBron

Six All-Stars, five lives, 15 seconds. Pick the two players whose combined stat or accolade beats LeBron James alone. Exactly one duo works.

- `index.html` - the whole game (no framework, no build step)
- `lebron-duo-data.js` - generated data: every All-Star in the HoopsMatic All-Time Database with 40 career metrics, plus LeBron's marks
- `build_lebron_duo_data.py` - regenerates the data file from the public nba-player-data JSON (`python build_lebron_duo_data.py`)
- `.github/workflows/update-data.yml` - optional daily rebuild via GitHub Actions

Questions are generated in the browser: the game picks a metric, a "big" player, a partner that pushes the pair narrowly past LeBron, and four fillers that all sit below the gap, which guarantees no other pair can reach LeBron's mark. Every question is verified before it is shown.
