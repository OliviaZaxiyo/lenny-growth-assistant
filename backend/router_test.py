from router import choose_skill

samples = [
    "How should I price my product early on?",
    "Write an essay on early-stage pricing",
    "Create a landing page about pricing lessons",
    "Turn the essay into an HTML page",
    "Make a checklist of onboarding steps",
    "What do guests say about UI design?",
    "Give me a Ship 30 for 30 style post on hiring",
]
for s in samples:
    skill, reason = choose_skill(s)
    print(f"{skill:12} <- {s}   ({reason})")