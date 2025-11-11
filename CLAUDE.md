# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

"Nothing is U.P" is a terminal-based surveillance state simulator game written in Python. The player acts as a state inspector reviewing intercepted conversations, deciding which citizens to flag as suspicious. Guilty citizens are known to be sent to the U.P department. The game explores themes of privacy, surveillance, and state power through interactive gameplay.

## New Improved Narrative

- YOU MUST adhere to the improved narrative.
"Nothing to Hide - The U.P department" is a terminal-based surveillance state simulator written in Python. The player acts as a state inspector, part of a draconic, authoritarian, but dying state. You are tasked with investigating the recent uptake in "rebellious thinking" amongst the population by reviewing their private conversations. You must decide which citizens will be investigated by the mysterious U.P department for treason. Nobody, not even you, know what the U.P department is. You only know that those investigated by them dissapear. IF you choose to flag the true `has_secret` conversations as false, a new conversation line will open on day 7. This will be an undercover agent trying to investigate you for collaborating with the rebels. Answer his messages wrong, and you too will be investigated by the U.P department and the game will end. Answer the questions right, and his suspicion of you will fade. On day 8, if the game has not ended and you answered his questions right,  you get a normal day of work where ever conversation is actually that of the agent that investigated you. This way, you find out where and what the U.P department is. At the end of day 8, you get a choice if you want to communicate the information to the rebels. If you say yes, game ends with the "good ending". If you say no, you are informed all of the rebels have been caught and executed by the U.P department and the "bad ending" comes in.

## Key changes from original narrative

The U.P department is now the main bad guy.
Extra days with some extra conversations based on your choices.
Find out what's U.P?
Good and bad endings depending on choice. 


## Technical Architecture

### Core Components

**Main Game Loop** (`main()` at line 1249)
- 6 to 8-day campaign structure with 6 conversations per day
- Special conversations (IDs 1-6) appear on specific days and unlock follow-up content
- Tracking system monitors if player correctly flagged conversations 1, 2, and 3 to unlock follow-ups 4, 5, and 6 respectively on days 4, 5, and 6


**Conversation Data Structure** (`CONVERSATIONS` list starting at line 118)
- Each conversation has: `id`, `participants`, `messages`, `has_secret`, `secret`
- Three categories: GUILTY (actual crimes), INNOCENT (normal chats), FALSE POSITIVES (suspicious-sounding but innocent)
- 42 total conversations with diverse scenarios

**Skippable Animation System** (`SkippableAnimation` class at line 88)
- Context manager pattern for all timed animations and text displays
- Press 'S' key to skip any animation
- Thread-safe with `animation_lock` for concurrent animation handling
- All display functions (`slow_print`, `blink_eye`, `scanning_animation`, etc.) use this system

**Cross-Platform Input Handling** (`KeyboardHandler` class at line 33)
- Windows: Uses `msvcrt` for keyboard detection
- Unix/Linux/Mac: Uses `termios` and `tty` for raw input
- Non-blocking key detection for skip functionality
- Automatic cleanup of terminal state

**Sound System** (lines 835-1030)
- Optional pygame-based audio (gracefully degrades if pygame unavailable)
- Procedurally generated sounds: menu music, ambient surveillance station sound, typing effects
- Uses array-based wave generation with mathematical functions for different frequencies

### Display Architecture

**Terminal Rendering**
- Auto-centering for all content based on terminal width
- Fixed width design: `TERM_WIDTH = 100`, `CONTENT_WIDTH = 96`
- Bordered display using `#` characters for framing
- ASCII art for title screen and "watching eye" animations

**Animation Functions**
- `slow_print()`: Typewriter effect with optional typing sounds
- `blink_eye()`: Eye opening/closing animation for transitions
- `scanning_animation()`: Progress bar simulation
- `display_conversation()`: Message-by-message reveal with typing effect
- All animations skippable with S key via `SkippableAnimation` wrapper

### Game Flow

1. **Main Menu** → Display title, play looping menu music, show intro text
2. **6-Day Loop**:
   - Day intro screen
   - 6 conversations per day (special convs guaranteed on specific days)
   - Player judgment: Flag (suspicious) or Clear (innocent)
   - Scanning animation + judgment recording
   - Daily report at end of shift
3. **Final Evaluation** → Performance summary based on total score

## Development Commands

### Running the Game
```bash
python Nothing_to_hide.py
```

### Building Executable (PyInstaller)
```bash
pyinstaller NothingToHide.spec
```
The spec file is configured for single-file executable output with console mode enabled.

### Dependencies
- **Required**: Python 3.x with standard library
- **Optional**: `pygame` for sound effects (game runs without it)
- **Windows-specific**: `msvcrt` (standard library)
- **Unix-specific**: `termios`, `tty` (standard library)

Install pygame:
```bash
pip install pygame
# or
sudo apt install python3-pygame
```

## Key Implementation Details

### Platform-Specific Code
- OS detection: `os.name == 'nt'` for Windows
- Keyboard input handling has separate code paths for Windows (msvcrt) vs Unix (termios)
- Screen clearing: `cls` on Windows, `clear` on Unix

### Special Conversation Logic
The game has a consequence system where correctly flagging conversations 1, 2, and 3 unlocks follow-up investigations:
- Conv 1 (Alice & Bob - financial fraud) → Conv 4 (their arrest)
- Conv 2 (Marcus & Julia - smuggling) → Conv 5 (their capture)
- Conv 3 (Dr. Chen & Patel - medical fraud) → Conv 6 (license revocation)

This is controlled by the `flagged_correctly` dictionary in the main loop (line 1279).

### Audio Generation
Sound effects are generated programmatically using sine waves, square waves, and noise:
- `create_menu_music()`: 8-second loop with bass pulses, industrial sounds, atmospheric drone
- `create_ambient_sound()`: 6-second loop with electrical hum, beeps, white noise
- `play_typing_sound()`: Short 800Hz burst for keypress simulation

## File Structure

```
NothingToHide/
├── Nothing_to_hide.py      # Main game file (~1400 lines)
├── NothingToHide.spec       # PyInstaller build configuration
├── Audio/                   # Sound effect files (not currently used by code)
├── build/                   # PyInstaller build artifacts
└── dist/                    # Built executables
```

## Important Notes

- The game uses global state for `current_animation` and `keyboard_handler` - these must be properly cleaned up
- Terminal state restoration is critical: always call `keyboard_handler.stop_monitoring()` on exit
- The `KeyboardHandler` manages terminal settings - improper cleanup can leave terminal in raw mode
- Sound is entirely optional - all sound failures are caught and the game continues silently
- Conversations are shuffled daily but special conversations are guaranteed to appear on their designated days