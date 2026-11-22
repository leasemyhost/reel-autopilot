"""Rules every reel spec must follow, applied automatically before voice + render."""
OUTRO_HI = "ऐसे ही ट्रिक्स के लिए, जयंत के गाइड्स को फ़ॉलो करना न भूलें।"
OUTRO_CAP = "Aise tricks ke liye [Follow] karo"


def ensure_outro(spec):
    """Jayant: har script ke end mein ye line zaroor. Last line replace/append, last section extended."""
    lines = spec["lines"]
    if "जयंत के गाइड्स" in lines[-1]["hi"]:
        return spec
    lines.append({"hi": OUTRO_HI, "cap": OUTRO_CAP})
    spec["sections"][-1]["lines"][1] = len(lines) - 1
    return spec
