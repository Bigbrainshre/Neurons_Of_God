# IIT Pokerbots Engine

This is the reference implementation of the engine for playing Sneak Peek hold'em.

---

## Team Contributions & Competition Performance

This repository contains the collection of poker bots developed and submitted by **Shreyas Asthana** as part of the **team _Neurons_Of_God_** for the **IITK PokerBots** competition.

Over the course of the competition, our team iteratively designed, tested, and refined multiple strategic approaches to Sneak Peek Hold'em. In total, we created **approximately 30 bot submissions**, each representing incremental improvements in decision logic, probability handling, and strategic depth.

Our team ultimately **secured Rank 261** in the competition standings.

This repository reflects the evolution of strategies, experiments, and refinements that shaped the final competitive bots.

---

## Documentation

For a detailed guide on how to build your bot, including available classes, methods, and game logic, please refer to **[BOT_GUIDE.md](BOT_GUIDE.md)**.

---

## Folder Structure & Imports

To ensure your bot runs correctly, especially regarding imports, you must maintain the following folder structure. The `pkbot` package must be located in the same directory as your `bot.py` file.

```text
.
├── bot.py              # Your bot implementation
├── pkbot/              # Game engine package (do not modify)
├── config.py           # Configuration for the engine
├── engine.py           # The game engine executable
└── requirements.txt    # Python dependencies
