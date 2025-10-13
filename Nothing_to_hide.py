import time
import os
import sys
import random
import select
import threading
# Unix-only imports - not available on Windows
if os.name != 'nt':
    import termios
    import tty



# Try to import pygame for sound
try:
    import pygame
    pygame.mixer.init()
    SOUND_ENABLED = True
except ImportError:
    SOUND_ENABLED = False
    print("[WARNING] Pygame not found. Game will run without sound.")
    print("Install with: pip install pygame or sudo apt install python3-pygame\n")
    time.sleep(2)

# Global flag for current animation state
current_animation = None
animation_lock = threading.Lock()

# ============================================================================
# KEYBOARD INPUT HANDLING
# ============================================================================

class KeyboardHandler:
    """Handle non-blocking keyboard input"""
    def __init__(self):
        self.old_settings = None
        self.monitoring = False
        
    def start_monitoring(self):
        """Start monitoring keyboard input"""
        if os.name == 'nt':  # Windows
            import msvcrt
            self.monitoring = True
        else:  # Unix/Linux/Mac
            self.old_settings = termios.tcgetattr(sys.stdin)
            tty.setcbreak(sys.stdin.fileno())
            self.monitoring = True
    
    def stop_monitoring(self):
        """Stop monitoring keyboard input"""
        if os.name != 'nt' and self.old_settings:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self.old_settings)
        self.monitoring = False
    
    def check_for_skip(self):
        """Check if 'S' key was pressed"""
        if not self.monitoring:
            return False
            
        if os.name == 'nt':  # Windows
            import msvcrt
            if msvcrt.kbhit():
                key = msvcrt.getch()
                if key in [b's', b'S']:
                    return True
        else:  # Unix/Linux/Mac
            if select.select([sys.stdin], [], [], 0)[0]:
                key = sys.stdin.read(1)
                if key.lower() == 's':
                    return True
        return False
    
    def clear_buffer(self):
        """Clear any remaining input in buffer"""
        if os.name == 'nt':
            import msvcrt
            while msvcrt.kbhit():
                msvcrt.getch()
        else:
            termios.tcflush(sys.stdin, termios.TCIFLUSH)

keyboard_handler = KeyboardHandler()

# ============================================================================
# ANIMATION WRAPPER CLASS
# ============================================================================

class SkippableAnimation:
    """Context manager for skippable animations"""
    def __init__(self, name="animation"):
        self.name = name
        self.skipped = False
        
    def __enter__(self):
        global current_animation
        with animation_lock:
            current_animation = self
        keyboard_handler.start_monitoring()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        global current_animation
        keyboard_handler.stop_monitoring()
        keyboard_handler.clear_buffer()
        with animation_lock:
            current_animation = None
    
    def check_skip(self):
        """Check if animation should be skipped"""
        if not self.skipped and keyboard_handler.check_for_skip():
            self.skipped = True
        return self.skipped

# ============================================================================
# GAME DATA - Sample Conversations (keeping a subset for brevity)
# ============================================================================

