# Troubleshooting Guide

This guide helps you resolve common issues with MSM (Minecraft Server Manager).

## Common Issues and Solutions

### 1. Network/Download Errors

**Error: "Download timeout: Connection to server timed out"**
- **Cause**: Poor internet connection or server is temporarily unavailable
- **Solution**: 
  - Check your internet connection
  - Try again later
  - Use a different network if possible

**Error: "DNS resolution failed: Could not resolve server address"**
- **Cause**: DNS issues or no internet connection
- **Solution**:
  - Check your internet connection
  - Try switching to a different DNS server (e.g., Google DNS: 8.8.8.8)
  - Restart your network connection

**Error: "Download failed: File not found (404)"**
- **Cause**: The requested server version is no longer available
- **Solution**:
  - Try a different version of the server software
  - Check if the server type is still supported
  - Select a more recent version

**Error: "Download failed: Access denied (403)"**
- **Cause**: Authentication required or access restricted
- **Solution**:
  - Check your credentials for the service
  - Ensure you have proper permissions
  - Try a different server type or version

### 2. Permission Errors

**Error: "Permission denied while writing to [path]"**
- **Cause**: Insufficient permissions to write to the directory
- **Solution**:
  - Run MSM with elevated privileges (sudo on Linux/macOS)
  - Check directory permissions
  - Ensure the target directory is writable

**Error: "Directory not found: [path]"**
- **Cause**: The specified directory doesn't exist
- **Solution**:
  - Create the missing directory
  - Check if the path is correct
  - Ensure MSM has permission to access the parent directory

### 3. Server Startup Issues

**Error: "No .jar file found in [path]"**
- **Cause**: Server software not installed or JAR file missing
- **Solution**:
  - Install the server software using option 3 in the menu
  - Verify the JAR file exists in the server directory
  - Reinstall the server software if corrupted

**Error: "Server '[name]' is already running"**
- **Cause**: The server is already running in another session
- **Solution**:
  - Stop the existing server first
  - Use `screen -ls` to check for running sessions
  - Kill the existing screen session if needed: `screen -S msm-[name] -X quit`

**Error: "Port in use"**
- **Cause**: Another process is using the server port
- **Solution**:
  - Change the server port in server.properties
  - Kill the process using the port: `kill $(lsof -t -i:[port])`
  - Restart the server

### 4. Debian/Environment Issues

**Error: "Bad system call"**
- **Cause**: Running outside of Debian environment
- **Solution**:
  - Run MSM within the Debian environment: `proot-distro login debian`
  - Ensure Debian is properly installed
  - Reinstall Debian if needed: `proot-distro reset debian`

**Error: "Command not found: screen"**
- **Cause**: Screen utility not installed
- **Solution**:
  - Install screen in Debian: `apt update && apt install -y screen`
  - Verify installation: `screen --version`

**Error: "Java not found"**
- **Cause**: Java Runtime Environment not installed
- **Solution**:
  - Install OpenJDK in Debian: `apt update && apt install -y openjdk-17-jre`
  - Verify installation: `java --version`

### 5. Backup/Restore Issues

**Error: "Backup verification failed"**
- **Cause**: Corrupted backup file or insufficient disk space
- **Solution**:
  - Check available disk space
  - Delete the corrupted backup file
  - Create a new backup
  - Verify the backup directory has write permissions

**Error: "No world directories found"**
- **Cause**: Server has never been started or world files are missing
- **Solution**:
  - Start the server at least once to generate world files
  - Verify world directories exist in the server folder
  - Check server logs for errors

### 6. Tunneling Issues

**Error: "Ngrok not found"**
- **Cause**: Ngrok is not installed
- **Solution**:
  - Install ngrok: `apt update && apt install -y ngrok`
  - Or download from https://ngrok.com/download

**Error: "Cloudflared not found"**
- **Cause**: Cloudflared is not installed
- **Solution**:
  - Install cloudflared: 
    ```bash
    curl -fsSL https://pkg.cloudflare.com/cloudflare-main.gpg | gpg --dearmor > /etc/apt/trusted.gpg.d/cloudflare.gpg
    echo "deb [signed-by=/etc/apt/trusted.gpg.d/cloudflare.gpg] https://pkg.cloudflare.com/ focal main" > /etc/apt/sources.list.d/cloudflare.list
    apt update && apt install -y cloudflared
    ```

**Error: "Playit token not configured"**
- **Cause**: Playit.gg token is missing
- **Solution**:
  - Follow the setup instructions in the tunnel manager
  - Visit https://playit.gg to get your token
  - Enter the token when prompted

## Advanced Troubleshooting

### Checking Logs
MSM logs all operations to help with debugging:
- **Log location**: `~/.msm/msm.log` (or `/root/msm/msm.log` in Debian)
- **View logs**: `tail -f ~/.msm/msm.log`

### Debug Mode
Enable verbose output for more detailed information:
```bash
python main.py --verbose
# or
python cli.py --verbose [command]
```

### Manual Cleanup
If MSM becomes unresponsive:
1. Kill all screen sessions: `pkill screen`
2. Delete temporary files: `rm -rf ~/.msm/*`
3. Restart MSM

## Getting Help

If you're still having issues:
1. Check the logs for detailed error messages
2. Search this troubleshooting guide for your error
3. Report the issue on GitHub with:
   - Error message
   - Steps to reproduce
   - MSM version
   - Environment details (Debian/Host OS)

## Environment Requirements

MSM is designed to work in the following environment:
- **Primary**: Termux with Debian (proot-distro)
- **Secondary**: Native Linux environments
- **Unsupported**: Windows (without WSL) or macOS

The Debian requirement exists because:
1. Many Minecraft server dependencies work best on Debian
2. Consistent environment for troubleshooting
3. Better compatibility with server software
4. Easier package management for tunneling tools

While MSM may work in other environments, support is limited to the primary environment.