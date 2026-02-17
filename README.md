# UEMGameTracker-CamoTracking

Call of Duty: Black Ops III - Tracker & Camo Matrix

A comprehensive external dashboard and overlay tool for Call of Duty: Black Ops III Zombies. This tool tracks live game statistics, calculates accurate weapon damage (bypassing the visual damage cap), manages custom camo progression for modded maps, and features a built-in challenge and reward system.
🤖 A Note on AI Development

This project was developed with the assistance of Generative AI.

If you are looking at the source code, you may notice patterns characteristic of AI-assisted generation, such as:

    Large blocks of HTML and CSS embedded directly within Python strings.

    Monolithic script structures.

    Specific logic patterns for UI state management.

While the code is fully functional and rigorously tested, it is structured differently than a traditional, manually architected application. It is provided "as-is" as a fun, community-focused tool.
✨ Key Features
📊 Live Game Tracker

    Real-Time Stats: Monitors Kills, Headshots, XP, Revives, and Downs.

    Damage Calculator: Tracks weapon damage beyond the standard integer limit (overflow support), giving you accurate numbers for high-round zombie health.

    Active Perks: Visual display of current perks with icons.

    Match Archival: Automatically saves match history to JSON files for later review.

🔫 Camo Matrix

    Custom Map Support: Track camo progress for weapons on custom zombies maps (requires profile JSON from uemmaps.com).

    Priority System: "Star" your favorite weapons to pin them to the top of the tracking list.

    Visual Progression: Dynamic progress bars and camo asset previews (Gold, Diamond, Dark Matter, etc.).

🏆 Challenges & Rewards

    Operations: Complete in-app challenges (e.g., "Get 1000 Headshots", "Survive 30 Rounds").

    Unlockables: Earn XP and unlock visual Themes (Void, Origins, Red Hex) and Calling Cards for the tracker interface.

🖥️ Overlay Mode

    Includes a "Unified Overlay" mode—a small, always-on-top window that sits over your game to show live perks and top weapon damage without cluttering the screen.

🛠️ Installation & Setup
Requirements

    OS: Windows 10/11

    Game: Call of Duty: Black Ops III (Steam Version recommended)

    Dependencies (if running from source): Python 3.x, pywebview, pyinstaller

How to Run

    Download/Compile: Ensure you have the executable (BO3Tracker.exe) and the accompanying asset folders.

    Asset Check: The following folders must be in the same directory as the .exe:

        perk icons

        camoimages

        callingcards

        themes

        trackericons (if applicable)

    Launch: Run BO3Tracker.exe.

    First Time Setup:

        Live Data File: Point the tracker to your local CurrentGame.json. This is usually found in your BO3 install directory under \players\CurrentGame.json.

        History Folder: Create a folder (e.g., BO3_History) and select it. This is where the tracker will save your past games.

📂 Project Structure

If you are modifying the source, the project requires the following file structure:

```text
BO3-Tracker/
│
├── assets/                  # 🎨 Game Assets & Data
│   ├── callingcards/        # Images/Videos for player cards
│   ├── camoimages/          # Images for weapon camos
│   ├── perk icons/          # Perk-a-Cola icons
│   ├── themes/              # CSS theme files
│   ├── custom_camos.json    # Database for modded map camos
│   ├── setup.css            # Styling for the setup window
│   └── style.css            # Main application styling
│
├── src/                     # 🐍 Python Source Code
│   ├── bo3tracker.py        # Main application entry point
│   └── challenge_system.py  # Backend logic for challenges
│
├── build_tracker.py         # 🔨 Script to compile the EXE
├── .gitignore               # 🚫 Files to exclude
├── LICENSE                  # ⚖️ License file
├── README.md                # 📖 Documentation
└── requirements.txt         # 📦 Dependencies
```

❓ Troubleshooting

    Stats not updating?

        Ensure the path to CurrentGame.json is correct in the Settings tab.

        Some mods only update this file at the end of a round or when the game is paused.

    Images/Icons missing?

        Ensure you have not moved the perk icons or camoimages folders away from the executable. The program looks for them in its immediate directory.

    "Classic" Badge:

        The Classic mode badge only appears if the gamemode string in the JSON contains "classic".

📜 License

This project is free to use for the Black Ops III Zombies community.
Visual assets (Perk Icons, Game Images) are the property of Activision/Treyarch. 
Also thanks to Sphynx for making an amazing black ops 3 mod. 
