# 🎮 Epic Games Claimer - Free Games Automation

Automate claiming free games from the Epic Games Store with this complete and robust Python script.

## 📋 Table of Contents

- [Description](#-description)
- [Features](#-features)
- [Prerequisites](#-prerequisites)
- [Installation](#-installation)
- [Configuration](#-configuration)
- [Usage](#-usage)
- [Scheduling](#-scheduling)
- [Log Structure](#-log-structure)
- [Troubleshooting](#-troubleshooting)
- [Security](#-security)

## 🎯 Description

This project fully automates the process of claiming free games from the Epic Games Store. The script:

- Automatically logs into your Epic Games account
- Detects available free games
- Adds games to your library automatically
- Queries unofficial APIs for upcoming game information
- Produces detailed logs organized by date
- Saves information in JSON for future reference

## ✨ Features

- ✅ **Full automation** using Playwright (more modern and reliable than Selenium)
- ✅ **2FA support** — script will pause to allow manual verification
- ✅ **CAPTCHA detection** — waits for manual resolution and continues automatically
- ✅ **Organized logs** — saved in a YYYY/MM/DD.txt directory structure
- ✅ **API queries** — get current and upcoming free game info
- ✅ **Robust error handling** — resilient to common failures
- ✅ **Single-run friendly** — great for scheduling via cron or Task Scheduler
- ✅ **Configurable via .env** — no need to edit code

## 🔧 Prerequisites

- **Python 3.8+** installed
- **Epic Games Store account** (free)
- **Internet connection**
- **Operating system**: Windows, Linux, or macOS

## 📥 Installation

### Step 1: Clone or Download the Project

```bash
# Clone the repository (or download and extract the ZIP)
cd /path/to/project/epic_games_claimer
```

### Step 2: Create a Virtual Environment (Recommended)

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/macOS
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Install Playwright Browsers

```bash
playwright install chromium
```

> Note: This command downloads the Chromium browser used for automation (~150MB)

## ⚙️ Configuration

### Step 1: Set Up Credentials

1. Copy the example file:

```bash
# Windows
copy .env.example .env

# Linux/macOS
cp .env.example .env
```

2. Edit the `.env` file with your credentials:

```env
EPIC_EMAIL=your_email@example.com
EPIC_PASSWORD=your_password_here
```

### Step 2: Optional Settings

```env
# Headless mode (true = no visible browser window)
HEADLESS=true

# Timeout in milliseconds
TIMEOUT=30000

# Log base directory
LOG_BASE_DIR=C:/IA/Epic Games

# Data directory
DATA_DIR=./data
```

### 📝 Configuration Notes

#### 🔐 Two-Factor Authentication (2FA)

If your account uses 2FA:

1. Set `HEADLESS=false` for the first run
2. The script will open a visible browser window
3. Complete the 2FA prompt manually when asked
4. The script will continue automatically after verification

#### 🤖 CAPTCHA

If a CAPTCHA appears:

1. The script will detect it automatically
2. Solve the CAPTCHA manually in the browser window
3. The script will continue after the CAPTCHA is solved

#### 🐧 Linux Users

Adjust the log path for Linux:

```env
LOG_BASE_DIR=/home/your_user/IA/Epic Games
```

## 🚀 Usage

### Manual Run

```bash
# Activate the virtual environment (if created)
# Windows: venv\Scripts\activate
# Linux/macOS: source venv/bin/activate

# Run the script
python epic_games_claimer.py
```

### Expected Output

```
================================================================================
Epic Games Claimer - New Run
================================================================================
✓ Configuration loaded (Headless: True, Timeout: 30000ms)
🔍 Querying API for free game information...
✓ Information saved to: ./data/next_games.json
📌 Current free games found: 2
   - Example Game 1
   - Example Game 2
🌐 Launching browser...
✓ Browser started successfully
🔐 Beginning login process...
✓ Login successful!
🎮 Searching for free games available...
✓ Total free games found: 2
🎁 Attempting to claim: Example Game 1
   ✅ Game successfully added: Example Game 1
================================================================================
📊 RUN SUMMARY
================================================================================
✅ Games processed successfully: 2
   - Example Game 1
   - Example Game 2
================================================================================
✓ Run completed!
```

## ⏰ Scheduling

### Windows - Task Scheduler

#### Option 1: GUI

1. Open **Task Scheduler**
2. Click **"Create Basic Task"**
3. Configure:
   - **Name**: Epic Games Claimer
   - **Trigger**: Daily at 12:00 (time Epic usually updates free games)
   - **Action**: Start a program
   - **Program**: `C:\path\to\venv\Scripts\python.exe`
   - **Arguments**: `C:\path\to\epic_games_claimer.py`
   - **Start in**: `C:\path\to\project`

#### Option 2: Command Line

```powershell
# Create a .bat file
echo @echo off > run_claimer.bat
echo cd /d C:\path\to\epic_games_claimer >> run_claimer.bat
echo venv\Scripts\python.exe epic_games_claimer.py >> run_claimer.bat

# Schedule with schtasks
schtasks /create /tn "Epic Games Claimer" /tr "C:\path\to\run_claimer.bat" /sc daily /st 12:00
```

### Linux/macOS - Cron

1. Open crontab:

```bash
crontab -e
```

2. Add the line (runs daily at 12:00):

```bash
0 12 * * * cd /path/to/epic_games_claimer && /path/to/venv/bin/python epic_games_claimer.py
```

3. Save and close the editor

#### Cron schedule examples

```bash
# Daily at 12:00
0 12 * * * command

# Daily at 18:00
0 18 * * * command

# Every Thursday at 17:00 (the day Epic often releases new free games)
0 17 * * 4 command

# Twice daily (12:00 and 18:00)
0 12,18 * * * command
```

## 📂 Log Structure

### File Organization

```
C:/IA/Epic Games/
├── 2025/
│   ├── 10/
│   │   ├── 24.txt
│   │   ├── 25.txt
│   │   └── 26.txt
│   └── 11/
│       └── 01.txt
└── 2026/
    └── 01/
        └── 01.txt
```

### Log Contents

Each log file includes:

- ✅ **Timestamps** for each action
- 🔍 **Detected game information**
- ✅ **Successes** (games added)
- ⚠️ **Warnings** (already owned games, CAPTCHA, etc.)
- ❌ **Errors** (connection failures, timeouts, etc.)

### Data Files

```
./data/
└── next_games.json  # Current and upcoming game information
```

Example `next_games.json`:

```json
{
  "currentGames": [
    {
      "title": "Current Free Game",
      "date": "2025-10-24",
      "publisher": "Publisher"
    }
  ],
  "nextGames": [
    {
      "title": "Next Free Game",
      "date": "2025-10-31",
      "publisher": "Publisher"
    }
  ]
}
```

## 🔧 Troubleshooting

### ❌ Problem: "EPIC_EMAIL and EPIC_PASSWORD must be set"

**Fix**:

- Ensure a `.env` file exists in the project directory
- Confirm the variables are set correctly
- Do not include spaces before or after the `=` sign

### ❌ Problem: "Timeout during login"

**Fixes**:

- Increase `TIMEOUT` in `.env` (e.g. `TIMEOUT=60000`)
- Verify your internet connection
- Run with `HEADLESS=false` to observe issues visually
- Clear browser cache and cookies

### ❌ Problem: CAPTCHA appears frequently

**Fixes**:

- Run with `HEADLESS=false` and solve the CAPTCHA manually
- Wait a few minutes between runs
- Avoid running repeatedly in rapid succession
- Epic may apply rate limits

### ❌ Problem: Two-factor authentication not working

**Fix**:

- Set `HEADLESS=false`
- Complete the 2FA manually in the browser window
- The script will wait up to 2 minutes for completion

### ❌ Problem: "No free games found"

**Possible causes**:

- There are no free games available at the moment
- Epic changed the website structure (script needs an update)
- Connection or timeout issues

**Fix**:

- Check the Epic Games Store website manually
- Run with `HEADLESS=false` to inspect the page
- Check `next_games.json` for upcoming game info

### ❌ Problem: Script won't run via cron/Task Scheduler

**Linux/macOS**:
```bash
# Use absolute paths
0 12 * * * cd /full/path/epic_games_claimer && /full/path/venv/bin/python /full/path/epic_games_claimer.py >> /tmp/epic_claimer.log 2>&1
```

**Windows**:

- Ensure the scheduled user has the necessary permissions
- Use absolute paths (not relative)
- Test the .bat file manually before scheduling

### ⚠️ Problem: Account temporarily blocked

**Fix**:

- Wait a few hours before trying again
- Do not run the script repeatedly in a short time window
- Schedule at reasonable intervals (once per day)

## 🔒 Security

### ⚠️ Important Warnings

1. **NEVER share your `.env`** with credentials
2. **Use strong, unique passwords** for your Epic Games account
3. **Enable 2FA** on your account for added security
4. **Do not run on public or shared machines**

### 📁 .gitignore Example

If using git, add these to `.gitignore`:

```gitignore
.env
data/
*.log
__pycache__/
venv/
```

### 🔐 Best Practices

- ✅ Use a Python virtual environment
- ✅ Keep dependencies updated
- ✅ Review logs periodically
- ✅ Back up your `.env` securely
- ❌ Do not share credentials
- ❌ Do not run code from untrusted sources

## 📊 Project Structure

```
epic_games_claimer/
├── epic_games_claimer.py    # Main script
├── .env                      # Configuration (DO NOT commit)
├── .env.example              # Configuration template
├── requirements.txt          # Python dependencies
├── README.md                 # This file
└── data/                     # Saved data (created automatically)
    └── next_games.json       # Game information
```

## 🤝 Contributing

Found a bug or have a suggestion? Feel free to:

1. Open an issue
2. Submit a pull request
3. Share improvements

## 📜 License

This project is provided "as-is" for personal use. Use at your own risk.

## ⚠️ Disclaimer

- This project is not affiliated, endorsed, or sponsored by Epic Games
- Use at your own risk
- Respect Epic Games' Terms of Service
- Automation may violate terms in some circumstances

## 📞 Support

For issues or questions:

1. See the [Troubleshooting](#-troubleshooting) section
2. Check logs at `C:/IA/Epic Games/YYYY/MM/DD.txt`
3. Run with `HEADLESS=false` for visual debugging

---

**Built with ❤️ for the gaming community**

*Enjoy your free games! 🎮*
