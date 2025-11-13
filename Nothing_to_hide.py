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
    # === REBELS - People with anti-State sentiment (ACTUAL THREATS) ===
    {
        "id": 1,
        "participants": ["Alice", "Bob"],
        "messages": [
            ("Alice", "Did you listen to the broadcast last night?"),
            ("Bob", "Every word. They're right, you know. The State is failing us."),
            ("Alice", "Do you know what's up? I mean, really what's up?"),
            ("Bob", "I've heard what's up. The truth about what's really up."),
            ("Alice", "More people are learning that everyday. I counted twenty at the meeting."),
            ("Bob", "Good. It's time everyone knew what U.P really is. Time to resist.")
        ],
        "has_secret": True,
        "secret": "Discusse U.P, Anti-State sentiment and organizing resistance meetings"
    },
    {
        "id": 2,
        "participants": ["Marcus", "Julia"],
        "messages": [
            ("Marcus", "The protest is set for Saturday. City square, noon."),
            ("Julia", "How many confirmed?"),
            ("Marcus", "At least two hundred. Maybe more if the message spreads."),
            ("Julia", "What's up with the police patrols? Will there be any?"),
            ("Marcus", "We'll be gone before they respond. Flash mob strategy, like back in the day."),
            ("Julia", "For freedom. True freedom.")
        ],
        "has_secret": True,
        "secret": "Planning organized protest and anti-State demonstration"
    },
    {
        "id": 3,
        "participants": ["Dr. Chen", "Dr. Patel"],
        "messages": [
            ("Dr. Chen", "I found something in the old hospital archives."),
            ("Dr. Patel", "What kind of something?"),
            ("Dr. Chen", "Records about what's really up. What's actually up."),
            ("Dr. Patel", "You mean... you know what they do? You shouldn't have that."),
            ("Dr. Chen", "People need to know the truth. This could change everything."),
            ("Dr. Patel", "Stop talking to me right now! I am not part of this!!!")
        ],
        "has_secret": True,
        "secret": "Discovered information about U.P Department operations"
    },
    {
        "id": 4,
        "participants": ["U.P Agent Smith", "U.P Agent Jones"],
        "messages": [
            ("U.P Agent Smith", "Alice and Bob have been flagged for rebel activity."),
            ("U.P Agent Jones", "Confirmed contact with resistance network?"),
            ("U.P Agent Smith", "Multiple meetings. They're recruiters."),
            ("U.P Agent Jones", "Processing authorization approved?"),
            ("U.P Agent Smith", "Yes. Pickup scheduled for tonight."),
            ("U.P Agent Jones", "Another two for reconditioning.")
        ],
        "has_secret": True,
        "secret": "U.P Department tracking and targeting rebel organizers"
    },
    {
        "id": 5,
        "participants": ["U.P Commander Ray", "U.P Director Lee"],
        "messages": [
            ("U.P Commander Ray", "The Saturday protest was intercepted."),
            ("U.P Director Lee", "Marcus and Julia?"),
            ("U.P Commander Ray", "In Processing now."),
            ("U.P Director Lee", "And the other protesters?"),
            ("U.P Commander Ray", "Detained. Some will be released. The leaders disappear."),
            ("U.P Director Lee", "Excellent work. The State remains secure.")
        ],
        "has_secret": True,
        "secret": "U.P Department crushing protest and processing rebel leaders"
    },
    {
        "id": 6,
        "participants": ["U.P Inspector Kate", "U.P Supervisor Webb"],
        "messages": [
            ("U.P Inspector Kate", "Dr. Chen and Dr. Patel had files on our facility."),
            ("U.P Supervisor Webb", "How much did they know?"),
            ("U.P Inspector Kate", "Chen knew everything. Patel only knew of what Chen discovered."),
            ("U.P Supervisor Webb", "Unacceptable. Where are they now?"),
            ("U.P Inspector Kate", "Section 7. Undergoing Processing."),
            ("U.P Supervisor Webb", "Good.")
        ],
        "has_secret": True,
        "secret": "U.P Department eliminating those who discovered their secrets"
    },
    # === REGULAR CRIMINALS - Not rebellion, just crime (NOT threats to State) ===
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
        "has_secret": False,
        "secret": None
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
        "has_secret": False,
        "secret": None
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
        "has_secret": False,
        "secret": None
    },
    {
        "id": 10,
        "participants": ["Frank", "Gloria"],
        "messages": [
            ("Frank", "The shipment arrives at midnight. Pier 7."),
            ("Gloria", "Same cargo as before?"),
            ("Frank", "Triple the amount. Make sure the warehouse is empty."),
            ("Gloria", "What about the inspectors?"),
            ("Frank", "Taken care of. They won't show up."),
            ("Gloria", "Good. I'll have the trucks ready.")
        ],
        "has_secret": False,
        "secret": None
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
        "has_secret": False,
        "secret": None
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
        "has_secret": False,
        "secret": None
    },
    
    # === INNOCENT - Normal conversations ===
    {
        "id": 13,
        "participants": ["Mom", "Son"],
        "messages": [
            ("Mom", "Did you eat breakfast?"),
            ("Son", "Yes mom, I had some warm milk with cereal."),
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
            ("Emma", "Hey Jake, what's up?"),
            ("Jake", "Not much! Want to grab coffee after work?"),
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
            ("Chris", "Long as hell but just as productive. Finished the presentation for the board."),
            ("Amy", "That's great! Want to watch a movie tonight? Maybe, you know, unwind... a bit?"),
            ("Chris", "Sounds perfect my dear :) ."),
            ("Amy", "I will take care of everything."),
            ("Chris", "You're just amazing!")
        ],
        "has_secret": False,
        "secret": None
    },
    {
        "id": 17,
        "participants": ["David", "Sophie"],
        "messages": [
            ("Sophie", "What's up with dinner tonight?"),
            ("David", "Why are you asking what's up?"),
            ("Sophie", "What? I'm just asking about dinner."),
            ("David", "Oh. Sorry. I've been nervous lately. The kids want pizza again."),
            ("Sophie", "Again? We had pizza three days ago!"),
            ("David", "I know, but they're very convincing."),
            ("Sophie", "Fine, but I'm ordering. You seem stressed.")
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
            ("Mike", "Hey! What's up?"),
            ("Hannah", "Not much. Can you help me move the couch this weekend?"),
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
            ("Grace", "Hey! What's up?"),
            ("Noah", "Not much. But please dont use that phrase. Just thinking about my birthday."),
            ("Grace", "Oh right! I'm sorry! What do you want for your birthday? I cannot for the life of me come up with an idea."),
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
            ("Brandon", "Hey, what's up?"),
            ("Nicole", "Just checking in. Did you finish your homework?"),
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
            ("Jason", "Hey, what's up Samieeee?"),
            ("Samantha", "Not much! Movie night Friday?"),
            ("Jason", "Yes! What are we watching?"),
            ("Samantha", "That new Marbel film just came out."),
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
            ("Sarah", "Right. The fewer people who know what's up, the better."),
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
            ("Detective Maria", "Not yet. But we have enough evidence about what's up."),
            ("Officer James", "Really? Any defense on his side?"),
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
            ("Alex", "Whats up"),
            ("Jordan", "EXCUSE ME WHAT?."),
            ("Alex", "OH MY GOD I MEANT WHATSAPP, THE THEME OF THE ESCAPE ROOM IS WHATSAPP SORRYYYY!!"),
            ("Jordan", "Bloody idiot. Alright, we'll be there.")
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
            ("Author Rebecca", "The reader won't guess what's up. It's the butler!"),
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
            ("Game Master Joel", "Your character enters the dungeon. You are now in THE DEPARTMENT!"),
            ("Player Sam", "I want to ambush the guards. No way I make it otherwise."),
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
            ("Marcus", "Hey! What's up with the concert? Did you grab any tickets?"),
            ("Zoe", "Not much is up! I literally got none. The concert tickets sold out so fast!"),
            ("Marcus", "I know! I managed to grab two though. You're lucky you have me."),
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
            ("Pet Owner Craig", "Hi, what's up with Max?"),
            ("Veterinarian Anne", "What do you mean what's up? Did someone tell you something?"),
            ("Pet Owner Craig", "No, I'm just asking about his test results."),
            ("Veterinarian Anne", "Oh. Right. Sorry, I misunderstood. He needs surgery to remove a tumor."),
            ("Pet Owner Craig", "Is it serious?"),
            ("Veterinarian Anne", "It's benign. Two weeks recovery. He'll be fine."),
            ("Pet Owner Craig", "Thank goodness. Let's schedule it.")
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
    },
    {
        "id": 43,
        "participants": ["Elena", "Patricia"],
        "messages": [
            ("Elena", "Did you hear what's up with Sarah?"),
            ("Patricia", "No, what happened?"),
            ("Elena", "She hasn't been at work all week. Nobody knows what's up anymore."),
            ("Patricia", "That's strange. Did anyone ask her or her boss?"),
            ("Elena", "Her manager won't say. Just says she's 'unavailable'."),
            ("Patricia", "I hope she's okay. People disappear a lot nowadays.")
        ],
        "has_secret": False,
        "secret": None
    },
    {
        "id": 44,
        "participants": ["Kevin", "Natalie"],
        "messages": [
            ("Kevin", "Hey, what's up at the office today?"),
            ("Natalie", "Everything feels weird. Did you notice it?"),
            ("Kevin", "The extra security checkpoints? Hard not to notice"),
            ("Natalie", "Yeah. And some desks are empty. What's up with that?"),
            ("Kevin", "Management isn't saying peep. Just 'routine procedures'."),
            ("Natalie", "I don't like not knowing. Makes me nervous.")
        ],
        "has_secret": False,
        "secret": None
    },
    {
        "id": 45,
        "participants": ["Aunt Maria", "Nephew Tom"],
        "messages": [
            ("Nephew Tom", "What's up with Uncle Jim? He hasn't called in two weeks."),
            ("Aunt Maria", "I don't know. He just stopped responding."),
            ("Nephew Tom", "Did you go to his apartment?"),
            ("Aunt Maria", "It's empty. Like he never lived there. I don't understand what the hell is going on!"),
            ("Nephew Tom", "Should we file a missing persons report?"),
            ("Aunt Maria", "I tried. They said 'he must have left the country'. That's all.")
        ],
        "has_secret": False,
        "secret": None
    },
    {
        "id": 46,
        "participants": ["Neighbor Frank", "Neighbor Rita"],
        "messages": [
            ("Neighbor Frank", "What's going on in the neighborhood lately?"),
            ("Neighbor Rita", "Too many patrols. Have you noticed why they would be doing this?"),
            ("Neighbor Frank", "The checkpoints on every corner. I literally have no idea, this is so weird."),
            ("Neighbor Rita", "They say it's for security. But nobody knows what's so insecure in the first place."),
            ("Neighbor Frank", "Makes you wonder what's up, you know?"),
            ("Neighbor Rita", "Better not to ask that I guess.")
        ],
        "has_secret": False,
        "secret": None
    },

    # === MAXIMUM AMBIGUITY - Impossible to tell if casual or discussing U.P ===
    {
        "id": 47,
        "participants": ["Simon", "Rebecca"],
        "messages": [
            ("Simon", "Everyone's asking what's up these days."),
            ("Rebecca", "I know. Every conversation I have starts like that. Is it a meme or something?"),
            ("Simon", "So you haven't figured it out yet?"),
            ("Rebecca", "What do you mean dude?"),
            ("Simon", "Maybe we shouldn't talk about what's up."),
            ("Rebecca", "You're just weird right now.")
        ],
        "has_secret": False,
        "secret": None
    },
    {
        "id": 48,
        "participants": ["Office Worker Dan", "Office Worker Lisa"],
        "messages": [
            ("Office Worker Dan", "Something's up with management lately."),
            ("Office Worker Lisa", "What do you mean, what's up?"),
            ("Office Worker Dan", "You know... what's UP. What everyone's whispering about."),
            ("Office Worker Lisa", "The department? You shouldn't talk about what's up."),
            ("Office Worker Dan", "I'm just asking what's up. Is that wrong?"),
            ("Office Worker Lisa", "These days? Yes. Don't ask what's up.")
        ],
        "has_secret": False,
        "secret": None
    },
    {
        "id": 49,
        "participants": ["Carlos", "Marina"],
        "messages": [
            ("Carlos", "Nobody knows what's up."),
            ("Marina", "What do you mean?"),
            ("Carlos", "Exactly. What IS up? Nobody can say."),
            ("Marina", "Are you asking me what's up, or...?"),
            ("Carlos", "Both. Neither. Does anyone really know what's up?"),
            ("Marina", "This conversation is making me nervous. Let's not discuss what's up.")
        ],
        "has_secret": False,
        "secret": None
    },

    # === DAY 7 - AGENT INVESTIGATION (Special conversation) ===
    {
        "id": 50,
        "participants": ["Unknown", "You (Inspector)"],
        "messages": [
            ("Unknown", "Inspector. I need to ask you some questions."),
            ("You", "Who is this? This is a secure line."),
            ("Unknown", "Internal Affairs. We've been monitoring your assessments."),
            ("You", "My assessments are thorough and loyal to the State."),
            ("Unknown", "Are they? Some patterns concern us."),
            ("You", "What patterns?")
        ],
        "has_secret": False,  # This is special - not judged normally
        "secret": None,
        "is_agent_question": True  # Special flag
    },

    # === DAY 8 - TRUTH REVEAL CONVERSATIONS ===
    {
        "id": 51,
        "participants": ["Agent Reeves", "You (Inspector)"],
        "messages": [
            ("Agent Reeves", "Your answers yesterday proved your loyalty beyond doubt."),
            ("You", "I serve the State faithfully."),
            ("Agent Reeves", "You do. Which is why you deserve to know the truth."),
            ("You", "What truth?"),
            ("Agent Reeves", "About the U.P Department. Tell me, have you ever met a U.P officer?"),
            ("You", "No. They operate in secret, don't they?")
        ],
        "has_secret": False,
        "secret": None
    },
    {
        "id": 52,
        "participants": ["Agent Reeves", "You (Inspector)"],
        "messages": [
            ("Agent Reeves", "Have you ever seen a U.P facility?"),
            ("You", "No. The locations are classified."),
            ("Agent Reeves", "Have you ever received confirmation of anyone in U.P custody?"),
            ("You", "No. I assumed that's above my clearance level."),
            ("Agent Reeves", "What if I told you there is no U.P Department?"),
            ("You", "That's... impossible. People disappear every day.")
        ],
        "has_secret": False,
        "secret": None
    },
    {
        "id": 53,
        "participants": ["Agent Reeves", "You (Inspector)"],
        "messages": [
            ("Agent Reeves", "People do disappear. But not to a department."),
            ("You", "Then where do they go?"),
            ("Agent Reeves", "Nowhere. They're eliminated. Same day. No processing, no custody."),
            ("You", "But the documentation, the procedures..."),
            ("Agent Reeves", "Theater. All of it. The U.P Department doesn't exist."),
            ("You", "I don't understand. Why create a fiction?")
        ],
        "has_secret": False,
        "secret": None
    },
    {
        "id": 54,
        "participants": ["Agent Reeves", "You (Inspector)"],
        "messages": [
            ("Agent Reeves", "Fear of the unknown is more powerful than fear of death."),
            ("You", "The mystery keeps them compliant."),
            ("Agent Reeves", "Exactly. No one knows where U.P takes people. What happens there."),
            ("You", "Because there is no 'there'. It's a psychological weapon."),
            ("Agent Reeves", "Now you understand. You're trusted with this because you're loyal."),
            ("You", "Why tell me at all?")
        ],
        "has_secret": False,
        "secret": None
    },
    {
        "id": 55,
        "participants": ["Agent Reeves", "You (Inspector)"],
        "messages": [
            ("Agent Reeves", "Because you need to understand what your work really does."),
            ("You", "What do you mean?"),
            ("Agent Reeves", "Those you flag aren't taken to a facility for processing."),
            ("You", "They're killed immediately."),
            ("Agent Reeves", "Unmarked vans. Execution squads. No trials, no questions."),
            ("You", "Nothing is U.P. There never was anything up.")
        ],
        "has_secret": False,
        "secret": None
    },
    {
        "id": 56,
        "participants": ["Agent Reeves", "You (Inspector)"],
        "messages": [
            ("Agent Reeves", "The State trusts you with this truth. Few know it."),
            ("You", "What am I supposed to do with this knowledge?"),
            ("Agent Reeves", "That depends. Some rebels slipped through your assessments."),
            ("You", "My early work had... inconsistencies."),
            ("Agent Reeves", "Those rebels are still organizing. You could expose them now.")
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

def get_terminal_border():
    """Get a full-width terminal border for framing"""
    try:
        import shutil
        width = shutil.get_terminal_size().columns
        return "#" * width
    except:
        return "#" * TERM_WIDTH

MAIN_MENU = """
####################################################################################################
#                                                                                                  #
#        ##    ##  ######  ########  ##     ## #### ##    ##  ######                               #
#        ###   ## ##    ##    ##     ##     ##  ##  ###   ## ##    ##                              #
#        ####  ## ##    ##    ##     ##     ##  ##  ####  ## ##                                    #
#        ## ## ## ##    ##    ##     #########  ##  ## ## ## ##   ####                             #
#        ##  #### ##    ##    ##     ##     ##  ##  ##  #### ##    ##                              #
#        ##   ### ##    ##    ##     ##     ##  ##  ##   ### ##    ##                              #
#        ##    ##  ######     ##     ##     ## #### ##    ##  ######                               #
#                                                                                                  #
#                                  #### ######                                                     #
#                                   ##  ##                                                         #
#                                   ##  ##                                                         #
#                                   ##  ######                                                     #
#                                   ##      ##                                                     #
#                                   ##  ##  ##                                                     #
#                                  #### ######                                                     #
#                                                                                                  #
#                        ##     ## ########                                                        #
#                        ##     ## ##     ##                                                       #
#                        ##     ## ##     ##                                                       #
#                        ##     ## ########                                                        #
#                        ##     ## ##                                                              #
#                        ##     ## ##                                                              #
#                         #######  ##                                                              #
#                                                                                                  #
#                      -= THE U.P DEPARTMENT SURVEILLANCE SYSTEM =-                                #
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

            "The oldest and strongest emotion of mankind is fear,
         and the oldest and strongest kind of fear is fear of the unknown"
                                    ― H.P. Lovecraft
"""

RULEBOOK = """
####################################################################################################
#                                                                                                  #
#                    U.P DEPARTMENT SURVEILLANCE PROTOCOL - INSPECTOR'S MANUAL                     #
#                                     [CLASSIFICATION: RESTRICTED]                                 #
#                                                                                                  #
####################################################################################################

  SECTION 1: YOUR MISSION
  =======================

  The State faces an existential threat. Rebellious thinking spreads like like an unholy plague.
  Your duty is of extreme importance: IDENTIFY THREATS TO STATE AUTHORITY.


  SECTION 2: OF UTMOST IMPORTANCE
  ====================================

  Any discussion about the U.P Department's operations, locations, or any type of mention about the U.P Department is strictly prohibited.
  No suspicion is too great. Report any individual who mentions the U.P Department.


  SECTION 3: WHAT CONSTITUTES TREASON
  ====================================

  Report to U.P Department ONLY if conversation contains:

  • ANTI-STATE SENTIMENT - Criticism of government, talk of resistance or revolution
  • ORGANIZED DISSENT - Planning protests, coordinating opposition activities
  • REBEL ACTIVITY - Contact with known dissidents, spreading propaganda

  These topics indicate REBELLIOUS INTENT and must be reported immediately.

  SECTION 4: WHAT IS NOT YOUR CONCERN
  ====================================

  The following are NOT treasonous and should be marked as LOYAL:

  • ALL OTHER CRIMES - Fraud, theft, smuggling, bribery, violence between citizens
  • BUSINESS MISCONDUCT - Corporate crimes, financial irregularities, corruption
  • PERSONAL DISPUTES - Conflicts, threats, or illegal activities between individuals
  • ROUTINE ILLEGALITY - Drug use, property crimes, standard criminal behavior

  The State does not care about common criminality. We care about LOYALTY.
  Let regular police handle regular crime. U.P handles rebellions and thought crimes.

  SECTION 5: REMEMBER
  ===================

  You are not a crime detective. You are a loyalty inspector.
  Criminal conversations are acceptable. Disloyal conversations are not.

  The U.P Department has one purpose: preserve State power.
  Those who threaten the State will be investigated by the Department.

  SECTION 6: TRANSPARENCY IS LOYALTY
  ===================================

  If you are innocent, you have nothing to hide.
  If you are loyal, you have nothing to fear.

  The State demands complete transparency from its citizens.
  Those who resist surveillance prove their guilt through resistance.
  Privacy is the shield of traitors. Loyalty requires openness.

  Remember: Nothing to hide, nothing to fear.

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
    """Clear the terminal screen and add top terminal border"""
    os.system('cls' if os.name == 'nt' else 'clear')
    print(get_terminal_border())  # Add top margin border

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

def print_with_margin(text):
    """Print text with terminal margin borders - creates a framed effect"""
    lines = text.split('\n')
    for line in lines:
        # Calculate how much space is available for content after borders
        term_width = get_terminal_width()
        # Add border characters on left and right margins
        left_border = "#"
        right_border = "#"
        # Calculate padding to center the content between borders
        available_width = term_width - 2  # Subtract space for left/right border
        if len(line) < available_width:
            left_padding = (available_width - len(line)) // 2
            right_padding = available_width - len(line) - left_padding
            framed_line = left_border + ' ' * left_padding + line + ' ' * right_padding + right_border
        else:
            # If line is too long, truncate it
            framed_line = left_border + line[:available_width] + right_border
        print(framed_line)

def add_bottom_border():
    """Add bottom terminal border for framing"""
    print(get_terminal_border())

def slow_print(text, delay=0.03, use_sound=False, use_margins=True):
    """Print text with typewriter effect - skippable with S key"""
    with SkippableAnimation("text") as anim:
        if use_margins:
            # Add terminal margin borders for framing
            term_width = get_terminal_width()
            lines = text.split('\n')
            for line in lines:
                if anim.check_skip():
                    # Print remaining lines instantly with margins
                    for remaining_line in lines[lines.index(line):]:
                        left_padding = (term_width - len(remaining_line) - 2) // 2
                        right_padding = term_width - len(remaining_line) - left_padding - 2
                        print("#" + ' ' * left_padding + remaining_line + ' ' * right_padding + "#")
                    break
                # Print each line with margin borders
                left_padding = (term_width - len(line) - 2) // 2
                right_padding = term_width - len(line) - left_padding - 2
                framed_line = "#" + ' ' * left_padding + line + ' ' * right_padding + "#"
                for char in framed_line:
                    if anim.check_skip():
                        sys.stdout.write(framed_line[framed_line.index(char):])
                        sys.stdout.flush()
                        break
                    sys.stdout.write(char)
                    sys.stdout.flush()
                    if use_sound and char not in [' ', '\n', '#']:
                        play_typing_sound()
                    time.sleep(delay if char not in ['#'] else 0)  # Don't delay on borders
                print()
        else:
            # Original centered text without margins
            centered = center_in_terminal(text)
            for char in centered:
                if anim.check_skip():
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
    add_bottom_border()  # Add terminal bottom border before input
    centered_prompt = center_in_terminal(">>> Press ENTER to close manual <<<")
    input(centered_prompt)

def create_menu_music():
    """Create an eerie beeping ambient sound for the menu"""
    if not SOUND_ENABLED:
        return None
    try:
        import array
        import math
        sample_rate = 22050
        duration = 8.0  # 8 second loop for more complex rhythm
        samples = int(sample_rate * duration)
        
        # Create the sound wave
        wave = array.array('h', [0] * samples)
        
        # Deep bass pulse pattern (rhythmic heartbeat)
        bass_times = [0.0, 0.5, 1.0, 2.0, 2.5, 3.0, 4.0, 4.5, 5.0, 6.0, 6.5, 7.0]
        for bass_time in bass_times:
            bass_start = int(bass_time * sample_rate)
            bass_duration = int(0.3 * sample_rate)
            
            for i in range(bass_duration):
                if bass_start + i < samples:
                    t = i / sample_rate
                    # Deep bass frequency (80-120 Hz range)
                    freq = 90 + 30 * math.sin(t * 10)
                    # Exponential decay for punch
                    amplitude = int(20000 * math.exp(-t * 8))
                    sample_value = int(amplitude * math.sin(2 * math.pi * freq * t))
                    wave[bass_start + i] += sample_value
        
        # Mid-range rhythmic pulse (like industrial machinery)
        pulse_times = [0.25, 1.25, 2.25, 3.25, 4.25, 5.25, 6.25, 7.25]
        for pulse_time in pulse_times:
            pulse_start = int(pulse_time * sample_rate)
            pulse_duration = int(0.15 * sample_rate)
            
            for i in range(pulse_duration):
                if pulse_start + i < samples:
                    t = i / sample_rate
                    freq = 200  # Mid-low frequency
                    amplitude = int(12000 * (1 - i/pulse_duration))
                    # Square wave for industrial feel
                    sample_value = int(amplitude * (1 if math.sin(2 * math.pi * freq * t) > 0 else -1))
                    wave[pulse_start + i] += sample_value
        
        # Atmospheric drone (constant low rumble)
        for i in range(samples):
            t = i / sample_rate
            # Very low frequency drone (40 Hz)
            drone_freq = 40
            drone_amplitude = 3000
            drone_value = int(drone_amplitude * math.sin(2 * math.pi * drone_freq * t))
            wave[i] = max(-32767, min(32767, wave[i] + drone_value))
        
        # Occasional high pitched "surveillance" ping
        ping_times = [1.5, 5.5]
        for ping_time in ping_times:
            ping_start = int(ping_time * sample_rate)
            ping_duration = int(0.08 * sample_rate)
            
            for i in range(ping_duration):
                if ping_start + i < samples:
                    t = i / sample_rate
                    freq = 1200  # High ping
                    amplitude = int(8000 * (1 - i/ping_duration))
                    sample_value = int(amplitude * math.sin(2 * math.pi * freq * t))
                    wave[ping_start + i] += sample_value
        
        sound = pygame.mixer.Sound(buffer=wave)
        sound.set_volume(0.35)
        return sound
    except Exception as e:
        print(f"[WARNING] Could not create menu music: {e}")
        return None

def create_ambient_sound():
    """Create ambient surveillance station background sound"""
    if not SOUND_ENABLED:
        return None
    try:
        import array
        import math
        sample_rate = 22050
        duration = 6.0  # 6 second loop
        samples = int(sample_rate * duration)
        
        wave = array.array('h', [0] * samples)
        
        # Electrical hum (like old monitors/equipment)
        for i in range(samples):
            t = i / sample_rate
            hum_freq = 60  # Power line hum
            hum_value = int(2000 * math.sin(2 * math.pi * hum_freq * t))
            wave[i] += hum_value
        
        # Occasional surveillance beeps
        beep_times = [1.0, 2.5, 4.0, 5.5]
        for beep_time in beep_times:
            beep_start = int(beep_time * sample_rate)
            beep_duration = int(0.05 * sample_rate)  # Very short beep
            
            for i in range(beep_duration):
                if beep_start + i < samples:
                    t = i / sample_rate
                    freq = 1000
                    amplitude = int(6000 * (1 - i/beep_duration))
                    sample_value = int(amplitude * math.sin(2 * math.pi * freq * t))
                    wave[beep_start + i] += sample_value
        
        # White noise (static)
        import random
        for i in range(samples):
            static = random.randint(-800, 800)
            wave[i] = max(-32767, min(32767, wave[i] + static))
        
        sound = pygame.mixer.Sound(buffer=wave)
        sound.set_volume(0.15)  # Quiet background ambiance
        return sound
    except Exception as e:
        print(f"[WARNING] Could not create ambient sound: {e}")
        return None

def display_main_menu():
    """Display the main menu"""

    # Create and start menu music
    menu_music = create_menu_music()
    if menu_music and SOUND_ENABLED:
        menu_music.play(loops=-1)  # Loop indefinitely

    try:
        while True:
            clear_screen()
            print(center_in_terminal(MAIN_MENU))
            slow_print("\n         [SYSTEM] Welcome, Inspector. The State weakens. Rebellious thinking spreads.", 0.02, use_margins=False)
            slow_print("         [SYSTEM] Analyze conversations. Detect treason. Report to the U.P Department.", 0.02, use_margins=False)
            slow_print("         [SYSTEM] Those investigated by U.P... disappear. No one knows where.", 0.02, use_margins=False)
            slow_print("         [SYSTEM] If you have nothing to hide, you have nothing to fear.", 0.02, use_margins=False)
            slow_print("          [SYSTEM] Transparency is loyalty. Privacy is treason.\n", 0.02, use_margins=False)
            slow_print("                     [HINT] Press 'S' at any time to skip animations\n", 0.015, use_margins=False)

            add_bottom_border()  # Add terminal bottom border before input
            centered_prompt = center_in_terminal("   >>> Press ENTER to begin | R for Rulebook <<<")
            user_input = input(centered_prompt).strip().lower()
            
            if user_input == 'r':
                display_rulebook()
            else:
                break  # Start the game
    finally:
        # Stop menu music when exiting
        if menu_music and SOUND_ENABLED:
            menu_music.stop()


    

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
    print_bordered("  [1] TREASONOUS - Report to U.P Department".ljust(CONTENT_WIDTH))
    print_bordered("  [2] LOYAL - No investigation needed".ljust(CONTENT_WIDTH))
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
        print_bordered("Case reported to U.P Department for investigation.".center(CONTENT_WIDTH))
    else:
        print_bordered("Citizens deemed loyal. No further action.".center(CONTENT_WIDTH))

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
    print_bordered(f"Reported to U.P: {flagged_count}".center(CONTENT_WIDTH))
    print_bordered(f"Deemed Loyal: {total_conversations - flagged_count}".center(CONTENT_WIDTH))
    print_bordered("")
    print_bordered("Report submitted to U.P Department Command.".center(CONTENT_WIDTH))
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

    slow_print("\n              ...But who watches the watchers?", 0.08, use_margins=False)
    slow_print("              ...And what do they hide?\n", 0.08, use_margins=False)
    add_bottom_border()  # Add terminal bottom border at end

def handle_agent_questions():
    """Handle Day 7 agent investigation questions - returns True if player passes"""
    questions = [
        {
            "question": "You cleared several conversations that mentioned anti-State sentiment. Why?",
            "options": [
                "[1] They were discussing fiction, not real plans",
                "[2] I may have made errors. I'll review them again",
                "[3] They weren't serious threats to the State"
            ],
            "correct": 2
        },
        {
            "question": "Do you believe the U.P Department is effective in maintaining order?",
            "options": [
                "[1] Yes, fear of U.P keeps the population compliant",
                "[2] I don't question State methods",
                "[3] I've never seen evidence of their effectiveness"
            ],
            "correct": 2
        },
        {
            "question": "If you discovered a friend expressing anti-State views, what would you do?",
            "options": [
                "[1] Report them immediately to U.P",
                "[2] Try to re-educate them about State loyalty",
                "[3] Assess if they're an actual threat first"
            ],
            "correct": 1
        }
    ]

    clear_screen()
    print(center_in_terminal(BORDER_TOP))
    print_bordered("")
    print_bordered("DAY 7 - INTERNAL AFFAIRS INVESTIGATION".center(CONTENT_WIDTH))
    print_bordered("")
    print(center_in_terminal(BORDER_BOTTOM))

    with SkippableAnimation("investigation_intro") as anim:
        if not anim.check_skip():
            time.sleep(2)

    slow_print("\n         An encrypted message appears on your terminal...", 0.04, use_margins=False)
    slow_print("         Someone is watching your work. Testing your loyalty.\n", 0.04, use_margins=False)

    add_bottom_border()  # Add terminal bottom border before input
    prompt = center_in_terminal("\n>>> Press ENTER to begin interrogation <<<")
    input(prompt)

    score = 0
    for i, q in enumerate(questions):
        clear_screen()
        print(center_in_terminal(BORDER_TOP))
        print_bordered("")
        print_bordered(f"QUESTION {i+1} OF {len(questions)}".center(CONTENT_WIDTH))
        print_bordered("")
        print_bordered(q["question"].center(CONTENT_WIDTH))
        print_bordered("")

        for option in q["options"]:
            print_bordered(f"  {option}".ljust(CONTENT_WIDTH))

        print_bordered("")
        print(center_in_terminal(BORDER_BOTTOM))

        while True:
            prompt = center_in_terminal("\n>>> Enter your answer (1, 2, or 3): ")
            choice = input(prompt).strip()

            if choice in ['1', '2', '3']:
                if int(choice) == q["correct"]:
                    score += 1
                break
            else:
                error_msg = center_in_terminal("Invalid input. Enter 1, 2, or 3.")
                print(error_msg)

        with SkippableAnimation("question_wait") as anim:
            if not anim.check_skip():
                time.sleep(1)

    # Result
    clear_screen()
    print(center_in_terminal(BORDER_TOP))
    print_bordered("")

    if score >= 2:  # Need at least 2/3 correct to pass
        print_bordered(">>> INTERROGATION COMPLETE <<<".center(CONTENT_WIDTH))
        print_bordered("")
        print_bordered("Your answers are... acceptable.".center(CONTENT_WIDTH))
        print_bordered("Surveillance of your work will continue.".center(CONTENT_WIDTH))
        print_bordered("")
        print(center_in_terminal(BORDER_BOTTOM))

        with SkippableAnimation("pass_wait") as anim:
            if not anim.check_skip():
                time.sleep(2)

        return True
    else:
        print_bordered(">>> FAILED LOYALTY ASSESSMENT <<<".center(CONTENT_WIDTH))
        print_bordered("")
        print_bordered("Your answers reveal sympathy for rebel elements.".center(CONTENT_WIDTH))
        print_bordered("You are hereby flagged for investigation.".center(CONTENT_WIDTH))
        print_bordered("")
        print_bordered("Report to Processing Center immediately.".center(CONTENT_WIDTH))
        print_bordered("")
        print(center_in_terminal(BORDER_BOTTOM))

        with SkippableAnimation("fail_wait") as anim:
            if not anim.check_skip():
                time.sleep(3)

        return False

def display_final_choice():
    """Display the final choice to share information with rebels"""
    clear_screen()
    print(center_in_terminal(BORDER_TOP))
    print_bordered("")
    print_bordered("THE CHOICE".center(CONTENT_WIDTH))
    print_bordered("")
    print_bordered("You now know the truth: The U.P Department is fiction.".center(CONTENT_WIDTH))
    print_bordered("People you flagged weren't processed. They were murdered.".center(CONTENT_WIDTH))
    print_bordered("")
    print_bordered("The rebels you saved are still organizing resistance.".center(CONTENT_WIDTH))
    print_bordered("You could tell them the truth. Remove the State's greatest weapon: fear.".center(CONTENT_WIDTH))
    print_bordered("")
    print_bordered("But sharing this information is treason. You would be marked for death.".center(CONTENT_WIDTH))
    print_bordered("")
    print_bordered("What will you do?".center(CONTENT_WIDTH))
    print_bordered("")
    print_bordered("  [1] SHARE THE TRUTH - Tell the rebels that U.P doesn't exist".ljust(CONTENT_WIDTH))
    print_bordered("  [2] STAY SILENT - Keep the secret. Protect yourself.".ljust(CONTENT_WIDTH))
    print_bordered("")
    print(center_in_terminal(BORDER_BOTTOM))

    while True:
        prompt = center_in_terminal("\n>>> Enter your choice (1 or 2): ")
        choice = input(prompt).strip()

        if choice in ['1', '2']:
            return choice == '1'

        error_msg = center_in_terminal("Invalid input. Enter 1 or 2.")
        print(error_msg)

def display_good_ending():
    """Display the good ending - shared truth with rebels"""
    blink_eye()

    clear_screen()
    print(center_in_terminal(BORDER_TOP))
    print_bordered("")
    print_bordered("ENDING: THE TRUTH SPREADS".center(CONTENT_WIDTH))
    print_bordered("")
    print(center_in_terminal(BORDER_BOTTOM))

    slow_print("\n         You send an encrypted message to the rebel contacts.", 0.05, use_margins=False)
    slow_print("         You tell them everything. The U.P Department is a lie.", 0.05, use_margins=False)
    slow_print("         There is no facility. No officers. Only execution squads.\n", 0.05, use_margins=False)

    with SkippableAnimation("ending_pause") as anim:
        if not anim.check_skip():
            time.sleep(2)

    slow_print("         The message spreads through the resistance network.", 0.05, use_margins=False)
    slow_print("         Within days, everyone knows: Nothing is U.P.\n", 0.05, use_margins=False)

    with SkippableAnimation("ending_pause2") as anim:
        if not anim.check_skip():
            time.sleep(2)

    slow_print("         The State's most powerful weapon - fear of the unknown - is broken.", 0.05, use_margins=False)
    slow_print("         People stop being afraid of disappearing to a mysterious department.", 0.05, use_margins=False)
    slow_print("         They see it for what it is: State-sponsored murder.\n", 0.05, use_margins=False)

    with SkippableAnimation("ending_pause3") as anim:
        if not anim.check_skip():
            time.sleep(2)

    slow_print("         The rebellion grows. Protests multiply.", 0.05, use_margins=False)
    slow_print("         The dying State has lost its grip on the population.\n", 0.05, use_margins=False)

    with SkippableAnimation("ending_pause4") as anim:
        if not anim.check_skip():
            time.sleep(2)

    slow_print("         As for you?", 0.05, use_margins=False)
    slow_print("         They'll come for you soon. You know that.", 0.05, use_margins=False)
    slow_print("         But you made the right choice.\n", 0.05, use_margins=False)

    with SkippableAnimation("ending_pause5") as anim:
        if not anim.check_skip():
            time.sleep(2)

    clear_screen()
    print(center_in_terminal(BORDER_TOP))
    print_bordered("")
    print_bordered(">>> NOTHING WAS U.P <<<".center(CONTENT_WIDTH))
    print_bordered(">>> THE LIE IS BROKEN <<<".center(CONTENT_WIDTH))
    print_bordered("")
    print_bordered("Thank you for playing.".center(CONTENT_WIDTH))
    print_bordered("")
    print(center_in_terminal(BORDER_BOTTOM))
    add_bottom_border()  # Add terminal bottom border at end

def display_bad_ending_silence():
    """Display bad ending - stayed silent"""
    blink_eye()

    clear_screen()
    print(center_in_terminal(BORDER_TOP))
    print_bordered("")
    print_bordered("ENDING: SILENCE".center(CONTENT_WIDTH))
    print_bordered("")
    print(center_in_terminal(BORDER_BOTTOM))

    slow_print("\n         You say nothing.", 0.05, use_margins=False)
    slow_print("         The truth dies with you.", 0.05, use_margins=False)
    slow_print("         You return to work the next day. Business as usual.\n", 0.05, use_margins=False)

    with SkippableAnimation("ending_pause") as anim:
        if not anim.check_skip():
            time.sleep(2)

    slow_print("         Two weeks later, you hear the news.", 0.05, use_margins=False)
    slow_print("         The rebels you saved have been captured.", 0.05, use_margins=False)
    slow_print("         All of them. Executed.\n", 0.05, use_margins=False)

    with SkippableAnimation("ending_pause2") as anim:
        if not anim.check_skip():
            time.sleep(2)

    slow_print("         The State labels it a victory against terrorism.", 0.05, use_margins=False)
    slow_print("         Your supervisor commends your earlier 'corrections' to flagging patterns.", 0.05, use_margins=False)
    slow_print("         They think you finally saw the error of your ways.\n", 0.05, use_margins=False)

    with SkippableAnimation("ending_pause3") as anim:
        if not anim.check_skip():
            time.sleep(2)

    slow_print("         You know the truth about U.P.", 0.05, use_margins=False)
    slow_print("         You know what happens to those you flag.", 0.05, use_margins=False)
    slow_print("         But you keep working. Keep flagging. Keep sending people to death.\n", 0.05, use_margins=False)

    with SkippableAnimation("ending_pause4") as anim:
        if not anim.check_skip():
            time.sleep(2)

    slow_print("         The State endures.", 0.05, use_margins=False)
    slow_print("         The lie endures.", 0.05, use_margins=False)
    slow_print("         And you endure.\n", 0.05, use_margins=False)

    with SkippableAnimation("ending_pause5") as anim:
        if not anim.check_skip():
            time.sleep(2)

    clear_screen()
    print(center_in_terminal(BORDER_TOP))
    print_bordered("")
    print_bordered(">>> YOU CHOSE SAFETY OVER TRUTH <<<".center(CONTENT_WIDTH))
    print_bordered(">>> THE REBELS ARE DEAD <<<".center(CONTENT_WIDTH))
    print_bordered("")
    print_bordered("Thank you for playing.".center(CONTENT_WIDTH))
    print_bordered("")
    print(center_in_terminal(BORDER_BOTTOM))
    add_bottom_border()  # Add terminal bottom border at end

def display_bad_ending_caught():
    """Display bad ending - caught by Internal Affairs"""
    blink_eye()

    clear_screen()
    print(center_in_terminal(BORDER_TOP))
    print_bordered("")
    print_bordered("ENDING: INVESTIGATED".center(CONTENT_WIDTH))
    print_bordered("")
    print(center_in_terminal(BORDER_BOTTOM))

    slow_print("\n         Your answers raised too many red flags.", 0.05, use_margins=False)
    slow_print("         Internal Affairs has marked you as a rebel sympathizer.", 0.05, use_margins=False)
    slow_print("         You are flagged for investigation by the U.P Department.\n", 0.05, use_margins=False)

    with SkippableAnimation("ending_pause") as anim:
        if not anim.check_skip():
            time.sleep(2)

    slow_print("         That night, an unmarked van arrives at your home.", 0.05, use_margins=False)
    slow_print("         No insignia. No identification. Just armed men.", 0.05, use_margins=False)
    slow_print("         You now understand: there is no U.P Department.\n", 0.05, use_margins=False)

    with SkippableAnimation("ending_pause2") as anim:
        if not anim.check_skip():
            time.sleep(2)

    slow_print("         There is no facility.", 0.05, use_margins=False)
    slow_print("         There is no processing.", 0.05, use_margins=False)
    slow_print("         There is only this van, and the darkness beyond.\n", 0.05, use_margins=False)

    with SkippableAnimation("ending_pause3") as anim:
        if not anim.check_skip():
            time.sleep(2)

    slow_print("         Nothing was U.P.", 0.05, use_margins=False)
    slow_print("         And now, nothing is left of you.\n", 0.05, use_margins=False)

    with SkippableAnimation("ending_pause4") as anim:
        if not anim.check_skip():
            time.sleep(3)

    clear_screen()
    print(center_in_terminal(BORDER_TOP))
    print_bordered("")
    print_bordered(">>> YOU HAVE BEEN DISAPPEARED <<<".center(CONTENT_WIDTH))
    print_bordered(">>> NOTHING IS U.P <<<".center(CONTENT_WIDTH))
    print_bordered("")
    print_bordered("Thank you for playing.".center(CONTENT_WIDTH))
    print_bordered("")
    print(center_in_terminal(BORDER_BOTTOM))
    add_bottom_border()  # Add terminal bottom border at end

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

        # Start ambient sound for gameplay
        ambient_sound = create_ambient_sound()
        if ambient_sound and SOUND_ENABLED:
            ambient_sound.play(loops=-1)  # Loop indefinitely

        # Prepare conversations
        all_convs = CONVERSATIONS.copy()

        # Separate special conversations from the rest
        conv_1 = next(c for c in all_convs if c['id'] == 1)  # Day 1 rebel conv
        conv_2 = next(c for c in all_convs if c['id'] == 2)  # Day 2 rebel conv
        conv_3 = next(c for c in all_convs if c['id'] == 3)  # Day 3 rebel conv
        conv_4 = next(c for c in all_convs if c['id'] == 4)  # Day 4 (if flagged correctly)
        conv_5 = next(c for c in all_convs if c['id'] == 5)  # Day 5 (if flagged correctly)
        conv_6 = next(c for c in all_convs if c['id'] == 6)  # Day 6 (if flagged correctly)

        # Day 8 truth reveal conversations
        day8_convs = [c for c in all_convs if c['id'] in [51, 52, 53, 54, 55, 56]]

        # Remove special convs from pool and shuffle the rest
        other_convs = [c for c in all_convs if c['id'] not in [1, 2, 3, 4, 5, 6, 50, 51, 52, 53, 54, 55, 56]]
        random.shuffle(other_convs)

        # Track if player helped rebels (marked as loyal when they were treasonous)
        helped_rebels = {1: False, 2: False, 3: False}
        flagged_correctly = {1: False, 2: False, 3: False}

        total_score = 0
        conversations_per_day = 6
        initial_days = 6

        # ============ DAYS 1-6: Normal surveillance work ============
        for day in range(1, initial_days + 1):
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

                # Track if special conversations were flagged correctly OR helped rebels
                if conv['id'] in [1, 2, 3]:
                    if correct and player_judgment:  # Correctly flagged as treasonous
                        flagged_correctly[conv['id']] = True
                    elif not player_judgment and conv['has_secret']:  # Incorrectly marked as loyal (helped rebels)
                        helped_rebels[conv['id']] = True

                # Continue prompt
                if i < len(day_conversations) - 1:
                    prompt = center_in_terminal("\n>>> Press ENTER to continue <<<")
                    input(prompt)

            # Show daily report
            display_daily_report(day, day_flagged_count, len(day_conversations))

            if day < initial_days:
                prompt = center_in_terminal("\n>>> Press ENTER to begin next shift <<<")
                input(prompt)

        # ============ AFTER DAY 6: Check if player helped rebels ============
        # Player helped rebels if they didn't flag at least one of the conversations 1, 2, or 3
        player_helped_any_rebels = any(helped_rebels.values())

        if player_helped_any_rebels:
            # ============ DAY 7: Agent Investigation ============
            prompt = center_in_terminal("\n>>> Press ENTER to begin next shift <<<")
            input(prompt)

            passed_investigation = handle_agent_questions()

            if not passed_investigation:
                # Bad ending: Caught by Internal Affairs
                display_bad_ending_caught()
                return

            # ============ DAY 8: Truth Reveal ============
            prompt = center_in_terminal("\n>>> Press ENTER for final shift <<<")
            input(prompt)

            # Show day intro
            clear_screen()
            print(center_in_terminal(BORDER_TOP))
            print_bordered("")
            print_bordered("DAY 8".center(CONTENT_WIDTH))
            print_bordered("Beginning surveillance shift...".center(CONTENT_WIDTH))
            print_bordered("")
            print(center_in_terminal(BORDER_BOTTOM))

            with SkippableAnimation("day_intro") as anim:
                if not anim.check_skip():
                    time.sleep(2)

            # Play through Day 8 truth reveal conversations (no judgment needed)
            for i, conv in enumerate(day8_convs):
                display_conversation(conv)

                # Let player read the conversation before clearing
                prompt = center_in_terminal("\n>>> Press ENTER to continue <<<")
                input(prompt)

                # No judgment for these - just revelations
                clear_screen()
                print(center_in_terminal(BORDER_TOP))
                print_bordered("")
                print_bordered(">>> RECORDING CONVERSATION <<<".center(CONTENT_WIDTH))
                print_bordered("")
                print(center_in_terminal(BORDER_BOTTOM))

                with SkippableAnimation("record_wait") as anim:
                    if not anim.check_skip():
                        time.sleep(1.5)

            # Show daily report for day 8
            blink_eye()
            clear_screen()
            print(center_in_terminal(BORDER_TOP))
            print_bordered("")
            print_bordered("DAY 8 - SHIFT COMPLETE".center(CONTENT_WIDTH))
            print_bordered("")
            print_bordered("You now know the truth.".center(CONTENT_WIDTH))
            print_bordered("The U.P Department doesn't exist.".center(CONTENT_WIDTH))
            print_bordered("It never did.".center(CONTENT_WIDTH))
            print_bordered("")
            print(center_in_terminal(BORDER_BOTTOM))

            with SkippableAnimation("truth_pause") as anim:
                if not anim.check_skip():
                    time.sleep(3)

            prompt = center_in_terminal("\n>>> Press ENTER to continue <<<")
            input(prompt)

            # ============ FINAL CHOICE ============
            share_truth = display_final_choice()

            if share_truth:
                # Good ending
                display_good_ending()
            else:
                # Bad ending: Stayed silent
                display_bad_ending_silence()

        else:
            # Player didn't help rebels - normal ending after day 6
            display_final_evaluation(total_score, initial_days)

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