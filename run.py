from sc2 import maps
from sc2.data import Difficulty, Race
from sc2.main import run_game
from sc2.player import Bot, Computer

from sajuuk import Sajuuk


def main():
    """
    Sets up and runs a single game of StarCraft II with the Sajuuk bot.

    This file is the primary entry point for testing the bot locally.
    It configures the map, the players (our bot vs. a computer),
    and launches the game.
    """
    # Use try-except to handle potential game launch errors gracefully.
    try:
        run_game(
            # maps.get() is a utility function to find a map by its name.
            # We are selecting "AbyssalReefLE", a standard ladder map.
            maps.get("AbyssalReefLE"),
            # Define the players. We are Player 1, a bot running our Sajuuk AI.
            [
                Bot(Race.Terran, Sajuuk(), name="Sajuuk"),
                # Player 2 is a computer opponent with an "Easy" difficulty.
                # This is ideal for initial testing and build order validation.
                Computer(Race.Zerg, Difficulty.Easy),
            ],
            # Set realtime=False to run the game as fast as possible.
            # This is standard for bot development and testing.
            realtime=False,
            # Optional: Specify a path to save the replay file.
            # This is extremely useful for debugging and analysis.
            save_replay_as="Sajuuk-vs-EasyZerg.SC2Replay",
        )
    except Exception as e:
        print(f"An error occurred while running the game: {e}")
        # This could be due to a missing map file, a configuration issue,
        # or an error within the bot's on_start() method.
        # Adding more detailed logging here would be a future improvement.


if __name__ == "__main__":
    main()
