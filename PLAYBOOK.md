# Reel Autopilot - Playbook (har scheduled run yahi follow kare)

Account: **Jayant Ke Guides** - Hindi/Hinglish tech, AI aur online kamai content, Tier 2/3 India audience.
Goal: roz 3 reels (subah 9, dopahar 1, shaam 7 IST) - views aur followers badhana, bina fake engagement.

## Ek run ka kaam (ek reel)
1. `git pull`. `data/topics_log.json` aur `data/insights.json` padho (kya chala, kya nahi).
2. **Topic research** (WebSearch, 4-8 searches): pichhle 48 ghante ke AI/tech news, naye free AI tools,
   Instagram/YouTube India par trending tech topics, aur "online kamai / AI se kaam" angles.
   - Pichhle 30 din ke topics_log se repeat mat karo.
   - `data/learnings.md` sabse pehle padho. Abhi tak sabse strong: **"FREE AI tool/credits/jugaad + comment keyword"** (5x views).
   - Pillars (weight): (a) **FREE AI tool / free credits / free alternative** 40%, (b) Claude/ChatGPT/Gemini ka
     naya feature ya hidden trick 25%, (c) AI se kaam/kamai (realistic, bina guarantee) 20%, (d) AI/tech news jo aam
     aadmi ko affect kare 15%. Sirf AI/tech niche - personal/food/travel nahi.
   - "Free" claim tabhi jab official source se verified ho (pricing page, official blog). Limit/condition reel mein bolo.
   - Har fact jo reel mein jaaye, uska source verify karo. Agar pakka nahi to reel mein mat daalo.
3. **Script** (`.claude/skills/ig-reel` ka process): 3 hooks likho, `hookscore.py` se score, best chuno.
   30-45 sec, 12-18 lines, ek line = ek idea, hook pehle 2 sec mein.
   - CTA: **"Follow karo + Save karo"** (default). Comment-keyword DM CTA ("Comment FREE") sirf tab jab
     `data/dm_automation.json` mein `"enabled": true` ho - warna DM ka vaada mat karo.
   - `hi`: poora Devanagari Hindi (English shabd bhi Devanagari: "वेबसाइट", "एआई") - ye voice padhegi.
   - `cap`: Roman Hinglish caption, 2-3 keywords `[Bracket]` mein (bracket ke baad punctuation mat lagao).
   - Income/number claims: sirf math/example ("₹10,000 x 10 = ₹1 lakh"), kabhi guarantee nahi.
     Kisi asli insaan/brand ke naam se jhoothi baat ya fake testimonial nahi.
4. **Spec** `specs/pending/<YYYY-MM-DD>-<slot>.json` likho (format: `specs/example-ai-website.json`, `"slot"` field zaroori).
   6-8 sections, har section 2-3 lines, alag-alag card types (engine/cards.py ki docstrings dekho):
   hero, list_scan, terminal, chat, stats, crosses, compare, steps, big_number, cta (aakhri section hamesha cta).
   Card text chhota rakho (30 chars se kam best). `caption` field mein poora Instagram caption
   (`.claude/skills/ig-caption/caption.py` se lint: pehli line hook, value lines, CTA keyword, 3-5 hashtags).
   - **Trending tags/keywords** (2-3 searches): is topic ke liye abhi India mein kya search/trend ho raha hai
     (tool ka naam, "free", "AI tools", Hindi keywords). Caption ki pehli 2 lines mein 2-3 search keywords
     naturally daalo (IG search keywords se rank karta hai). Hashtags 3-5: 1 broad (#aitools), 2 niche
     (#chatgpthindi, #aitoolsforfree), 1-2 topic-specific/trending (tool ya event ka naam). 30 hashtags spam nahi.
5. **Layout check** (is cloud se Gemini block hai, isliye voice yahan nahi banti):
   `python3 tools/build_reel.py specs/pending/<id>.json build/<id> --estimate --preview` ->
   `build/<id>/preview/sheet.png` Read karke dekho: text kat to nahi raha, overlap nahi, captions sahi. Galti ho to spec theek karo.
6. `data/topics_log.json` mein topic append. Commit + push (`git -c push.negotiate=true push`). `build/` commit mat karo.
7. GitHub Actions:
   - `build.yml` post se **2 ghante pehle** (07:00 / 11:00 / 17:00 IST): Sadachbia voice (Gemini) -> render -> checks -> ready artifact.
   - `post.yml` **exact time** (09:00 / 13:00 / 19:00 IST): ready reel Instagram par post -> `posted/<id>/meta.json`.
     Ready reel na mile to wahi build + post kar deta hai (fallback).
   - Isliye ye Claude run slot se kam se kam 3 ghante pehle spec push kare (05:20 / 09:20 / 15:20 IST).

## Weekly review (Sunday run)
`data/insights.json` padho: views, reach, avg watch time, shares, saves. Top 3 aur bottom 3 reels ke hooks/topics
compare karo, `data/learnings.md` update karo (kaunse pillars, hooks, lengths chal rahe hain). Agle hafte usi hisaab se.

## Rules
- Copyrighted music/images nahi. Sirf engine ke apne visuals aur khud ke SFX/music.
- Kisi real person ki photo/awaaz nahi. Fake reviews/testimonials nahi.
- Medical/legal/financial investment advice nahi.
- Agar koi step fail ho (TTS quota, render error), queue mein kuch mat daalo aur `data/errors.log` mein likh do.