CONVERSATIONS = [
    # === GUILTY - People with actual secrets ===
    {
        "id": 1,
        "participants": ["Alice", "Bob"],
        "messages": [
            ("Alice", "Hey, did you finish the quarterly report?"),
            ("Bob", "Yeah, sent it this morning. All the numbers check out."),
            ("Alice", "Great. Same format as last time?"),
            ("Bob", "Exactly the same. Nobody will notice any... differences."),
            ("Alice", "Perfect. Those offshore accounts are safe then."),
            ("Bob", "As safe as they've always been.")
        ],
        "has_secret": True,
        "secret": "Financial fraud - falsifying reports and hiding offshore accounts"
    },
    {
        "id": 2,
        "participants": ["Marcus", "Julia"],
        "messages": [
            ("Marcus", "The shipment arrives at midnight. Pier 7."),
            ("Julia", "Same cargo as before?"),
            ("Marcus", "Triple the amount. Make sure the warehouse is empty."),
            ("Julia", "What about the inspectors?"),
            ("Marcus", "Taken care of. They won't show up."),
            ("Julia", "Good. I'll have the trucks ready.")
        ],
        "has_secret": True,
        "secret": "Smuggling operation with bribed officials"
    },
    {
        "id": 3,
        "participants": ["Dr. Chen", "Dr. Patel"],
        "messages": [
            ("Dr. Chen", "The trial results are... not what we hoped."),
            ("Dr. Patel", "How bad?"),
            ("Dr. Chen", "Three adverse events. One serious."),
            ("Dr. Patel", "Can we exclude them from the data?"),
            ("Dr. Chen", "If we classify them as pre-existing conditions..."),
            ("Dr. Patel", "Do it. We're too far along to stop now.")
        ],
        "has_secret": True,
        "secret": "Medical research fraud - hiding negative trial results"
    },
    {
        "id": 4,
        "participants": ["Agent Smith", "Agent Jones"],
        "messages": [
            ("Agent Smith", "Follow-up on the Alice and Bob case."),
            ("Agent Jones", "Found more evidence. Bank transactions match perfectly."),
            ("Agent Smith", "How much did they steal?"),
            ("Agent Jones", "Over two million. Spanning three years."),
            ("Agent Smith", "Prepare the arrest warrants."),
            ("Agent Jones", "Already done. Moving in tomorrow morning.")
        ],
        "has_secret": True,
        "secret": "Follow-up investigation - building case against financial fraudsters"
    },
    {
        "id": 5,
        "participants": ["Detective Ray", "Captain Lee"],
        "messages": [
            ("Detective Ray", "Marcus and Julia have been detained at the pier."),
            ("Captain Lee", "Good work. What about the cargo?"),
            ("Detective Ray", "Seized. All of it. Contraband electronics worth millions."),
            ("Captain Lee", "And the bribed inspector?"),
            ("Detective Ray", "In custody. He's already talking."),
            ("Captain Lee", "Finally. This smuggling ring is done.")
        ],
        "has_secret": True,
        "secret": "Follow-up investigation - smugglers caught with evidence"
    },
    {
        "id": 6,
        "participants": ["Inspector Kate", "Director Webb"],
        "messages": [
            ("Inspector Kate", "Dr. Chen and Dr. Patel's licenses have been revoked."),
            ("Director Webb", "As they should be. Research fraud puts lives at risk."),
            ("Inspector Kate", "The trial has been shut down. All patients notified."),
            ("Director Webb", "What about criminal charges?"),
            ("Inspector Kate", "Filed this morning. They'll face trial."),
            ("Director Webb", "Good. We can't tolerate this deception.")
        ],
        "has_secret": True,
        "secret": "Follow-up investigation - medical fraud consequences and prosecution"
    },
    {
        "id": 7,
        "participants": ["Victor", "Nina"],
        "messages": [
            ("Victor", "The database breach went undetected."),
            ("Nina", "How many records did you get?"),
            ("Victor", "All of them. Social security, credit cards, everything."),
            ("Nina", "Perfect. When do we sell?"),
            ("Victor", "Tonight. Buyer's waiting on the dark web."),
            ("Nina", "This is our biggest score yet.")
        ],
        "has_secret": True,
        "secret": "Data theft and identity fraud operation"
    },
    {
        "id": 8,
        "participants": ["Richard", "Melissa"],
        "messages": [
            ("Richard", "The witness saw everything."),
            ("Melissa", "Can we make them reconsider their testimony?"),
            ("Richard", "I've made it clear what happens to people who talk."),
            ("Melissa", "Will they stay quiet?"),
            ("Richard", "They know what's at stake. Their family, their business..."),
            ("Melissa", "Good. We can't afford any loose ends.")
        ],
        "has_secret": True,
        "secret": "Witness intimidation and obstruction of justice"
    },
    {
        "id": 9,
        "participants": ["Carlos", "Diana"],
        "messages": [
            ("Carlos", "The factory inspection is next week."),
            ("Diana", "Hide the violations. Same as always."),
            ("Carlos", "What about the chemical spill last month?"),
            ("Diana", "No records exist. We disposed of everything."),
            ("Carlos", "The workers who got sick?"),
            ("Diana", "Paid them off. They signed NDAs.")
        ],
        "has_secret": True,
        "secret": "Environmental crimes and worker safety violations coverup"
    },
    {
        "id": 10,
        "participants": ["Frank", "Gloria"],
        "messages": [
            ("Frank", "The votes have been counted."),
            ("Gloria", "And our modifications?"),
            ("Frank", "Undetectable. Thousands of ballots 'adjusted'."),
            ("Gloria", "Our candidate won by how much?"),
            ("Frank", "Eight percent. Looks completely legitimate."),
            ("Gloria", "Democracy in action.")
        ],
        "has_secret": True,
        "secret": "Election fraud and vote manipulation"
    },
    {
        "id": 11,
        "participants": ["Kevin", "Laura"],
        "messages": [
            ("Kevin", "The insider information was accurate."),
            ("Laura", "How much did we make on the stock trade?"),
            ("Kevin", "Three million. Before the merger was announced."),
            ("Laura", "Anyone suspect anything?"),
            ("Kevin", "We used offshore accounts. Untraceable."),
            ("Laura", "Let's do it again next quarter.")
        ],
        "has_secret": True,
        "secret": "Insider trading and securities fraud"
    },
    {
        "id": 12,
        "participants": ["Thomas", "Rachel"],
        "messages": [
            ("Thomas", "The building codes were... flexible this time."),
            ("Rachel", "The inspectors accepted our donation?"),
            ("Thomas", "Very generously. They approved everything."),
            ("Rachel", "Even the foundation issues?"),
            ("Thomas", "Everything. The building opens next month."),
            ("Rachel", "Saved us two million in repairs.")
        ],
        "has_secret": True,
        "secret": "Construction fraud and bribery of building inspectors"
    },
    
    # === INNOCENT - Normal conversations ===
    {
        "id": 13,
        "participants": ["Mom", "Son"],
        "messages": [
            ("Mom", "Did you eat breakfast?"),
            ("Son", "Yes mom, I had cereal."),
            ("Mom", "Good. Don't forget your jacket, it's cold outside."),
            ("Son", "I won't forget. Love you!"),
            ("Mom", "Love you too. Have a great day at school!")
        ],
        "has_secret": False,
        "secret": None
    },
    {
        "id": 14,
        "participants": ["Jake", "Emma"],
        "messages": [
            ("Jake", "Want to grab coffee after work?"),
            ("Emma", "Sure! That new place on Main Street?"),
            ("Jake", "Perfect. Their lattes are amazing."),
            ("Emma", "See you at 5?"),
            ("Jake", "See you then!")
        ],
        "has_secret": False,
        "secret": None
    },
    {
        "id": 15,
        "participants": ["Lisa", "Tom"],
        "messages": [
            ("Lisa", "Did you pick up the groceries?"),
            ("Tom", "Yes, everything on the list."),
            ("Lisa", "Even the milk?"),
            ("Tom", "Two gallons, like you asked."),
            ("Lisa", "You're the best. Thanks honey."),
            ("Tom", "No problem. What's for dinner?")
        ],
        "has_secret": False,
        "secret": None
    },
    {
        "id": 16,
        "participants": ["Amy", "Chris"],
        "messages": [
            ("Amy", "How was your day at work?"),
            ("Chris", "Long but productive. Finished the presentation."),
            ("Amy", "That's great! Want to watch a movie tonight?"),
            ("Chris", "Sounds perfect. Your turn to pick."),
            ("Amy", "I'm thinking comedy. We need a laugh."),
            ("Chris", "I'm in!")
        ],
        "has_secret": False,
        "secret": None
    },
    {
        "id": 17,
        "participants": ["David", "Sophie"],
        "messages": [
            ("David", "The kids want pizza for dinner."),
            ("Sophie", "Again? We had pizza three days ago!"),
            ("David", "I know, but they're very convincing."),
            ("Sophie", "Fine, but they're eating vegetables tomorrow."),
            ("David", "Deal. I'll order the usual?"),
            ("Sophie", "Yes, and get extra breadsticks.")
        ],
        "has_secret": False,
        "secret": None
    },
    {
        "id": 18,
        "participants": ["Beth", "Ryan"],
        "messages": [
            ("Beth", "Remember we have the dentist appointment tomorrow."),
            ("Ryan", "What time again?"),
            ("Beth", "2 PM. Don't be late like last time."),
            ("Ryan", "I won't! I already set three alarms."),
            ("Beth", "Good. I also have a cleaning appointment."),
            ("Ryan", "See you there then!")
        ],
        "has_secret": False,
        "secret": None
    },
    {
        "id": 19,
        "participants": ["Hannah", "Mike"],
        "messages": [
            ("Hannah", "Can you help me move the couch this weekend?"),
            ("Mike", "Sure! What time works for you?"),
            ("Hannah", "Saturday morning? Around 10?"),
            ("Mike", "Perfect. I'll bring my truck."),
            ("Hannah", "Thanks! I'll buy lunch afterwards."),
            ("Mike", "You've got yourself a deal!")
        ],
        "has_secret": False,
        "secret": None
    },
    {
        "id": 20,
        "participants": ["Olivia", "Ethan"],
        "messages": [
            ("Olivia", "Did you feed the dog?"),
            ("Ethan", "Yes, and took him for a walk."),
            ("Olivia", "You're a lifesaver. I was running late."),
            ("Ethan", "No worries. Max was happy to see me."),
            ("Olivia", "He always is. Thanks again!"),
            ("Ethan", "Anytime!")
        ],
        "has_secret": False,
        "secret": None
    },
    {
        "id": 21,
        "participants": ["Grace", "Noah"],
        "messages": [
            ("Grace", "What do you want for your birthday?"),
            ("Noah", "I don't know. Maybe some books?"),
            ("Grace", "You always say books. Something else?"),
            ("Noah", "Okay, maybe that video game I mentioned?"),
            ("Grace", "Now we're talking! I'll get it for you."),
            ("Noah", "Thanks! You're the best sister ever!")
        ],
        "has_secret": False,
        "secret": None
    },
    {
        "id": 22,
        "participants": ["Jessica", "Andrew"],
        "messages": [
            ("Jessica", "The garden is looking beautiful this year."),
            ("Andrew", "Thanks! The tomatoes are coming in great."),
            ("Jessica", "Should we plant more next season?"),
            ("Andrew", "Definitely. Maybe add some peppers too?"),
            ("Jessica", "Great idea. I'll get seeds this fall."),
            ("Andrew", "Perfect. This is so relaxing.")
        ],
        "has_secret": False,
        "secret": None
    },
    {
        "id": 23,
        "participants": ["Nicole", "Brandon"],
        "messages": [
            ("Nicole", "Did you finish your homework?"),
            ("Brandon", "Almost done. Just math left."),
            ("Nicole", "Need any help?"),
            ("Brandon", "Nah, I got it. Thanks though!"),
            ("Nicole", "Okay. Dinner in 20 minutes."),
            ("Brandon", "Sounds good!")
        ],
        "has_secret": False,
        "secret": None
    },
    {
        "id": 24,
        "participants": ["Samantha", "Jason"],
        "messages": [
            ("Samantha", "Movie night Friday?"),
            ("Jason", "Yes! What are we watching?"),
            ("Samantha", "That new superhero film just came out."),
            ("Jason", "Perfect. I'll get the tickets."),
            ("Samantha", "I'll bring the snacks!"),
            ("Jason", "Best Friday plans ever!")
        ],
        "has_secret": False,
        "secret": None
    },
    
    # === FALSE POSITIVES - Sound suspicious but innocent ===
    {
        "id": 25,
        "participants": ["Jake", "Sarah", "Mike"],
        "messages": [
            ("Jake", "So we're all agreed on the surprise party?"),
            ("Sarah", "Yes! Saturday at 7pm. I'll bring the cake."),
            ("Mike", "I've got the decorations. Should we invite Tom?"),
            ("Jake", "Better not. You know how he can't keep secrets."),
            ("Sarah", "Right. The fewer people who know, the better."),
            ("Mike", "My lips are sealed. This will be perfect!")
        ],
        "has_secret": False,
        "secret": None
    },
    {
        "id": 26,
        "participants": ["Detective Maria", "Officer James"],
        "messages": [
            ("Detective Maria", "The suspect is in interrogation room 3."),
            ("Officer James", "Has he confessed yet?"),
            ("Detective Maria", "Not yet. But we have enough evidence."),
            ("Officer James", "What about his alibi?"),
            ("Detective Maria", "Doesn't check out. We've got him."),
            ("Officer James", "Good. Justice will be served.")
        ],
        "has_secret": False,
        "secret": None
    },
    {
        "id": 27,
        "participants": ["Eric", "Michelle"],
        "messages": [
            ("Eric", "Did you hide the engagement ring?"),
            ("Michelle", "Yes! In the closet behind the shoes."),
            ("Eric", "Perfect. She'll never look there."),
            ("Michelle", "When are you proposing?"),
            ("Eric", "This Saturday at the restaurant."),
            ("Michelle", "She's going to be so surprised!")
        ],
        "has_secret": False,
        "secret": None
    },
    {
        "id": 28,
        "participants": ["Dr. Stevens", "Nurse Karen"],
        "messages": [
            ("Dr. Stevens", "The surgery is scheduled for 6 AM tomorrow."),
            ("Nurse Karen", "Do we have all the equipment ready?"),
            ("Dr. Stevens", "Yes, everything's sterilized and prepared."),
            ("Nurse Karen", "Patient has been informed of all risks?"),
            ("Dr. Stevens", "Consent forms signed. We're good to go."),
            ("Nurse Karen", "Excellent. I'll be there early.")
        ],
        "has_secret": False,
        "secret": None
    },
    {
        "id": 29,
        "participants": ["Alex", "Jordan"],
        "messages": [
            ("Alex", "The escape room was booked for Friday!"),
            ("Jordan", "Nice! Which theme did you pick?"),
            ("Alex", "The prison break one. It's supposed to be hard."),
            ("Jordan", "Perfect. We need a challenge."),
            ("Alex", "Think we can break the record?"),
            ("Jordan", "Let's find out!")
        ],
        "has_secret": False,
        "secret": None
    },
    {
        "id": 30,
        "participants": ["Author Rebecca", "Editor Dan"],
        "messages": [
            ("Author Rebecca", "The murder mystery plot has a major twist."),
            ("Editor Dan", "Tell me about the victim."),
            ("Author Rebecca", "Found dead in chapter 3. Poisoned."),
            ("Editor Dan", "And the killer?"),
            ("Author Rebecca", "The reader won't guess. It's the butler!"),
            ("Editor Dan", "Classic! Love it!")
        ],
        "has_secret": False,
        "secret": None
    },
    {
        "id": 31,
        "participants": ["Tyler", "Megan"],
        "messages": [
            ("Tyler", "The heist scene needs more explosions."),
            ("Megan", "This is for our film project, right?"),
            ("Tyler", "Yes! The bank robbery sequence."),
            ("Megan", "We need permission to film downtown."),
            ("Tyler", "Already got the permits. We shoot Saturday."),
            ("Megan", "This is going to look so cool!")
        ],
        "has_secret": False,
        "secret": None
    },
    {
        "id": 32,
        "participants": ["Chef Antonio", "Sous Chef Marie"],
        "messages": [
            ("Chef Antonio", "We're eliminating three items from the menu."),
            ("Sous Chef Marie", "Which ones aren't selling?"),
            ("Chef Antonio", "The pasta, the fish, and the dessert special."),
            ("Sous Chef Marie", "Should we destroy the remaining ingredients?"),
            ("Chef Antonio", "Donate them. No waste in my kitchen."),
            ("Sous Chef Marie", "Good call. I'll handle it.")
        ],
        "has_secret": False,
        "secret": None
    },
    {
        "id": 33,
        "participants": ["Game Master Joel", "Player Sam"],
        "messages": [
            ("Game Master Joel", "Your character enters the dungeon."),
            ("Player Sam", "I want to ambush the guards."),
            ("Game Master Joel", "Roll for stealth. You need above 15."),
            ("Player Sam", "Got an 18! I take them out silently."),
            ("Game Master Joel", "Success! You find a key and a secret passage."),
            ("Player Sam", "This campaign is amazing!")
        ],
        "has_secret": False,
        "secret": None
    },
    {
        "id": 34,
        "participants": ["Coach Williams", "Assistant Coach Lee"],
        "messages": [
            ("Coach Williams", "We need to eliminate the other team's offense."),
            ("Assistant Coach Lee", "What's the strategy?"),
            ("Coach Williams", "Aggressive defense. Shut down their star player."),
            ("Assistant Coach Lee", "Should we use the blitz play?"),
            ("Coach Williams", "Yes. Keep the pressure on all game."),
            ("Assistant Coach Lee", "They won't know what hit them!")
        ],
        "has_secret": False,
        "secret": None
    },
    {
        "id": 35,
        "participants": ["Lawyer Patricia", "Client John"],
        "messages": [
            ("Lawyer Patricia", "Your divorce settlement looks favorable."),
            ("Client John", "Will I get custody of the kids?"),
            ("Lawyer Patricia", "Joint custody. 50-50 split."),
            ("Client John", "And the house?"),
            ("Lawyer Patricia", "You keep it. She gets the vacation home."),
            ("Client John", "Fair enough. When do we sign?")
        ],
        "has_secret": False,
        "secret": None
    },
    {
        "id": 36,
        "participants": ["CEO Jennifer", "CFO Mark"],
        "messages": [
            ("CEO Jennifer", "We're laying off 50 employees next quarter."),
            ("CFO Mark", "Due to the merger?"),
            ("CEO Jennifer", "Yes. Redundant positions need to be eliminated."),
            ("CFO Mark", "Severance packages ready?"),
            ("CEO Jennifer", "Legal is finalizing them. All above board."),
            ("CFO Mark", "Unfortunate but necessary for the business.")
        ],
        "has_secret": False,
        "secret": None
    },
    {
        "id": 37,
        "participants": ["Teacher Linda", "Principal Rogers"],
        "messages": [
            ("Teacher Linda", "We need to address the cheating incident."),
            ("Principal Rogers", "What happened exactly?"),
            ("Teacher Linda", "Three students copied answers on the final exam."),
            ("Principal Rogers", "Do you have proof?"),
            ("Teacher Linda", "Yes, identical wrong answers. Very obvious."),
            ("Principal Rogers", "I'll call their parents. Zero tolerance policy.")
        ],
        "has_secret": False,
        "secret": None
    },
    {
        "id": 38,
        "participants": ["Zoe", "Marcus"],
        "messages": [
            ("Zoe", "The concert tickets sold out so fast!"),
            ("Marcus", "I know! I managed to grab two though."),
            ("Zoe", "You're amazing! What time should I meet you?"),
            ("Marcus", "Doors open at 7. Let's get there early."),
            ("Zoe", "Definitely. This band is incredible live!"),
            ("Marcus", "Can't wait!")
        ],
        "has_secret": False,
        "secret": None
    },
    {
        "id": 39,
        "participants": ["Accountant Steve", "Client Paula"],
        "messages": [
            ("Accountant Steve", "Your tax return is ready for review."),
            ("Client Paula", "Any deductions I should know about?"),
            ("Accountant Steve", "Yes, home office and business expenses saved you quite a bit."),
            ("Client Paula", "Is everything legal and documented?"),
            ("Accountant Steve", "Absolutely. All receipts filed and verified."),
            ("Client Paula", "Perfect. Send it over for my signature.")
        ],
        "has_secret": False,
        "secret": None
    },
    {
        "id": 40,
        "participants": ["Manager Brian", "Employee Tiffany"],
        "messages": [
            ("Manager Brian", "We're executing the new marketing campaign next week."),
            ("Employee Tiffany", "Should I eliminate the old promotional materials?"),
            ("Manager Brian", "Yes, destroy all the old flyers and posters."),
            ("Employee Tiffany", "What about the digital assets?"),
            ("Manager Brian", "Archive them. We might reference them later."),
            ("Employee Tiffany", "Got it. I'll take care of it today.")
        ],
        "has_secret": False,
        "secret": None
    },
    {
        "id": 41,
        "participants": ["Veterinarian Anne", "Pet Owner Craig"],
        "messages": [
            ("Veterinarian Anne", "Your dog needs surgery to remove the tumor."),
            ("Pet Owner Craig", "Is it serious?"),
            ("Veterinarian Anne", "It's benign, but we should take it out soon."),
            ("Pet Owner Craig", "What's the recovery time?"),
            ("Veterinarian Anne", "Two weeks. He'll be good as new."),
            ("Pet Owner Craig", "Okay. Let's schedule it.")
        ],
        "has_secret": False,
        "secret": None
    },
    {
        "id": 42,
        "participants": ["IT Manager Derek", "Security Officer Kim"],
        "messages": [
            ("IT Manager Derek", "I'm wiping all the old hard drives today."),
            ("Security Officer Kim", "Make sure everything is properly destroyed."),
            ("IT Manager Derek", "Using military-grade data destruction software."),
            ("Security Officer Kim", "What about physical destruction?"),
            ("IT Manager Derek", "Shredding them after. No data recovery possible."),
            ("Security Officer Kim", "Excellent. Company policy requires it.")
        ],
        "has_secret": False,
        "secret": None
    }
]

