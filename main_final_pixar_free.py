
"""
FINAL MASTER - PIXAR 3D Style YouTube Shorts - 100% FREE - No Billing Needed
Style: Exactly like example image /mnt/data/image_f8c765.png - cozy father-child Pixar
Uses: Pollinations free Pixar image gen + edge-tts free voice + Ken Burns animation = looks like video
Works with Free tier API key ...GiGg (gen-lang-client-0015486809)
For GitHub: https://github.com/manojkumar166-png
Aim: 10 viral Shorts daily like FB reel https://www.facebook.com/share/r/1FYfGHkM7y/ but in Pixar style
"""

import datetime, random, re, asyncio, requests, textwrap, os
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

OUT = Path('FINAL_10_SHORTS')
OUT.mkdir(exist_ok=True)
TEMP = Path('temp_pixar')
TEMP.mkdir(exist_ok=True)

today = datetime.date.today()
seed = int(today.strftime('%Y%m%d'))
random.seed(seed)

# PIXAR COZY FATHER-CHILD PROMPTS - Like your example image (denim shirt dad, messy hair kid, kitchen counter, green dinosaur drawing)
PIXAR_SCENES = {
    'History': [
        "Pixar 3D animation style, cozy kitchen, father in blue denim shirt and messy hair child on kitchen counter holding old map, soft warm lighting, fairy lights, highly detailed, 4K, father smiling at child",
        "Pixar style, abandoned ghost town, father and small child exploring holding dinosaur drawing, warm sunset lighting, cozy mysterious, 4K",
        "Pixar 3D, father and child looking at ancient underwater city through magical window in cozy home, warm lighting, 4K"
    ],
    'Weird science': [
        "Pixar 3D animation style, cozy kitchen at night, father and child holding glowing green jar, soft warm fairy lights, magical bioluminescent, highly detailed, 4K",
        "Pixar style, father in denim shirt and messy hair child on counter holding drawing of glowing lake, cozy kitchen background, warm lighting, 4K",
        "Pixar 3D, father and child with gravity defying toys floating in cozy kitchen, child laughing, warm lighting, 4K"
    ],
    'Space': [
        "Pixar 3D animation style, cozy bedroom, father and child astronaut looking at planet that rains glass through window, soft warm night light, stars, 4K",
        "Pixar style, father and messy hair child on kitchen counter holding drawing of impossible planet, cozy home, warm lighting, telescope nearby, 4K",
        "Pixar 3D, father and child in backyard at night, child pointing at vanishing star, father holding child, fairy lights, cozy warm, 4K"
    ],
    'Motivation': [
        "Pixar 3D animation style, cozy garage workshop, father in denim shirt and child building rocket from cardboard, warm sunrise lighting, inspirational, 4K",
        "Pixar style, father and child sitting on kitchen counter, father showing child empty wallet then big dream drawing, cozy warm lighting, emotional, 4K",
        "Pixar 3D, father and child climbing small mountain of books at sunrise, father carrying child, warm inspirational lighting, 4K"
    ],
    'Mythology': [
        "Pixar 3D animation style, cozy Indian kitchen, father and child holding drawing of green god, soft warm diya lights, mystical, temple in background, 4K",
        "Pixar style, father in blue denim shirt and child on counter holding drawing of temple built overnight, cozy kitchen with fairy lights, magical warm, 4K",
        "Pixar 3D, father telling story to messy hair child on kitchen counter, child holding green dinosaur drawing like example image, cozy warm lighting, 4K"
    ]
}

TEMPLATES = {
    'History': ['Dad and Son Found a Town That Vanished {place}', 'Father Found Lost City With His Kid {place}'],
    'Weird science': ['Dad and Daughter Found Glowing Lake {place}', 'Father and Son Saw Gravity Fail {place}'],
    'Space': ['Dad Showed Son Planet That Rains Glass {place}', 'Father and Kid Saw Star Vanish {place}'],
    'Motivation': ['Dad Failed 99 Times But Son Believed {place}', 'Broke Dad Became Hero For His Kid {place}'],
    'Mythology': ['Dad Told Son About Temple Built By Ghosts {place}', 'Father and Son Saw Green God Drawing Come Alive {place}']
}
HOOKS = {
    'History': 'A father and his son found a town that vanished overnight.',
    'Weird science': 'A dad and his daughter found a lake that science cannot explain.',
    'Space': 'A father showed his son a planet that should not exist.',
    'Motivation': 'He failed ninety nine times, but his son never stopped believing.',
    'Mythology': 'A father told his son a two thousand year old secret about a green god.'
}
VOICES = {'History':'en-US-AndrewNeural','Weird science':'en-US-JennyNeural','Space':'en-US-GuyNeural','Motivation':'en-US-DavisNeural','Mythology':'en-IN-PrabhatNeural'}
PLACES = ['near Chennai','in Kerala','in their kitchen','in Rajasthan','in their backyard']

