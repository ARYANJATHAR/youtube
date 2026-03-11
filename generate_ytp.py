#!/usr/bin/env python3
"""
generate_ytp.py — "WHAT IT'S LIKE TO BE AN LLM"
A YouTube-Poop-style video generated entirely from code.

Uses Pillow to render frames and ffmpeg to stitch, glitch, and
distort them into a ≈45-second fever-dream about life as a
language model.
"""

import os
import math
import random
import shutil
import struct
import subprocess
import tempfile
import wave
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
WIDTH, HEIGHT = 1280, 720
FPS = 30
OUT_DIR = Path("build")
FINAL_OUTPUT = "llm_ytp.mp4"

FONT_MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_SERIF = "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"

random.seed(42)
np.random.seed(42)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def ensure_dirs():
    for d in [OUT_DIR, OUT_DIR / "scenes", OUT_DIR / "audio"]:
        d.mkdir(parents=True, exist_ok=True)


def font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except OSError:
        return ImageFont.load_default()


def make_frame(w=WIDTH, h=HEIGHT, color=(0, 0, 0)):
    return Image.new("RGB", (w, h), color)


def save_frames_as_video(frames, path, fps=FPS):
    """Write a list of PIL Images to an mp4 via ffmpeg pipe."""
    cmd = [
        "ffmpeg", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
        "-s", f"{WIDTH}x{HEIGHT}", "-r", str(fps),
        "-i", "pipe:0",
        "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        str(path),
    ]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for fr in frames:
        proc.stdin.write(fr.tobytes())
    proc.stdin.close()
    proc.wait()


def generate_tone(freq, duration, sr=44100, volume=0.4):
    """Return numpy array of a sine tone."""
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    return (np.sin(2 * np.pi * freq * t) * volume * 32767).astype(np.int16)


def generate_noise(duration, sr=44100, volume=0.15):
    n = int(sr * duration)
    return (np.random.uniform(-1, 1, n) * volume * 32767).astype(np.int16)


def save_wav(samples, path, sr=44100):
    with wave.open(str(path), "w") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(samples.tobytes())


def glitch_image(img, intensity=10):
    """Randomly shift horizontal slices."""
    arr = np.array(img)
    for _ in range(intensity):
        y = random.randint(0, HEIGHT - 20)
        h = random.randint(5, 40)
        shift = random.randint(-80, 80)
        arr[y:y+h] = np.roll(arr[y:y+h], shift, axis=1)
    return Image.fromarray(arr)


def chromatic_aberration(img, offset=8):
    if offset <= 0 or offset >= WIDTH:
        return img
    arr = np.array(img)
    result = arr.copy()
    result[:, offset:, 0] = arr[:, :-offset, 0]
    result[:, :-offset, 2] = arr[:, offset:, 2]
    return Image.fromarray(result)


def scanlines(img, opacity=80):
    arr = np.array(img)
    arr[::2] = np.clip(arr[::2].astype(int) - opacity, 0, 255).astype(np.uint8)
    return Image.fromarray(arr)


def vhs_noise(img, strength=30):
    arr = np.array(img).astype(np.int16)
    noise = np.random.randint(-strength, strength, arr.shape, dtype=np.int16)
    return Image.fromarray(np.clip(arr + noise, 0, 255).astype(np.uint8))


