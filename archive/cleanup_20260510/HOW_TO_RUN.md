# How to Run This on Claude Code — Dummy-Proof Edition

You're going to do exactly 12 things. Don't skip any. Don't improvise. The whole thing takes about 30 minutes the first time, mostly waiting for downloads.

---

## What You Need Before You Start

- A Windows PC (the scripts assume this — paths use `C:\`)
- Python 3.10 or newer installed. To check, open Command Prompt and type:
  ```
  python --version
  ```
  If it says `'python' is not recognized`, install it from https://www.python.org/downloads/ and **tick the "Add to PATH" box** during install. Open a new Command Prompt after installing.
- An internet connection (for the first run only)

---

## Step 1 — Install Claude Code

Claude Code is a separate program from the chat you're using right now. It's a command-line tool that can run code, edit files, and use your computer.

1. Open Command Prompt (press Windows key, type `cmd`, hit Enter)
2. Paste this and press Enter:
   ```
   npm install -g @anthropic-ai/claude-code
   ```
3. If that fails with "npm is not recognized", install Node.js first from https://nodejs.org/ (LTS version), restart Command Prompt, and try again.

Verify it worked:
```
claude --version
```
You should see a version number. If you do, move on.

---

## Step 2 — Make the Project Folder

In Command Prompt, paste these one at a time:
```
mkdir C:\money-machine
cd C:\money-machine
mkdir scripts output tools assets
mkdir output\videos output\audio output\metadata output\logs
mkdir tools\piper
```

If any folder already exists, Windows will say so. That's fine — keep going.

---

## Step 3 — Drop the Two Python Files Into That Folder

You have two files from this conversation:
- `run_pipeline.py` — the production pipeline
- `generate_scripts.py` — the script writer

**Move both files into `C:\money-machine\`** (not into a subfolder — directly in the `money-machine` folder).

Verify with:
```
dir C:\money-machine
```
You should see both `.py` files listed.

---

## Step 4 — Install ffmpeg (Required, Don't Skip)

ffmpeg is what actually encodes your videos. Without it, the pipeline crashes.

In an **administrator** Command Prompt (right-click Command Prompt, "Run as administrator"), paste:
```
winget install Gyan.FFmpeg
```

Close that admin Command Prompt and open a fresh **regular** Command Prompt. Verify:
```
ffmpeg -version
```
You should see version info. If you get "not recognized", restart your computer and try again — the PATH update needs a reboot sometimes.

---

## Step 5 — Start Claude Code in the Project Folder

In Command Prompt:
```
cd C:\money-machine
claude
```

The first time, it'll ask you to log in via browser. Do that. Then you'll see the Claude Code prompt waiting for input.

**You're now talking to Claude Code, not the web chat.** Anything you type is a command for it.

---

## Step 6 — Generate Scripts (the Easy Way)

Type this exactly into Claude Code and press Enter:

```
Run python generate_scripts.py --template to create 20 placeholder scripts. After it finishes, list the contents of the scripts folder so I can confirm.
```

Claude Code will run the command, write the 20 files, and show you the listing. Each file should be roughly 1-2 KB. **These are placeholder scripts** — solid enough to test the pipeline, but generic.

### Optional but Strongly Recommended: Better Scripts via API

The template scripts work but are repetitive. For unique, well-written scripts, get an Anthropic API key:

1. Go to https://console.anthropic.com/
2. Sign up, add $5 of credit (generating 20 scripts costs about $0.50)
3. Create an API key, copy it
4. Close Claude Code (Ctrl+C twice)
5. In Command Prompt:
   ```
   setx ANTHROPIC_API_KEY "sk-ant-paste-your-key-here"
   ```
6. **Open a brand new Command Prompt** (the env var only shows in new windows)
7. Navigate back: `cd C:\money-machine`
8. Restart `claude`
9. Tell Claude Code:
   ```
   Run python generate_scripts.py --force to regenerate all 20 scripts using the API.
   ```

---

## Step 7 — Validate the Environment

Tell Claude Code:
```
Run python run_pipeline.py --check and tell me about any warnings or errors.
```

This validates:
- All folders exist
- All Python packages installed
- Scripts are present and parseable
- ffmpeg is available
- Piper TTS or gTTS is available

If it reports issues, tell Claude Code:
```
Fix the issues you found.
```

It will install missing packages and download Piper for you.

---

## Step 8 — Set Up Piper TTS (Best Voice Quality)

Tell Claude Code:
```
Run python run_pipeline.py --setup to install all packages and download Piper TTS. Show me the output.
```

This downloads about 70MB. If Piper download fails (HuggingFace sometimes throttles), don't panic — the pipeline falls back to gTTS automatically. The audio will still work, it'll just sound slightly more robotic and need internet during runs.

---

## Step 9 — Do a Single-Video Test Run

**Don't render all 20 yet.** Render one and watch it. Tell Claude Code:

```
Run python run_pipeline.py --only 1 and report how long it took and where the output landed.
```

This makes one MP4. Should take 3-8 minutes depending on your CPU. When it's done:

```
explorer C:\money-machine\output\videos
```

Open the MP4 in VLC. Listen to the audio. Look at the slides. **If anything is wrong, fix it now before rendering 19 more.**

Common issues and fixes:
- **No audio / silence**: Piper failed and gTTS isn't installed. Tell Claude Code: `Install gtts and try video 1 again with --redo 1`
- **Captions missing**: ImageMagick isn't installed. Captions are optional — videos still work without them. To add: `winget install ImageMagick.ImageMagick`
- **Crashes on rendering**: Tell Claude Code: `Show me the last 50 lines of C:\money-machine\output\logs\errors.log`

---

## Step 10 — Render All 20

Tell Claude Code:
```
Run python run_pipeline.py to render all remaining videos. Tell me the final summary when it finishes.
```

This will take **2-4 hours** total on a typical 16GB laptop. The pipeline is crash-safe — if anything dies (power, blue screen, you close the window), just run the same command again and it picks up from where it left off.

If you want to monitor progress, open a second Command Prompt and:
```
type C:\money-machine\output\logs\progress.json
```

---

## Step 11 — Spot Check the Output

When done, tell Claude Code:
```
Tell me how many MP4 files are in C:\money-machine\output\videos, their total size, and read me one of the metadata JSON files.
```

You should have 20 MP4 files, each 30-150 MB, totaling about 1-3 GB.

Open three of them in VLC at random — beginning, middle, end. Confirm:
- Audio plays cleanly
- No audio cuts out mid-sentence
- Slides are readable
- Title is correct

---

## Step 12 — Upload (Manually)

The pipeline does NOT upload to YouTube — that requires OAuth and a Google Cloud project. Upload manually:

1. Go to https://studio.youtube.com/
2. Click "Create" → "Upload videos"
3. Drag the MP4 in
4. Open the matching JSON in `output\metadata\` — copy the title, description, tags
5. **Set visibility to Private until you've reviewed it**
6. Add a thumbnail
7. Publish when ready

---

## What to Tell Claude Code If Things Go Wrong

These prompts work well in Claude Code:

- `Show me the last error in C:\money-machine\output\logs\errors.log`
- `Video 7 failed. Show me the script, the error, and try to fix it.`
- `Re-render only video 12 with --redo 12`
- `One of the videos has no audio. Diagnose and fix it.`
- `Update the slide background colors in run_pipeline.py to use a blue and gold palette instead.`

---

## What This Setup Will NOT Do

Be honest about the limits:

- **It won't make viral videos.** Slide-based videos with TTS narration are baseline content. They're fine for educational channels but won't crush in the algorithm without strong hooks, thumbnails, and topic selection.
- **It won't write financial advice.** The scripts are general education. Don't claim otherwise on YouTube — you can get demonetized or sued.
- **It won't auto-upload.** You need to upload each one yourself. This is intentional — it forces you to spot-check before going live.
- **It won't pick thumbnails.** Make those yourself in Canva or similar.
- **The TTS isn't human.** Piper sounds good for a free local engine but it's not ElevenLabs. If you want studio-quality voice, swap in ElevenLabs API by editing the `tts_piper` function — that's a 20-line change Claude Code can do for you.

---

## TL;DR Cheat Sheet

```
# Setup (once)
winget install Gyan.FFmpeg
npm install -g @anthropic-ai/claude-code
mkdir C:\money-machine && cd C:\money-machine
# (drop the two .py files in here)
claude

# Inside Claude Code:
Run python generate_scripts.py --template
Run python run_pipeline.py --setup
Run python run_pipeline.py --only 1     # test one
Run python run_pipeline.py               # do all 20
```

That's it. Good luck.
