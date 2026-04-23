# 2D Speedrun Platformer (Pygame)

A short 2D platformer focused on speedrunning. Each level has a countdown timer and local best-time tracking.

## Features

- Smooth run/jump controls (`A/D` or arrows, `Space` to jump).
- Hazards: spikes, pits, walls/geometry constraints, and patrolling enemies.
- Moving platforms with horizontal/vertical movement.
- Checkpoint system with on-screen feedback.
- Finish flag and end-of-level time summary.
- Pause menu (`P`) and start menu.
- Local high-score storage in `Game/highscores.json`.
- Basic generated sound effects (jump/checkpoint/finish).

## Run

```bash
python Game/game.py
```

## Controls

- `Enter`: Start game / return to menu from final screen
- `A/D` or `Left/Right`: Move
- `Space`: Jump
- `P`: Pause/resume
- `R`: Retry current level (after finishing)
- `N`: Next level / show run summary
- `Q`: Quit from menu

## Notes

- Default level timer is 90 seconds.
- Best times are saved per level and persist across runs.