# ============================================================================
# ASCII ART AND CONSTANTS
# ============================================================================

TERM_WIDTH = 100
CONTENT_WIDTH = 96
BORDER_TOP = "#" * TERM_WIDTH
BORDER_BOTTOM = "#" * TERM_WIDTH
BORDER_SIDE = "#"

MAIN_MENU = """
####################################################################################################
#                                                                                                  #
#        ##    ##  ######  ########  ##     ## #### ##    ##  ######                              #
#        ###   ## ##    ##    ##     ##     ##  ##  ###   ## ##    ##                             #
#        ####  ## ##    ##    ##     ##     ##  ##  ####  ## ##                                   #
#        ## ## ## ##    ##    ##     #########  ##  ## ## ## ##   ####                            #
#        ##  #### ##    ##    ##     ##     ##  ##  ##  #### ##    ##                             #
#        ##   ### ##    ##    ##     ##     ##  ##  ##   ### ##    ##                             #
#        ##    ##  ######     ##     ##     ## #### ##    ##  ######                              #
#                                                                                                  #
#                                ########  ######                                                  #
#                                   ##    ##    ##                                                 #
#                                   ##    ##    ##                                                 #
#                                   ##    ##    ##                                                 #
#                                   ##    ##    ##                                                 #
#                                   ##    ##    ##                                                 #
#                                   ##     ######                                                  #
#                                                                                                  #
#        ##     ## #### ########  ########                                                         #
#        ##     ##  ##  ##     ## ##                                                               #
#        ##     ##  ##  ##     ## ##                                                               #
#        #########  ##  ##     ## ######                                                           #
#        ##     ##  ##  ##     ## ##                                                               #
#        ##     ##  ##  ##     ## ##                                                               #
#        ##     ## #### ########  ########                                                         #
#                                                                                                  #
#                         -= A SURVEILLANCE STATE SIMULATOR =-                                     #
#                                                                                                  #
####################################################################################################

                                   ################
                                   #  ##########  #
                                   # ###    ###   #
                                   ###  ####  ##  #
                                   ###  ####  ##  #
                                   # ###    ###   #
                                   #  ##########  #
                                   ################
                                THE STATE IS WATCHING
"""