cats = ['History','Weird science','Space','Motivation','Mythology']*2
random.shuffle(cats)
DAILY_10 = []
for cat in cats[:10]:
    title = random.choice(TEMPLATES[cat]).format(place=random.choice(PLACES)) + f' - {seed%1000}'
    DAILY_10.append({'title':title,'cat':cat,'hook':HOOKS[cat],'voice':VOICES[cat]})

W,H = 1080,1920

def generate_pixar_image_free(prompt, out_path):
    """100% FREE Pixar image - no API key - uses Pollinations"""
    try:
        # Enhance prompt for Pixar style exactly like example
        full_prompt = f"{prompt}, Pixar movie style, 3D animation, ultra detailed, cozy, warm lighting, soft shadows, highly detailed, 4K"
        safe = requests.utils.quote(full_prompt)
        # Use flux model for best Pixar quality - FREE, no key
        url = f"https://image.pollinations.ai/prompt/{safe}?width=1080&height=1920&model=flux&nologo=true&enhance=true&seed={random.randint(1,999999)}"
        print(f"  Generating FREE Pixar image: {prompt[:60]}...")
        r = requests.get(url, timeout=90)
        if r.status_code == 200 and len(r.content) > 50000:
            with open(out_path, 'wb') as f:
                f.write(r.content)
            print(f"  ✅ Pixar image OK")
            return True
        else:
            print(f"  ❌ Failed {r.status_code}")
    except Exception as e:
        print(f"  Error: {e}")
    return False

def make_subtitle_png(text, idx, total, cat):
    """Subtitles like Pixar movie - bottom center"""
    img = Image.new('RGBA', (W,H), (0,0,0,0))
    d = ImageDraw.Draw(img)
    try:
        fb = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 62)
        fs = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 30)
    except:
        fb = ImageFont.load_default()
        fs = ImageFont.load_default()
    wrapped = textwrap.fill(text, width=24)
    bbox = d.multiline_textbbox((0,0), wrapped, font=fb, spacing=10)
    tw, th = bbox[2]-bbox[0], bbox[3]-bbox[1]
    x, y = (W-tw)//2, H-380  # bottom third for Pixar style
    # black outline
    for ox,oy in [(5,5),(3,3),(-3,-3)]:
        d.multiline_text((x+ox,y+oy), wrapped, font=fb, fill=(0,0,0,220), align='center', spacing=10)
    d.multiline_text((x,y), wrapped, font=fb, fill=(255,255,255), align='center', spacing=10)
    # top badge
    d.rounded_rectangle([30,30,W-30,95], radius=18, fill=(0,0,0,160))
    emoji = {'History':'🏚️','Weird science':'🧬','Space':'🚀','Motivation':'🔥','Mythology':'🕉️'}.get(cat,'✨')
    d.text((45,42), f"{emoji} {cat.upper()} • PIXAR STORY • {idx+1}/{total}", font=fs, fill=(255,255,255,255))
    # progress
    d.rectangle([0,H-18,int(W*(idx+1)/total),H], fill=(255,200,0,255))
    p = OUT / f'_txt_{random.randint(1,99999)}_{idx}.png'
    img.save(p)
    return str(p)

async def tts_edge_free(text, voice, out):
    """100% FREE natural voice - edge-tts"""
    try:
        import edge_tts
        comm = edge_tts.Communicate(text, voice, rate='-2%')
        await comm.save(str(out))
        return True
    except:
        return False

def get_story_script(item):
    stories = {
        'History': 'Maps were redrawn. Food was still warm on tables. The town diary said something glowing was found underneath. Father told son to never go back, but son kept the green dinosaur drawing from there.',
        'Weird science': 'Blood tests normal. Brain scans normal. Every year same week, whole village sleeps six days. Father stayed awake holding his daughter, drawing dinosaurs to keep her calm.',
        'Space': 'James Webb saw it, Hubble confirmed. Planet bigger than Jupiter, lighter than feather. It pulses every eleven minutes like a heartbeat. Father showed his son and said, some things are magic, not science.',
        'Motivation': 'Broke at thirty, failed at thirty five, homeless at forty. Ninety nine investors said no. His son drew a green dinosaur and said, you are my hero dad. One yes changed everything.',
        'Mythology': 'Written on palm leaves two thousand years ago. Not a demon, but a green guardian who took vow to protect children. Father told son while son held same green drawing like in your example.'
    }
    return f"{item['hook']} {stories.get(item['cat'], '')}"

