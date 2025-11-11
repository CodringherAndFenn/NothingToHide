# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

"Nothing is U.P" is a terminal-based surveillance state simulator game written in Python. The player acts as a state inspector reviewing intercepted conversations, deciding which citizens to flag as suspicious. Guilty citizens are known to be sent to the U.P department. The game explores themes of privacy, surveillance, and state power through interactive gameplay.

## Narrative Structure (IMPLEMENTED)

"Nothing to Hide - The U.P Department" is a terminal-based surveillance state simulator written in Python. The player acts as a state inspector in a draconic, authoritarian, but dying state, tasked with investigating "rebellious thinking" by reviewing private conversations. The central mystery: Nobody knows what the U.P Department actually is - only that those investigated by them disappear.

### The Twist: **Nothing is U.P**

The core narrative revelation is that the U.P Department **doesn't exist**. It never did. It's a fabrication used by the state to justify extrajudicial killings. There is no facility, no processing, no mysterious department - just execution squads in unmarked vans. The title "Nothing's U.P" is literal: nothing is "up" because there is no actual department.

### Game Flow Based on Player Choices

**DAYS 1-6: Normal Surveillance Work**
- Player reviews 6 conversations per day
- Special conversations 1, 2, 3 (rebel activity) appear on days 1, 2, 3
- Player decides: Flag as TREASONOUS or mark as LOYAL
- If player correctly flags conversations 1, 2, 3: Conversations 4, 5, 6 (U.P agents capturing rebels) appear on days 4, 5, 6
- After Day 6: Game branches based on whether player helped rebels