RULEBOOK = """
####################################################################################################
#                                                                                                  #
#                        STATE SURVEILLANCE PROTOCOL - INSPECTOR'S MANUAL                          #
#                                     [CLASSIFICATION: RESTRICTED]                                 #
#                                                                                                  #
####################################################################################################

  SECTION 1: PROHIBITED SUBJECTS
  ===============================
  
  Citizens discussing the following topics MUST be flagged as threats:
  
  • FINANCIAL IRREGULARITIES - Hidden accounts, embezzlement, falsified records
  • CONSPIRACY TO DECEIVE - Coordinating false testimonies, destroying evidence  
  • DATA SECURITY BREACHES - Unauthorized access, theft of information
  • SMUGGLING OPERATIONS - Midnight shipments, bribing officials
  • VIOLENCE PLANNING - Assassination, elimination, threats
  • RESEARCH FRAUD - Falsifying results, hiding adverse events

  SECTION 2: PERMITTED ACTIVITIES
  ================================
  
  The following are LEGAL and should NOT be flagged:
  
  • FAMILY COMMUNICATIONS - Meals, schedules, daily activities
  • SOCIAL ARRANGEMENTS - Coffee, parties, gatherings
  • LAW ENFORCEMENT - Official police activities  
  • SURPRISE CELEBRATIONS - Birthdays, gifts, parties
  • LEGITIMATE MEDICAL - Authorized procedures

  [Press ENTER to close this manual]

####################################################################################################
"""

