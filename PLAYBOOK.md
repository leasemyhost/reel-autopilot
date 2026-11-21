# Reel Autopilot - Playbook (har scheduled run yahi follow kare)

Account: **Jayant Ke Guides** - Hindi/Hinglish tech, AI aur online kamai content, Tier 2/3 India audience.
Goal: roz 3 reels (subah 9, dopahar 1, shaam 7 IST) - views aur followers badhana, bina fake engagement.

## Ek run ka kaam (ek reel)
1. `git pull`. `data/topics_log.json` aur `data/insights.json` padho (kya chala, kya nahi).
2. **Topic research** (WebSearch, 4-8 searches): pichhle 48 ghante ke AI/tech news, naye free AI tools,
   Instagram/YouTube India par trending tech topics, aur "online kamai / AI se kaam" angles.
   - Pichhle 30 din ke topics_log se repeat mat karo.
   - Pillars rotate karo: (a) naya AI tool demo, (b) AI se kamai/side hustle (realistic, bina guarantee),
     (c) phone/PC hack ya productivity trick, (d) tech news jo aam aadmi ko affect kare.
   - Har fact jo reel mein jaaye, uska source verify karo. Agar pakka nahi to reel mein mat daalo.
3. **Script** (`.claude/skills/ig-reel` ka process): 3 hooks likho, `hookscore.py` se score, best chuno.
   35-50 sec, 14-21 lines, ek line = ek idea, hook pehle 2 sec mein, end mein ek keyword CTA.
   - `hi`: poora Devanagari Hindi (English shabd bhi Devanagari: "वेबसाइट", "एआई") - ye voice padhegi.
   - `cap`: Roman Hinglish caption, 2-3 keywords `[Bracket]` mein (bracket ke baad punctuation mat lagao).
   - Income/number claims: sirf math/example ("₹10,000 x 10 = ₹1 lakh"), kabhi guarantee nahi.
     Kisi asli insaan/brand ke naam se jhoothi baat ya fake testimonial nahi.
4. **Spec** `specs/<YYYY-MM-DD>-<slot>.json` likho (format: `specs/example-ai-website.json`).
   6-8 sections, har section 2-3 lines, alag-alag card types (engine/cards.py ki docstrings dekho):
   hero, list_scan, terminal, chat, stats, crosses, compare, steps, big_number, cta (aakhri section hamesha cta).
   Card text chhota rakho (fit_text auto-shrink karta hai, lekin 30 chars se kam best).
5. **Voice**: `python3 tools/tts_gemini.py specs/<id>.json build/<id>` (Sadachbia, $GEMINI_API_KEY).
6. **Preview**: `python3 tools/build_reel.py specs/<id>.json build/<id> --preview` -> `build/<id>/preview/sheet.png`
   ko Read karke dekho: text kat to nahi raha, overlap to nahi, caption sahi. Galti ho to spec theek karo.
7. **Render**: `python3 tools/build_reel.py specs/<id>.json build/<id>` -> `build/<id>/reel.mp4`.
   ffprobe se check: 1080x1920, audio stream, 30-60 sec.
8. **Caption** (`.claude/skills/ig-caption/caption.py` se lint): pehli line hook, 3-5 lines value,
   CTA keyword, 3-5 hashtags. Hinglish.
9. **Queue**: `queue/<id>/` mein `reel.mp4`, `caption.txt`, `meta.json`
   (`{"status":"ready","slot":"morning|noon|evening","created":ISO,"title","topic","hook","sources":[urls]}`).
   `data/topics_log.json` mein topic append. Commit + push (`git -c push.negotiate=true push`).
10. GitHub Actions slot time par apne aap post karega (`.github/workflows/post.yml`).

## Weekly review (Sunday run)
`data/insights.json` padho: views, reach, avg watch time, shares, saves. Top 3 aur bottom 3 reels ke hooks/topics
compare karo, `data/learnings.md` update karo (kaunse pillars, hooks, lengths chal rahe hain). Agle hafte usi hisaab se.

## Rules
- Copyrighted music/images nahi. Sirf engine ke apne visuals aur khud ke SFX/music.
- Kisi real person ki photo/awaaz nahi. Fake reviews/testimonials nahi.
- Medical/legal/financial investment advice nahi.
- Agar koi step fail ho (TTS quota, render error), queue mein kuch mat daalo aur `data/errors.log` mein likh do.