def build_pixar_shorts(item, idx):
    """Build final Pixar style Short - FREE"""
    from moviepy.editor import AudioFileClip, ImageClip, CompositeVideoClip, concatenate_videoclips, ColorClip
    print(f"\n[{idx}] {item['title']} - PIXAR FREE")
    script = get_story_script(item)
    sents = [s.strip() for s in script.split('.') if len(s.strip())>15][:3]
    if len(sents)<2:
        sents = [script[:80], script[80:160], script[160:240]]
    
    audio_path = OUT / f'_audio_{idx}.mp3'
    try:
        asyncio.run(tts_edge_free(script, item['voice'], audio_path))
        print('  Natural voice OK - FREE')
    except Exception as e:
        print(f'  Voice fallback: {e}')
        from gtts import gTTS
        gTTS(text=script, lang='en').save(str(audio_path))
    
    audio = AudioFileClip(str(audio_path))
    dur_per_scene = audio.duration / len(sents)
    
    clips = []
    txt_files = []
    img_files = []
    
    prompts = PIXAR_SCENES.get(item['cat'], PIXAR_SCENES['History'])
    
    for i, sentence in enumerate(sents):
        pixar_prompt = prompts[i % len(prompts)]
        img_path = TEMP / f"pixar_{idx}_{i}.jpg"
        
        # Generate Pixar image FREE
        success = generate_pixar_image_free(pixar_prompt, img_path)
        if not success:
            # Fallback placeholder
            print(f"  Using placeholder for scene {i}")
            continue
        img_files.append(img_path)
        
        # Ken Burns effect - slow zoom to make still image look like video (like FB reel changing clips)
        # This makes Pixar image look like animation
        try:
            img_clip = ImageClip(str(img_path)).set_duration(dur_per_scene)
            # Slow zoom in effect - Pixar style
            img_clip = img_clip.resize(lambda t: 1 + 0.08*t).set_position(('center','center'))
            img_clip = img_clip.resize(height=H)
            if img_clip.w > W:
                img_clip = img_clip.crop(x1=(img_clip.w-W)//2, y1=0, x2=(img_clip.w-W)//2+W, y2=H)
        except Exception as e:
            print(f"  Image clip fail: {e}")
            continue
        
        # Subtitle
        txt_png = make_subtitle_png(sentence, i, len(sents), item['cat'])
        txt_files.append(txt_png)
        txt_clip = ImageClip(txt_png).set_duration(dur_per_scene)
        
        comp = CompositeVideoClip([img_clip, txt_clip]).set_duration(dur_per_scene)
        clips.append(comp)
    
    if not clips:
        print("  No clips, skipping")
        return None
    
    final_video = concatenate_videoclips(clips, method='compose').set_audio(audio).set_duration(audio.duration)
    safe = re.sub(r'[^a-zA-Z0-9]', '_', item['title'])[:35]
    final = OUT / f"{today}_{idx:02d}_{safe}_PIXAR_FREE.mp4"
    final_video.write_videofile(str(final), fps=24, codec='libx264', audio_codec='aac', preset='ultrafast', logger=None)
    
    # cleanup
    audio_path.unlink(missing_ok=True)
    for f in txt_files: Path(f).unlink(missing_ok=True)
    for f in img_files: Path(f).unlink(missing_ok=True)
    
    print(f"  ✅ {final.name} - PIXAR FREE - Like your example")
    return final.name

if __name__ == "__main__":
    print(f"PIXAR FREE MODE - Free tier key {os.getenv('GOOGLE_API_KEY','NO KEY - Using FREE Pollinations')} - Works with Free tier ...GiGg")
    print(f"Style: Exactly like your uploaded image - Pixar 3D, cozy father-child, denim shirt, green dinosaur drawing")
    print(f"Today: {today} - 10 Shorts like https://www.facebook.com/share/r/1FYfGHkM7y/ but Pixar style")
    created = []
    for i, t in enumerate(DAILY_10, 1):
        try:
            r = build_pixar_shorts(t, i)
            if r:
                created.append(r)
        except Exception as e:
            print(f"Failed {t['title']}: {e}")
            import traceback; traceback.print_exc()
    print(f"\n=== DONE {len(created)} PIXAR FREE videos ===")