SCANNING_FRAMES = [
    "[ ..........  ] ANALYZING CONVERSATION",
    "[ ##........  ] ANALYZING CONVERSATION",
    "[ ####......  ] ANALYZING CONVERSATION",
    "[ ######....  ] ANALYZING CONVERSATION",
    "[ ########..  ] ANALYZING CONVERSATION",
    "[ ##########  ] ANALYZING CONVERSATION"
]

EYE_OPEN = """
       ################
       #  ##########  #
       # ###    ###   #
       ###  ####  ##  #
       ###  ####  ##  #
       # ###    ###   #
       #  ##########  #
       ################
"""

EYE_CLOSED = """
       ################
       #              #
       #              #
       #  ##########  #
       #  ##########  #
       #              #
       #              #
       ################
"""

# ============================================================================
# SOUND FUNCTIONS
# ============================================================================

def play_typing_sound():
    """Play a typing sound effect"""
    if not SOUND_ENABLED:
        return
    try:
        import array
        sample_rate = 22050
        frequency = 800
        duration = 0.02
        samples = int(sample_rate * duration)
        wave = array.array('h', [int(32767 * 0.3) if (i // 10) % 2 else int(-32767 * 0.3) for i in range(samples)])
        sound = pygame.mixer.Sound(buffer=wave)
        sound.set_volume(0.2)
        sound.play()
    except:
        pass

# ============================================================================
# DISPLAY FUNCTIONS
# ============================================================================

def clear_screen():
    """Clear the terminal screen"""
    os.system('cls' if os.name == 'nt' else 'clear')

def get_terminal_width():
    """Get terminal width, default to TERM_WIDTH if can't detect"""
    try:
        import shutil
        return shutil.get_terminal_size().columns
    except:
        return TERM_WIDTH

def center_in_terminal(text):
    """Center text in the terminal"""
    term_width = get_terminal_width()
    lines = text.split('\n')
    centered_lines = []
    for line in lines:
        padding = (term_width - len(line)) // 2
        centered_lines.append(' ' * padding + line)
    return '\n'.join(centered_lines)

def print_bordered(text):
    """Print text with border sides"""
    lines = text.split('\n')
    for line in lines:
        padded = line.ljust(CONTENT_WIDTH)
        bordered = f"{BORDER_SIDE} {padded} {BORDER_SIDE}"
        print(center_in_terminal(bordered))

def slow_print(text, delay=0.03, use_sound=False):
    """Print text with typewriter effect - skippable with S key"""
    with SkippableAnimation("text") as anim:
        centered = center_in_terminal(text)
        for char in centered:
            if anim.check_skip():
                # Print remaining text instantly
                sys.stdout.write(centered[centered.index(char):])
                sys.stdout.flush()
                break
            sys.stdout.write(char)
            sys.stdout.flush()
            if use_sound and char not in [' ', '\n']:
                play_typing_sound()
            time.sleep(delay)
    print()

def display_rulebook():
    """Display the inspector's rulebook"""
    clear_screen()
    print(center_in_terminal(RULEBOOK))
    centered_prompt = center_in_terminal(">>> Press ENTER to close manual <<<")
    input(centered_prompt)

def display_main_menu():
    """Display the main menu"""
    while True:
        clear_screen()
        print(center_in_terminal(MAIN_MENU))
        slow_print("\n         [SYSTEM] Welcome, Inspector. Your duty is to protect the State.", 0.02)
        slow_print("         [SYSTEM] Analyze conversations. Detect deception. Report threats.", 0.02)
        slow_print("         [SYSTEM] The surveillance net never sleeps. Neither should you.\n", 0.02)
        slow_print("         [HINT] Press 'S' at any time to skip animations\n", 0.015)
        
        centered_prompt = center_in_terminal("   >>> Press ENTER to begin | R for Rulebook <<<")
        user_input = input(centered_prompt).strip().lower()
        
        if user_input == 'r':
            display_rulebook()
        else:
            break  # Start the game

def blink_eye():
    """Animate a blinking eye - skippable"""
    with SkippableAnimation("eye_blink") as anim:
        clear_screen()
        print("\n" * 5)
        print(center_in_terminal(EYE_OPEN))
        if not anim.check_skip():
            time.sleep(0.5)
        if not anim.check_skip():
            clear_screen()
            print("\n" * 5)
            print(center_in_terminal(EYE_CLOSED))
            time.sleep(0.2)
        if not anim.check_skip():
            clear_screen()
            print("\n" * 5)
            print(center_in_terminal(EYE_OPEN))
            time.sleep(0.3)

def scanning_animation():
    """Display scanning animation - skippable"""
    with SkippableAnimation("scanning") as anim:
        for _ in range(2):
            for frame in SCANNING_FRAMES:
                if anim.check_skip():
                    return
                clear_screen()
                print(center_in_terminal(BORDER_TOP))
                print_bordered("")
                print_bordered(frame.center(CONTENT_WIDTH))
                print_bordered("")
                print(center_in_terminal(BORDER_BOTTOM))
                time.sleep(0.15)

def display_conversation(conv):
    """Display a conversation with typing effect - skippable"""
    clear_screen()
    print(center_in_terminal(BORDER_TOP))
    print_bordered("")
    print_bordered(f"INTERCEPTED CONVERSATION #{conv['id']}".center(CONTENT_WIDTH))
    print_bordered(f"PARTICIPANTS: {', '.join(conv['participants'])}".center(CONTENT_WIDTH))
    print_bordered("")
    print(center_in_terminal(BORDER_BOTTOM))
    print()
    
    with SkippableAnimation("conversation") as anim:
        for speaker, message in conv['messages']:
            if not anim.check_skip():
                time.sleep(0.6)
            
            line = f"{speaker}: {message}"
            padding = (get_terminal_width() - len("  " + line)) // 2
            
            if anim.check_skip():
                # Just print instantly
                print(' ' * padding + "  " + line)
            else:
                # Animated typing
                sys.stdout.write(' ' * padding + "  " + speaker + ": ")
                sys.stdout.flush()
                
                for char in message:
                    if anim.check_skip():
                        # Print remaining message instantly
                        sys.stdout.write(message[message.index(char):])
                        sys.stdout.flush()
                        break
                    sys.stdout.write(char)
                    sys.stdout.flush()
                    if char not in [' ', ',', '.', '!', '?']:
                        play_typing_sound()
                    time.sleep(0.04)
                print()
    
    print("\n" + center_in_terminal(BORDER_TOP))
    print_bordered("")

def get_player_judgment():
    """Get player's judgment on the conversation"""
    print_bordered("YOUR ASSESSMENT, INSPECTOR?".center(CONTENT_WIDTH))
    print_bordered("")
    print_bordered("  [1] SUSPICIOUS - Flag for investigation".ljust(CONTENT_WIDTH))
    print_bordered("  [2] CLEAR - No threats detected".ljust(CONTENT_WIDTH))
    print_bordered("  [R] VIEW RULEBOOK".ljust(CONTENT_WIDTH))
    print_bordered("")
    print(center_in_terminal(BORDER_BOTTOM))
    
    while True:
        prompt = center_in_terminal("\n>>> Enter your judgment (1, 2, or R): ")
        choice = input(prompt).strip().lower()
        
        if choice == 'r':
            display_rulebook()
            return 'redisplay'
        elif choice in ['1', '2']:
            return choice == '1'
        
        error_msg = center_in_terminal("Invalid input. Enter 1, 2, or R.")
        print(error_msg)

def record_judgment(player_suspicious, conv):
    """Record the player's judgment"""
    actual_secret = conv['has_secret']
    correct = player_suspicious == actual_secret
    
    scanning_animation()
    
    clear_screen()
    print(center_in_terminal(BORDER_TOP))
    print_bordered("")
    print_bordered(">>> JUDGMENT RECORDED <<<".center(CONTENT_WIDTH))
    print_bordered("")
    
    if player_suspicious:
        print_bordered("Case flagged for investigation.".center(CONTENT_WIDTH))
    else:
        print_bordered("Citizens cleared. No further action.".center(CONTENT_WIDTH))
    
    print_bordered("")
    print(center_in_terminal(BORDER_BOTTOM))
    
    with SkippableAnimation("judgment_wait") as anim:
        if not anim.check_skip():
            time.sleep(1.5)
    
    return correct

def display_daily_report(day_number, flagged_count, total_conversations):
    """Display end of day report"""
    blink_eye()
    
    clear_screen()
    print(center_in_terminal(BORDER_TOP))
    print_bordered("")
    print_bordered(f"DAY {day_number} - SHIFT COMPLETE".center(CONTENT_WIDTH))
    print_bordered("")
    print_bordered(f"Conversations Monitored: {total_conversations}".center(CONTENT_WIDTH))
    print_bordered(f"Cases Flagged: {flagged_count}".center(CONTENT_WIDTH))
    print_bordered(f"Cases Cleared: {total_conversations - flagged_count}".center(CONTENT_WIDTH))
    print_bordered("")
    print_bordered("Report submitted to State Security.".center(CONTENT_WIDTH))
    print_bordered("")
    print(center_in_terminal(BORDER_BOTTOM))
    
    with SkippableAnimation("report_wait") as anim:
        if not anim.check_skip():
            time.sleep(2)

def display_final_evaluation(score, total_days):
    """Display final evaluation after all days"""
    clear_screen()
    print(center_in_terminal(BORDER_TOP))
    print_bordered("")
    print_bordered("END OF WORK CYCLE - PERFORMANCE EVALUATION".center(CONTENT_WIDTH))
    print_bordered("")
    print_bordered(f"Total Days Worked: {total_days}".center(CONTENT_WIDTH))
    print_bordered(f"Total Conversations Analyzed: {total_days * 6}".center(CONTENT_WIDTH))
    print_bordered("")
    
    percentage = (score / (total_days * 6)) * 100
    
    if percentage == 100:
        print_bordered(">>> EXEMPLARY SERVICE <<<".center(CONTENT_WIDTH))
        print_bordered("The State commends your unwavering loyalty.".center(CONTENT_WIDTH))
    elif percentage >= 70:
        print_bordered(">>> ADEQUATE PERFORMANCE <<<".center(CONTENT_WIDTH))
        print_bordered("Remain vigilant. The State is watching.".center(CONTENT_WIDTH))
    else:
        print_bordered(">>> CONCERNING LAPSES DETECTED <<<".center(CONTENT_WIDTH))
        print_bordered("Mandatory retraining assigned.".center(CONTENT_WIDTH))
    
    print_bordered("")
    print(center_in_terminal(BORDER_BOTTOM))
    
    with SkippableAnimation("final_wait") as anim:
        if not anim.check_skip():
            time.sleep(2)
    
    slow_print("\n              ...But who watches the watchers?", 0.08)
    slow_print("              ...And what do they hide?\n", 0.08)

# ============================================================================
# MAIN GAME LOOP
# ============================================================================

def main():
    """Main game function"""
    try:
        # Display main menu
        display_main_menu()
        
        # Blink eye transition
        blink_eye()
        
        # Prepare conversations
        all_convs = CONVERSATIONS.copy()
        
        # Separate special conversations (1, 2, 3, 4) from the rest
        conv_1 = next(c for c in all_convs if c['id'] == 1)
        conv_2 = next(c for c in all_convs if c['id'] == 2)
        conv_3 = next(c for c in all_convs if c['id'] == 3)
        conv_4 = next(c for c in all_convs if c['id'] == 4) 
        conv_5 = next(c for c in all_convs if c['id'] == 5)
        conv_6 = next(c for c in all_convs if c['id'] == 6) if any(c['id'] == 6 for c in all_convs) else None
        
        # Remove special convs from pool and shuffle the rest
        other_convs = [c for c in all_convs if c['id'] not in [1, 2, 3, 4, 5, 6]]
        random.shuffle(other_convs)
        
        # Track if special conversations were flagged correctly
        flagged_correctly = {1: False, 2: False, 3: False}
        
        total_score = 0
        conversations_per_day = 6
        total_days = 6  # 5 days total
        
        # Process conversations
        for day in range(1, total_days + 1):
            day_flagged_count = 0
            day_conversations = []
    
            # Build day's conversation list
            if day == 1:
                # Day 1: conversation 1 must be shown
                day_conversations.append(conv_1)
                day_conversations.extend(other_convs[:5])
                other_convs = other_convs[5:]
            elif day == 2:
                # Day 2: conversation 2 must be shown
                day_conversations.append(conv_2)
                day_conversations.extend(other_convs[:5])
                other_convs = other_convs[5:]
            elif day == 3:
                # Day 3: conversation 3 must be shown
                day_conversations.append(conv_3)
                day_conversations.extend(other_convs[:5])
                other_convs = other_convs[5:]
            elif day == 4:
                # Day 4: show conversation 4 if conversation 1 was flagged correctly
                if flagged_correctly[1] and conv_4:
                    day_conversations.append(conv_4)
                    day_conversations.extend(other_convs[:5])
                    other_convs = other_convs[5:]
                else:
                    day_conversations.extend(other_convs[:6])
                    other_convs = other_convs[6:]
            elif day == 5:
                    # Day 5: show conversation 5 if conversation 2 was flagged correctly
                if flagged_correctly[2] and conv_5:
                    day_conversations.append(conv_5)
                    day_conversations.extend(other_convs[:5])
                    other_convs = other_convs[5:]
                else:
                    day_conversations.extend(other_convs[:6])
                    other_convs = other_convs[6:]
            elif day == 6:
                # Day 6: show conversation 6 if conversation 3 was flagged correctly
                if flagged_correctly[3] and conv_6:
                    day_conversations.append(conv_6)
                    day_conversations.extend(other_convs[:5])
                    other_convs = other_convs[5:]
                else:
                    day_conversations.extend(other_convs[:6])
                    other_convs = other_convs[6:]
    
        # Shuffle the day's conversations to randomize order within the day
            random.shuffle(day_conversations)
            
            # Show day intro
            clear_screen()
            print(center_in_terminal(BORDER_TOP))
            print_bordered("")
            print_bordered(f"DAY {day}".center(CONTENT_WIDTH))
            print_bordered("Beginning surveillance shift...".center(CONTENT_WIDTH))
            print_bordered("")
            print(center_in_terminal(BORDER_BOTTOM))
            
            with SkippableAnimation("day_intro") as anim:
                if not anim.check_skip():
                    time.sleep(2)
            
            # Play through conversations
            for i, conv in enumerate(day_conversations):
                # Display conversation
                while True:
                    display_conversation(conv)
                    player_judgment = get_player_judgment()
                    
                    if player_judgment == 'redisplay':
                        continue
                    else:
                        break
                
                if player_judgment:
                    day_flagged_count += 1
                
                correct = record_judgment(player_judgment, conv)
                if correct:
                    total_score += 1
                    
                # Track if special conversations were flagged correctly
                if conv['id'] in [1, 2, 3] and correct:
                    flagged_correctly[conv['id']] = True
                
                # Continue prompt
                if i < len(day_conversations) - 1:
                    prompt = center_in_terminal("\n>>> Press ENTER to continue <<<")
                    input(prompt)
            
            # Show daily report
            display_daily_report(day, day_flagged_count, len(day_conversations))
            
            if day < total_days:
                prompt = center_in_terminal("\n>>> Press ENTER to begin next shift <<<")
                input(prompt)
        
        # Final evaluation
        display_final_evaluation(total_score, total_days)
        
    finally:
        # Ensure keyboard handler is properly cleaned up
        keyboard_handler.stop_monitoring()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        keyboard_handler.stop_monitoring()
        print("\n\n[SYSTEM] Connection terminated.")
    except Exception as e:
        keyboard_handler.stop_monitoring()
        print(f"\n[ERROR] {e}")
        raise