**PATH A: Player Helped Rebels (didn't flag conversations 1, 2, or 3)**

**DAY 7: Internal Affairs Investigation**
- Undercover agent questions player about their loyalty
- 3 questions with right/wrong answers
- Must get 2/3 correct to pass
- **If Failed**: BAD ENDING - Player gets disappeared by "U.P Department" (realizes at the end there's no department, just execution)
- **If Passed**: Proceed to Day 8

**DAY 8: Truth Reveal**
- 6 conversations with Agent Reeves gradually revealing the truth
- No judgments required - just story progression
- Player learns: U.P Department is fiction, people are simply executed
- The reveal: "Nothing is U.P. Nothing was ever up."

**FINAL CHOICE:**
- [1] SHARE THE TRUTH with rebels → **GOOD ENDING**: Truth spreads, rebellion grows, State's fear weapon is broken
- [2] STAY SILENT → **BAD ENDING**: Rebels captured and executed, player continues working for the State

**PATH B: Player Didn't Help Rebels (flagged all conversations correctly)**
- Standard 6-day ending with performance evaluation
- No Days 7-8, no truth reveal

### Multiple Endings

1. **Good Ending (The Truth Spreads)**: Player shares the truth with rebels, breaking the State's psychological weapon of fear
2. **Bad Ending (Silence)**: Player stays silent, rebels are executed, State endures
3. **Bad Ending (Investigated)**: Player fails Day 7 interrogation, gets disappeared by the non-existent "U.P Department"
4. **Standard Ending**: Player never helped rebels, completes 6-day evaluation 


## Technical Architecture

### Core Components

**Main Game Loop** (`main()` at line 1689)
- 6 to 8-day campaign structure with 6 conversations per day (days 7-8 are conditional)
- Special conversations (IDs 1-6) appear on specific days and unlock follow-up content
- Tracking systems:
  - `flagged_correctly`: Monitors if player correctly flagged conversations 1, 2, 3 to unlock follow-ups 4, 5, 6 on days 4, 5, 6
  - `helped_rebels`: Monitors if player marked conversations 1, 2, 3 as loyal (helping rebels) to trigger Days 7-8
- Branching narrative based on player choices

**Conversation Data Structure** (`CONVERSATIONS` list starting at line 118)
- Each conversation has: `id`, `participants`, `messages`, `has_secret`, `secret`
- Three categories: GUILTY (actual crimes), INNOCENT (normal chats), FALSE POSITIVES (suspicious-sounding but innocent)
- **49 total conversations** including:
  - IDs 1-42: Regular conversations (6 special rebel/UP conversations, 36 mixed regular/innocent/false positives)
  - ID 43: Day 7 agent investigation intro (unused in current flow - questions handled separately)
  - IDs 44-49: Day 8 truth reveal conversations with Agent Reeves

**Ending Functions** (lines 1366-1683)
- `handle_agent_questions()`: Day 7 interrogation system with 3 questions, 2/3 pass threshold
- `display_final_choice()`: Choice between sharing truth or staying silent
- `display_good_ending()`: Truth spreads ending
- `display_bad_ending_silence()`: Stayed silent, rebels executed
- `display_bad_ending_caught()`: Failed interrogation, player disappeared

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
- Bordered TERMINAL display using `#` characters for framing the margins of the terminal
- ASCII art for title screen and "watching eye" animations

**Animation Functions**
- `slow_print()`: Typewriter effect with optional typing sounds
- `blink_eye()`: Eye opening/closing animation for transitions
- `scanning_animation()`: Progress bar simulation
- `display_conversation()`: Message-by-message reveal with typing effect
- All animations skippable with S key via `SkippableAnimation` wrapper

### Game Flow

1. **Main Menu** → Display title, play looping menu music, show intro text
2. **Days 1-6: Surveillance Work**:
   - Day intro screen
   - 6 conversations per day (special convs guaranteed on specific days)
   - Player judgment: Flag as TREASONOUS or mark as LOYAL
   - Scanning animation + judgment recording
   - Daily report at end of shift
3. **Post-Day 6 Branching**:
   - **If player helped rebels** (didn't flag any of conversations 1, 2, or 3):
     - Day 7: Internal Affairs interrogation (3 questions, must pass 2/3)
     - If failed: Bad ending (caught)
     - If passed: Day 8 truth reveal + final choice + good/bad ending
   - **If player didn't help rebels** (flagged conversations correctly):
     - Standard performance evaluation
     - Game ends after 6 days

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

The game has a dual tracking system for player choices:

**Correctly Flagging (lines 1815-1816)**:
- Conv 1 (Alice & Bob - rebel organizers) → Conv 4 (U.P agents discussing their capture)
- Conv 2 (Marcus & Julia - protest organizers) → Conv 5 (U.P agents discussing protest shutdown)
- Conv 3 (Dr. Chen & Patel - discovered U.P secrets) → Conv 6 (U.P agents discussing their processing)
- Controlled by `flagged_correctly` dictionary - unlocks consequences on days 4, 5, 6

**Helping Rebels (lines 1817-1818)**:
- If player marks conversations 1, 2, or 3 as LOYAL when they actually have `has_secret=True`
- This saves those rebels from being captured
- Tracked by `helped_rebels` dictionary
- If ANY rebel conversation was helped → triggers Days 7-8 narrative branch
- Evaluated at line 1834: `player_helped_any_rebels = any(helped_rebels.values())`

**Day 7-8 Special Conversations**:
- Day 7: Uses `handle_agent_questions()` function instead of conversation display
- Day 8: Conversations 44-49 displayed without judgment (just story progression)

### Audio Generation
Sound effects are generated programmatically using sine waves, square waves, and noise:
- `create_menu_music()`: 8-second loop with bass pulses, industrial sounds, atmospheric drone
- `create_ambient_sound()`: 6-second loop with electrical hum, beeps, white noise
- `play_typing_sound()`: Short 800Hz burst for keypress simulation

## File Structure

```
NothingToHide/
├── Nothing_to_hide.py      # Main game file (~1930 lines)
│   ├── Lines 1-82: Imports, globals, keyboard handler
│   ├── Lines 88-112: SkippableAnimation class
│   ├── Lines 118-814: CONVERSATIONS data (49 conversations)
│   ├── Lines 816-1048: ASCII art, sound functions
│   ├── Lines 1050-1332: Display and animation functions
│   ├── Lines 1333-1683: Ending functions (agent questions, choices, endings)
│   └── Lines 1689-1930: Main game loop with branching narrative
├── CLAUDE.md                # This file - development documentation
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