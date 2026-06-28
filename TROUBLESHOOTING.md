# Troubleshooting Guide

Welcome to the MSM Troubleshooting Guide! If you run into issues while setting up or managing your Minecraft server, you'll likely find the solution here.

## 1. Java Version Mismatches

**Symptom:**
The server fails to start, and when you attach to the console (Option 6), you see an error like:
`UnsupportedClassVersionError: ... has been compiled by a more recent version of the Java Runtime`

**Cause:**
Newer versions of Minecraft require newer versions of Java. For example, Minecraft 1.20.5+ requires Java 21, while 1.17 - 1.20.4 require Java 17.

**Fix:**
1. Install the required Java version for your system.
   - **Termux:** `pkg install openjdk-17` or `pkg install openjdk-21`
   - **Debian/Ubuntu:** `sudo apt install openjdk-17-jre-headless` or `sudo apt install openjdk-21-jre-headless`
2. Restart MSM. It will automatically detect the installed Java versions.

## 2. Port Conflicts

**Symptom:**
The server fails to start, and the console shows:
`FAILED TO BIND TO PORT! The exception was: java.net.BindException: Address already in use`

**Cause:**
Another server or application is already using the specified port (default 25565).

**Fix:**
1. Stop the other server if it is running.
2. Or, change the port for the current server:
   - Go to `4. Configure server` in the MSM main menu.
   - Select `2. Port` and enter a new port number (e.g., 25566).
   - Start the server again.

## 3. Playit Linking Failures

**Symptom:**
You run the tunnel setup wizard for Playit, but it gets stuck, or the tunnel status says "Playit needs account linking" or "Missing Playit secret."

**Cause:**
The playit agent wasn't able to complete the claim exchange with the playit API, usually because the claim URL wasn't visited, or the browser session timed out.

**Fix:**
1. Stop the server from the MSM main menu.
2. Go to `4. Configure server` -> `15. Tunnel setup wizard`.
3. Choose `2. Setup playit`.
4. When asked "Run the guided playit claim flow now?", choose `Y`.
5. **Crucial Step:** When the URL appears (`https://playit.gg/claim/...`), copy and open it in your browser immediately.
6. Once the webpage says your device is linked, return to the MSM terminal and press Enter.

## 4. Server Killed by Android (Termux)

**Symptom:**
The server crashes unexpectedly without any Java errors in the console. The MSM auto-restart catches it, but it happens frequently.

**Cause:**
Android's Phantom Process Killer is terminating the Java process because it is using too much CPU/RAM in the background.

**Fix:**
1. Allocate less RAM to your server in the MSM configuration menu (try keeping it under 50% of your device's total RAM).
2. Disable the Android Phantom Process Killer using ADB:
   ```bash
   adb shell "settings put global settings_enable_monitor_phantom_procs false"
   ```

## 5. "screen is not installed"

**Symptom:**
When starting MSM or trying to attach to the console, you see `screen is not installed`.

**Cause:**
The `screen` utility is a hard dependency for MSM's process isolation, and it is missing from your system.

**Fix:**
Install `screen`:
- **Termux:** `pkg install screen`
- **Debian/Ubuntu:** `sudo apt install screen`