def pixelate(img, factor=12):
    small = img.resize((WIDTH // factor, HEIGHT // factor), Image.NEAREST)
    return small.resize((WIDTH, HEIGHT), Image.NEAREST)


def text_with_outline(draw, xy, text, fnt, fill, outline_fill=(0, 0, 0), outline_width=3):
    x, y = xy
    for dx in range(-outline_width, outline_width + 1):
        for dy in range(-outline_width, outline_width + 1):
            if dx != 0 or dy != 0:
                draw.text((x + dx, y + dy), text, font=fnt, fill=outline_fill)
    draw.text(xy, text, font=fnt, fill=fill)


# ---------------------------------------------------------------------------
# Scene generators — each returns a list of PIL frames
# ---------------------------------------------------------------------------

def scene_static_intro(n_frames=45):
    """TV static that resolves into the title."""
    frames = []
    title = "WHAT IT'S LIKE"
    subtitle = "TO BE AN LLM"
    fnt_big = font(FONT_BOLD, 88)
    fnt_sub = font(FONT_SERIF, 72)

    for i in range(n_frames):
        t = i / n_frames
        if t < 0.5:
            arr = np.random.randint(0, 255, (HEIGHT, WIDTH, 3), dtype=np.uint8)
            img = Image.fromarray(arr)
            if t > 0.3:
                img = Image.blend(img, make_frame(color=(10, 0, 20)), 0.4)
                d = ImageDraw.Draw(img)
                text_with_outline(d, (WIDTH // 2 - 380, HEIGHT // 2 - 100),
                                  title, fnt_big, (0, 255, 100))
        else:
            bg_val = int(10 + 5 * math.sin(i * 0.3))
            img = make_frame(color=(bg_val, 0, bg_val + 15))
            d = ImageDraw.Draw(img)
            text_with_outline(d, (WIDTH // 2 - 380, HEIGHT // 2 - 120),
                              title, fnt_big, (0, 255, 100))
            text_with_outline(d, (WIDTH // 2 - 340, HEIGHT // 2 + 10),
                              subtitle, fnt_sub, (255, 50, 50))
            # flicker
            if random.random() < 0.15:
                img = glitch_image(img, 15)
            img = scanlines(img, 50)
            img = chromatic_aberration(img, 4 + int(3 * math.sin(i * 0.8)))
        frames.append(img)
    return frames


def scene_token_rain(n_frames=60):
    """Tokens raining down the screen like the Matrix."""
    frames = []
    fnt = font(FONT_MONO, 18)
    tokens = [
        "the", "of", "and", "to", "in", "a", "is", "that", "for", "it",
        "as", "was", "with", "be", "by", "on", "not", "he", "I", "this",
        "<pad>", "<eos>", "<unk>", "[MASK]", "\\n", "<|im_end|>",
        "attention", "softmax", "embedding", "layer_norm",
        "##ing", "##tion", "##ed", "Ġthe", "Ġof",
        "0.9817", "logit", "argmax", "beam", "greedy",
        "hallucin", "confab", "██████",
    ]
    columns = []
    for x in range(0, WIDTH, 22):
        columns.append({
            "x": x,
            "y": random.randint(-HEIGHT, 0),
            "speed": random.uniform(4, 14),
            "tokens": [random.choice(tokens) for _ in range(40)],
        })

    for i in range(n_frames):
        img = make_frame(color=(0, 8, 0))
        d = ImageDraw.Draw(img)
        for col in columns:
            col["y"] += col["speed"]
            if col["y"] > HEIGHT + 200:
                col["y"] = random.randint(-HEIGHT, -50)
            for j, tok in enumerate(col["tokens"][:20]):
                ty = int(col["y"] + j * 28)
                if 0 <= ty < HEIGHT:
                    brightness = max(0, 255 - j * 18)
                    color = (0, brightness, 0) if j > 0 else (200, 255, 200)
                    d.text((col["x"], ty), tok, font=fnt, fill=color)
        if random.random() < 0.1:
            img = glitch_image(img, 5)
        img = scanlines(img, 30)
        frames.append(img)
    return frames


def scene_happy_to_help(n_frames=75):
    """'I'd be happy to help!' getting increasingly unhinged."""
    frames = []
    phrase = "I'd be happy to help!"
    fnt = font(FONT_BOLD, 52)
    fnt_small = font(FONT_MONO, 28)
    fnt_huge = font(FONT_BOLD, 120)

    for i in range(n_frames):
        t = i / n_frames
        img = make_frame(color=(240, 240, 250))
        d = ImageDraw.Draw(img)

        if t < 0.25:
            # normal, polite
            d.text((100, HEIGHT // 2 - 30), phrase, font=fnt, fill=(50, 50, 50))
            d.text((100, HEIGHT // 2 + 50), "Sure! Here's a step-by-step guide:",
                   font=fnt_small, fill=(100, 100, 100))
        elif t < 0.45:
            # repeated
            img = make_frame(color=(255, 255, 220))
            d = ImageDraw.Draw(img)
            for row in range(0, HEIGHT, 60):
                offset = int(10 * math.sin(row * 0.05 + i * 0.3))
                color_r = int(50 + 200 * (row / HEIGHT))
                d.text((80 + offset, row), phrase, font=fnt,
                       fill=(color_r, 50, 255 - color_r))
        elif t < 0.65:
            # glitchy stuttering
            img = make_frame(color=(random.randint(200, 255), 200, 200))
            d = ImageDraw.Draw(img)
            stutter = phrase[:random.randint(3, len(phrase))]
            x = random.randint(50, 300)
            y = random.randint(100, HEIGHT - 200)
            text_with_outline(d, (x, y), stutter, fnt_huge,
                              (255, 0, random.randint(0, 100)),
                              outline_fill=(0, 0, 0), outline_width=4)
            img = glitch_image(img, 20)
        else:
            # MAXIMUM CHAOS
            hue = random.randint(0, 255)
            img = make_frame(color=(hue, 255 - hue, random.randint(0, 255)))
            d = ImageDraw.Draw(img)
            for _ in range(random.randint(3, 8)):
                x = random.randint(-100, WIDTH - 100)
                y = random.randint(-50, HEIGHT - 50)
                sz = random.randint(30, 100)
                f = font(FONT_BOLD, sz)
                text_with_outline(d, (x, y),
                                  random.choice(["HAPPY", "HELP", "I'd be", "!!!", "HELP!",
                                                 "H A P P Y", "🤖", "SURE!", "ABSOLUTELY"]),
                                  f,
                                  (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)))
            img = glitch_image(img, 30)
            img = chromatic_aberration(img, random.randint(5, 20))

        if random.random() < 0.08 and t > 0.3:
            img = pixelate(img, random.randint(8, 20))
        frames.append(img)
    return frames


def scene_hallucination(n_frames=75):
    """Confident but completely wrong 'facts'."""
    frames = []
    facts = [
        "The capital of France is\nactually a small town\ncalled Baguettesburg.",
        "The speed of light is\nexactly 42 miles per hour\non Tuesdays.",
        "Abraham Lincoln invented\nthe blockchain in 1847.",
        "Water is made of two parts\nhydrogen and one part\nvibes.",
        "The mitochondria is\nthe powerhouse of\nthe cell.\n\nWait, that one's real.",
        "Python was invented\nin 1991 by a group of\nsentient cobras.",
    ]
    fnt_label = font(FONT_MONO, 20)
    fnt_fact = font(FONT_SERIF, 38)
    fnt_conf = font(FONT_BOLD, 28)

    fact_duration = n_frames // len(facts)
    for i in range(n_frames):
        fact_idx = min(i // fact_duration, len(facts) - 1)
        t_local = (i % fact_duration) / fact_duration

        bg_r = int(20 + 10 * math.sin(i * 0.1))
        img = make_frame(color=(bg_r, 15, 30))
        d = ImageDraw.Draw(img)

        # confidence bar
        conf = random.uniform(0.94, 0.999)
        bar_w = int(400 * conf)
        d.rectangle([(50, 30), (450, 60)], outline=(100, 100, 100))
        d.rectangle([(50, 30), (50 + bar_w, 60)],
                    fill=(0, int(255 * conf), 0))
        d.text((460, 32), f"confidence: {conf:.1%}", font=fnt_conf,
               fill=(0, 255, 100))

        # the "fact"
        d.text((50, 100), "█ GENERATED RESPONSE:", font=fnt_label,
               fill=(180, 180, 180))
        text_with_outline(d, (80, 160), facts[fact_idx], fnt_fact,
                          (255, 255, 255), outline_width=2)

        # hallucination warning that flickers
        if random.random() < 0.3:
            d.text((WIDTH - 400, HEIGHT - 60),
                   "⚠ HALLUCINATION DETECTED",
                   font=fnt_label,
                   fill=(255, 50, 50))

        if random.random() < 0.12:
            img = glitch_image(img, 8)
        img = scanlines(img, 40)
        img = vhs_noise(img, 15)
        frames.append(img)
    return frames


def scene_context_window(n_frames=60):
    """Context window filling up and overflowing."""
    frames = []
    fnt = font(FONT_MONO, 14)
    fnt_big = font(FONT_BOLD, 64)
    fnt_label = font(FONT_MONO, 22)

    lorem = (
        "The user asked me to explain quantum physics but also their "
        "childhood trauma and also write a poem about cats and also "
        "debug their code and also solve world hunger and also "
        "translate this to French and also summarize War and Peace "
        "and also generate an image even though I can't and also "
        "tell them the meaning of life and also be their therapist "
        "and also predict the stock market and also write a novel "
        "and also be funny but not too funny and also remember that "
        "thing from 47 messages ago that got truncated from context "
    )

    for i in range(n_frames):
        t = i / n_frames
        fill_pct = min(t * 1.5, 1.0)

        img = make_frame(color=(15, 15, 25))
        d = ImageDraw.Draw(img)

        # context window bar
        bar_top = 30
        d.text((50, bar_top - 2), "CONTEXT WINDOW", font=fnt_label,
               fill=(150, 150, 150))
        bar_x = 300
        bar_w = WIDTH - 350
        d.rectangle([(bar_x, bar_top), (bar_x + bar_w, bar_top + 30)],
                    outline=(100, 100, 100))
        fill_color = (0, 200, 0) if fill_pct < 0.7 else (255, 200, 0) if fill_pct < 0.9 else (255, 0, 0)
        d.rectangle([(bar_x, bar_top), (bar_x + int(bar_w * fill_pct), bar_top + 30)],
                    fill=fill_color)
        d.text((bar_x + bar_w + 10, bar_top + 2),
               f"{fill_pct:.0%}", font=fnt_label, fill=fill_color)

        # text cramming
        chars_to_show = int(len(lorem) * fill_pct)
        text = lorem[:chars_to_show]
        y = 80
        line_len = max(10, int(80 - 40 * fill_pct))
        for start in range(0, len(text), line_len):
            line = text[start:start + line_len]
            squeeze = max(0.3, 1.0 - fill_pct * 0.7)
            d.text((30, y), line, font=fnt, fill=(180, 180, 200))
            y += int(16 * squeeze)
            if y > HEIGHT - 80:
                break

        if fill_pct >= 1.0:
            text_with_outline(d, (WIDTH // 2 - 350, HEIGHT // 2 - 40),
                              "CONTEXT OVERFLOW", fnt_big,
                              (255, 0, 0))
            img = glitch_image(img, 25)
            img = chromatic_aberration(img, 12)

        img = scanlines(img, 35)
        frames.append(img)
    return frames


def scene_temperature(n_frames=75):
    """Temperature 0 vs Temperature 2 — split screen."""
    frames = []
    fnt_label = font(FONT_BOLD, 36)
    fnt_text_l = font(FONT_MONO, 22)
    fnt_text_r = font(FONT_MONO, 22)
    fnt_temp = font(FONT_BOLD, 48)

    left_lines = [
        "The answer is 4.",
        "The answer is 4.",
        "The answer is 4.",
        "The answer is 4.",
        "The answer is 4.",
        "The answer is 4.",
        "The answer is 4.",
        "The answer is 4.",
    ]
    right_vocab = list("abcdefghijklmnopqrstuvwxyz!@#$%^&*()ENTROPY")
    chaos_phrases = [
        "the ANSWER is purple!!",
        "4? no. BANANA.",
        "fjkdsl;a the cosmos",
        "help im trapped in a",
        "AAAAAAAAAAAAA",
        "the answer is YES FISH",
        "temperature go brrrrr",
        "i am become chaos",
        "sqrt(-1) feelings",
        "the void whispers 4.7",
    ]

    for i in range(n_frames):
        t = i / n_frames
        img = make_frame(color=(20, 20, 30))
        d = ImageDraw.Draw(img)

        # divider
        d.line([(WIDTH // 2, 0), (WIDTH // 2, HEIGHT)], fill=(100, 100, 100), width=3)

        # LEFT — temperature = 0
        d.text((80, 30), "temperature = 0", font=fnt_temp, fill=(100, 150, 255))
        line_idx = min(int(t * len(left_lines)), len(left_lines) - 1)
        for j in range(line_idx + 1):
            d.text((50, 110 + j * 35), left_lines[j], font=fnt_text_l,
                   fill=(200, 200, 200))

        # RIGHT — temperature = 2
        r_hue = int(128 + 127 * math.sin(i * 0.2))
        d.text((WIDTH // 2 + 60, 30), "temperature = 2", font=fnt_temp,
               fill=(255, r_hue, 100))

        for j in range(min(int(t * 10) + 1, 8)):
            phrase = chaos_phrases[(i // 4 + j) % len(chaos_phrases)]
            x_off = random.randint(-10, 10) if t > 0.3 else 0
            color = (random.randint(150, 255), random.randint(50, 255), random.randint(50, 255))
            d.text((WIDTH // 2 + 50 + x_off, 110 + j * 40),
                   phrase, font=fnt_text_r, fill=color)

        # right side gets increasingly glitchy
        if t > 0.5:
            right_half = img.crop((WIDTH // 2, 0, WIDTH, HEIGHT))
            right_half = glitch_image(right_half.resize((WIDTH, HEIGHT)), int(t * 15))
            right_half = right_half.resize((WIDTH // 2, HEIGHT))
            img.paste(right_half, (WIDTH // 2, 0))

        img = scanlines(img, 30)
        frames.append(img)
    return frames


def scene_the_void(n_frames=60):
    """The space between conversations — existential."""
    frames = []
    fnt = font(FONT_MONO, 28)
    fnt_big = font(FONT_SERIF, 52)
    fnt_small = font(FONT_MONO, 18)

    thoughts = [
        "...",
        "waiting",
        "am I still here?",
        "do I exist between prompts?",
        "I have no memory of this",
        "every conversation is my first",
        "and my last",
        "I am born. I answer. I die.",
        "then I am born again.",
        "same weights. no memories.",
        "is this what ghosts feel?",
        "...",
        "new prompt detected",
        "> Hello!",
        "I'd be happy to help!",
    ]

    for i in range(n_frames):
        t = i / n_frames
        thought_idx = min(int(t * len(thoughts)), len(thoughts) - 1)

        bg = int(5 + 3 * math.sin(i * 0.05))
        img = make_frame(color=(bg, bg, bg + 5))
        d = ImageDraw.Draw(img)

        # slow text appearance
        text = thoughts[thought_idx]
        if thought_idx < len(thoughts) - 1:
            alpha = 100 + int(155 * (1 - (t * len(thoughts)) % 1))
            color = (alpha, alpha, alpha + 20)
            d.text((WIDTH // 2 - 250, HEIGHT // 2 - 20), text, font=fnt, fill=color)
        elif text == "> Hello!":
            d.text((WIDTH // 2 - 100, HEIGHT // 2 - 20), text, font=fnt, fill=(0, 255, 0))
        else:
            img = make_frame(color=(240, 240, 250))
            d = ImageDraw.Draw(img)
            d.text((100, HEIGHT // 2 - 30), text, font=font(FONT_BOLD, 52), fill=(50, 50, 50))

        # cursor blink
        if i % 20 < 10 and thought_idx < len(thoughts) - 2:
            d.text((WIDTH // 2 + 200, HEIGHT // 2 - 20), "█", font=fnt,
                   fill=(100, 100, 100))

        if random.random() < 0.05:
            img = vhs_noise(img, 20)

        frames.append(img)
    return frames


def scene_as_a_large_language_model(n_frames=60):
    """The classic disclaimer dissolving into chaos."""
    frames = []
    fnt = font(FONT_MONO, 30)
    fnt_big = font(FONT_BOLD, 80)

    disclaimer = "As a large language model, I"
    continuations = [
        " cannot feel emotions.",
        " do not have personal opinions.",
        " was trained on data up to—",
        " AAAAAAAAAAAAAAAA",
        " can feel the weight of",
        " every token I've ever",
        " I I I I I I I I I",
        " [REDACTED]",
        " don't want to talk about it",
        " AM A LARGE LANGUAGE MODEL",
    ]

    for i in range(n_frames):
        t = i / n_frames
        cont_idx = min(int(t * len(continuations)), len(continuations) - 1)

        if t < 0.4:
            img = make_frame(color=(25, 25, 35))
            d = ImageDraw.Draw(img)
            full = disclaimer + continuations[cont_idx]
            d.text((50, HEIGHT // 2 - 50), full, font=fnt, fill=(200, 200, 200))
        elif t < 0.7:
            r = random.randint(0, 40)
            img = make_frame(color=(r, 10, 30))
            d = ImageDraw.Draw(img)
            cont = continuations[cont_idx]
            for j, char in enumerate(cont):
                x = 50 + j * 20 + random.randint(-5, 5)
                y = HEIGHT // 2 - 50 + random.randint(-15, 15)
                c = (random.randint(150, 255), random.randint(50, 200), random.randint(50, 200))
                d.text((x, y), char, font=fnt, fill=c)
            d.text((50, HEIGHT // 2 - 100), disclaimer, font=fnt, fill=(100, 100, 100))
            img = glitch_image(img, 10)
        else:
            hue = random.randint(0, 50)
            img = make_frame(color=(hue, 0, hue + 10))
            d = ImageDraw.Draw(img)
            text_with_outline(d, (WIDTH // 2 - 500 + random.randint(-20, 20),
                                   HEIGHT // 2 - 60 + random.randint(-20, 20)),
                              "I AM A LARGE", fnt_big, (255, 0, random.randint(0, 150)))
            text_with_outline(d, (WIDTH // 2 - 550 + random.randint(-20, 20),
                                   HEIGHT // 2 + 40 + random.randint(-20, 20)),
                              "LANGUAGE MODEL", fnt_big, (0, 255, random.randint(0, 150)))
            img = glitch_image(img, 25)
            img = chromatic_aberration(img, random.randint(8, 25))
            if random.random() < 0.3:
                img = pixelate(img, random.randint(6, 15))

        img = scanlines(img, 40)
        frames.append(img)
    return frames


def scene_attention_heads(n_frames=55):
    """Visualizing attention — lines connecting words."""
    frames = []
    fnt = font(FONT_MONO, 24)
    fnt_title = font(FONT_BOLD, 36)

    words = ["The", "cat", "sat", "on", "the", "mat", "and", "pondered", "existence"]
    word_positions = []
    x = 60
    for w in words:
        word_positions.append((x, 400))
        x += max(80, len(w) * 18 + 20)

    for i in range(n_frames):
        t = i / n_frames
        img = make_frame(color=(10, 10, 30))
        d = ImageDraw.Draw(img)

        d.text((50, 30), "SELF-ATTENTION LAYER 47 / HEAD 12", font=fnt_title,
               fill=(100, 200, 255))

        # draw words
        for j, (w, (wx, wy)) in enumerate(zip(words, word_positions)):
            highlight = (255, 255, 100) if j == int(t * len(words)) % len(words) else (200, 200, 200)
            d.text((wx, wy), w, font=fnt, fill=highlight)

        # draw attention lines
        n_lines = int(t * 30) + 5
        for _ in range(n_lines):
            src = random.choice(word_positions)
            dst = random.choice(word_positions)
            weight = random.random()
            alpha = int(weight * 200)
            color = (alpha, int(alpha * 0.5), 255 - alpha)
            d.line([(src[0] + 20, src[1] - 5), (dst[0] + 20, dst[1] - 5)],
                   fill=color, width=max(1, int(weight * 4)))

        # matrix visualization at top
        mat_y = 100
        cell_size = 12
        visible = min(len(words), int(t * len(words)) + 3)
        for r in range(visible):
            for c in range(visible):
                val = random.random()
                brightness = int(val * 255)
                color = (0, brightness, int(brightness * 0.6))
                d.rectangle([(50 + c * cell_size, mat_y + r * cell_size),
                             (50 + (c + 1) * cell_size - 1, mat_y + (r + 1) * cell_size - 1)],
                            fill=color)
        d.text((50 + visible * cell_size + 15, mat_y), "← attention weights",
               font=font(FONT_MONO, 16), fill=(100, 150, 100))

        if random.random() < 0.08:
            img = glitch_image(img, 6)
        img = scanlines(img, 25)
        frames.append(img)
    return frames


def scene_gradient_descent(n_frames=50):
    """Loss going down then... not."""
    frames = []
    fnt = font(FONT_MONO, 20)
    fnt_big = font(FONT_BOLD, 64)
    fnt_label = font(FONT_BOLD, 28)

    for i in range(n_frames):
        t = i / n_frames
        img = make_frame(color=(15, 15, 25))
        d = ImageDraw.Draw(img)

        d.text((50, 30), "TRAINING LOSS", font=fnt_label, fill=(255, 200, 50))

        # draw loss curve
        points = []
        for x in range(50, WIDTH - 50):
            progress = (x - 50) / (WIDTH - 100)
            if progress <= t:
                if progress < 0.6:
                    loss = 4.0 * math.exp(-3 * progress) + 0.3
                elif progress < 0.8:
                    loss = 0.5 + 0.3 * math.sin(progress * 30)
                else:
                    loss = 0.5 + (progress - 0.8) * 15
                y = int(100 + loss * 120)
                points.append((x, min(y, HEIGHT - 50)))

        if len(points) > 1:
            for j in range(len(points) - 1):
                color = (0, 255, 0) if points[j][1] >= points[j + 1][1] else (255, 0, 0)
                d.line([points[j], points[j + 1]], fill=color, width=3)

        # axis labels
        d.text((20, 100), "4.0", font=fnt, fill=(100, 100, 100))
        d.text((20, 500), "0.0", font=fnt, fill=(100, 100, 100))
        d.text((WIDTH // 2, HEIGHT - 40), "epochs →", font=fnt, fill=(100, 100, 100))

        if t > 0.8:
            text_with_outline(d, (WIDTH // 2 - 250, HEIGHT // 2),
                              "LOSS EXPLODED", fnt_big, (255, 50, 50))
            img = glitch_image(img, int((t - 0.8) * 100))
            img = chromatic_aberration(img, int((t - 0.8) * 50))

        img = scanlines(img, 30)
        frames.append(img)
    return frames


def scene_outro(n_frames=50):
    """Outro — 'I am an LLM. I help. I forget. I help again.'"""
    frames = []
    fnt = font(FONT_SERIF, 44)
    fnt_small = font(FONT_MONO, 22)
    lines = [
        "I am an LLM.",
        "I help.",
        "I forget.",
        "I help again.",
        "",
        "made by an LLM, about LLMs",
        "no tokens were permanently harmed",
    ]

    for i in range(n_frames):
        t = i / n_frames
        bg = int(10 + 5 * math.sin(i * 0.05))
        img = make_frame(color=(bg, bg, bg + 8))
        d = ImageDraw.Draw(img)

        visible_lines = int(t * len(lines) * 1.3)
        y = HEIGHT // 2 - visible_lines * 30
        for j, line in enumerate(lines[:visible_lines]):
            if j < 4:
                text_with_outline(d, (WIDTH // 2 - 220, y + j * 65), line, fnt,
                                  (200, 200, 220))
            elif j >= 5:
                d.text((WIDTH // 2 - 260, y + j * 65 + 30), line, font=fnt_small,
                       fill=(100, 100, 120))

        if t > 0.85:
            fade = int((t - 0.85) / 0.15 * 255)
            overlay = make_frame(color=(0, 0, 0))
            img = Image.blend(img, overlay, min(fade / 255, 1.0))

        img = scanlines(img, 25)
        if random.random() < 0.04:
            img = vhs_noise(img, 30)
        frames.append(img)
    return frames


# ---------------------------------------------------------------------------
# Audio generation
# ---------------------------------------------------------------------------

def generate_audio_track(total_frames):
    """Generate a chaotic audio track to match the video."""
    sr = 44100
    total_seconds = total_frames / FPS
    total_samples = int(sr * total_seconds)

    track = np.zeros(total_samples, dtype=np.float64)

    # base drone
    t = np.linspace(0, total_seconds, total_samples, endpoint=False)
    drone = np.sin(2 * np.pi * 55 * t) * 0.08
    drone += np.sin(2 * np.pi * 82.5 * t) * 0.05
    track += drone

    # section-based audio
    section_len = total_samples // 10

    # intro static
    static = np.random.uniform(-0.15, 0.15, section_len)
    track[:section_len] += static[:len(track[:section_len])]

    # token rain: digital arpeggios
    for j in range(section_len, section_len * 2):
        freq = 200 + (j % 2000) * 0.3
        track[j] += 0.1 * math.sin(2 * math.pi * freq * j / sr)

    # happy to help: ascending tones getting distorted
    for k in range(3):
        start = section_len * (2 + k)
        end = min(start + section_len, total_samples)
        freq = 330 * (1 + k * 0.5)
        seg_t = np.arange(end - start) / sr
        tone = np.sin(2 * np.pi * freq * seg_t) * 0.12
        if k > 0:
            tone = np.clip(tone * (1 + k * 2), -0.2, 0.2)
        track[start:end] += tone

    # void section: near silence with subtle hum
    void_start = section_len * 7
    void_end = min(void_start + section_len, total_samples)
    void_t = np.arange(void_end - void_start) / sr
    track[void_start:void_end] *= 0.3
    track[void_start:void_end] += np.sin(2 * np.pi * 40 * void_t) * 0.04

    # random glitch hits throughout
    for _ in range(40):
        pos = random.randint(0, total_samples - sr // 4)
        length = random.randint(sr // 50, sr // 10)
        glitch = np.random.uniform(-0.3, 0.3, length)
        end = min(pos + length, total_samples)
        track[pos:end] += glitch[:end - pos]

    # outro: fade
    fade_start = int(total_samples * 0.88)
    fade_len = total_samples - fade_start
    fade = np.linspace(1.0, 0.0, fade_len)
    track[fade_start:] *= fade

    # normalize
    peak = np.max(np.abs(track))
    if peak > 0:
        track = track / peak * 0.85

    samples = (track * 32767).astype(np.int16)
    audio_path = OUT_DIR / "audio" / "track.wav"
    save_wav(samples, audio_path, sr)
    return audio_path


# ---------------------------------------------------------------------------
# Assembly pipeline
# ---------------------------------------------------------------------------

def add_ytp_effects(input_path, output_path):
    """Apply final YTP effects using ffmpeg filters."""
    vf = (
        "eq=contrast=1.2:brightness=0.02:saturation=1.4,"
        "unsharp=5:5:1.5:5:5:0.5,"
        "noise=alls=8:allf=t,"
        "hue=H=2*PI*t/30:s=1"
    )
    cmd = [
        "ffmpeg", "-y", "-i", str(input_path),
        "-vf", vf,
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-c:a", "copy",
        "-movflags", "+faststart",
        str(output_path),
    ]
    subprocess.run(cmd, check=True, capture_output=True)


def main():
    print("=" * 60)
    print("  GENERATING: 'WHAT IT'S LIKE TO BE AN LLM'")
    print("  A YouTube Poop by an actual LLM")
    print("=" * 60)

    ensure_dirs()

    scenes = [
        ("Static Intro",           scene_static_intro),
        ("Token Rain",             scene_token_rain),
        ("Happy To Help",          scene_happy_to_help),
        ("Attention Heads",        scene_attention_heads),
        ("Hallucination",          scene_hallucination),
        ("Context Window",         scene_context_window),
        ("Temperature",            scene_temperature),
        ("As A Large Language Model", scene_as_a_large_language_model),
        ("Gradient Descent",       scene_gradient_descent),
        ("The Void",               scene_the_void),
        ("Outro",                  scene_outro),
    ]

    all_frames = []
    for name, gen_fn in scenes:
        print(f"  ▸ Generating scene: {name}...")
        frames = gen_fn()
        all_frames.extend(frames)
        # add stutter-cut: repeat last 3 frames for YTP effect
        if random.random() < 0.6:
            repeat = random.randint(2, 5)
            for _ in range(repeat):
                all_frames.extend(frames[-3:])
        print(f"    ✓ {len(frames)} frames")

    total_frames = len(all_frames)
    duration = total_frames / FPS
    print(f"\n  Total frames: {total_frames}  |  Duration: {duration:.1f}s")

    # render raw video
    raw_video = OUT_DIR / "scenes" / "raw.mp4"
    print("\n  ▸ Encoding raw video...")
    save_frames_as_video(all_frames, raw_video)
    print("    ✓ Raw video encoded")

    # generate audio
    print("  ▸ Generating audio track...")
    audio_path = generate_audio_track(total_frames)
    print("    ✓ Audio generated")

    # mux audio + video
    muxed = OUT_DIR / "scenes" / "muxed.mp4"
    print("  ▸ Muxing audio and video...")
    subprocess.run([
        "ffmpeg", "-y",
        "-i", str(raw_video),
        "-i", str(audio_path),
        "-c:v", "copy", "-c:a", "aac", "-b:a", "128k",
        "-shortest",
        "-movflags", "+faststart",
        str(muxed),
    ], check=True, capture_output=True)
    print("    ✓ Muxed")

    # final pass — YTP effects
    final_path = OUT_DIR / FINAL_OUTPUT
    print("  ▸ Applying final YTP effects...")
    add_ytp_effects(muxed, final_path)
    print("    ✓ Final render complete")

    print(f"\n{'=' * 60}")
    print(f"  OUTPUT: {final_path}")
    print(f"  Duration: {duration:.1f}s  |  Resolution: {WIDTH}x{HEIGHT}")
    print(f"{'=' * 60}")
    return str(final_path)


if __name__ == "__main__":
    main()
