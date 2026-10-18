
def generate_facts(topic: str):
    print(f"-> Generating facts for: {topic} (OFFLINE MODE - No API needed)")
    import random
    
    # Curated facts database - no API needed
    database = {
        "black holes": [
            "A black hole's gravity is so strong that not even light can escape it.",
            "Time slows down near a black hole due to extreme gravitational forces.",
            "The largest black hole discovered is 40 billion times the mass of our sun."
        ],
        "default": [
            f"{topic} can be more fascinating than you ever imagined.",
            f"Scientists are still discovering new secrets about {topic} every day.",
            f"The most interesting thing about {topic} will blow your mind."
        ]
    }
    
    key = topic.lower()
    if key in database:
        facts = database[key]
    else:
        # Generate generic but interesting facts
        facts = [
            f"Did you know {topic} is more mysterious than 99% of people realize?",
            f"The biggest myth about {topic} is completely wrong according to science.",
            f"{topic} holds a secret that scientists only recently discovered."
        ]
    
    print(f"OK Generated: {facts}")
    return facts
