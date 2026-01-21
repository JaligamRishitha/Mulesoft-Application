# 🔧 Frontend Troubleshooting Guide

## 🎯 Issue: Cannot Access Frontend Dashboard

The UI dashboard container is running successfully, but you cannot access it in your browser.

## ✅ Container Status:
- **Container:** deployments-ui-dashboard-1 ✅ RUNNING
- **Port Binding:** 0.0.0.0:3000->3000/tcp ✅ BOUND
- **Compilation:** webpack compiled successfully ✅ COMPILED
- **Server:** Development server started ✅ STARTED

## 🔍 Possible Causes & Solutions:

### **1. Browser Access Issues**

**Try these URLs in your browser:**
```
http://localhost:3000
http://127.0.0.1:3000
http://0.0.0.0:3000
```

**Clear browser cache:**
- Press `Ctrl + F5` to hard refresh
- Clear browser cache and cookies
- Try incognito/private mode

### **2. Windows Firewall/Security**

**Check Windows Firewall:**
1. Open Windows Defender Firewall
2. Allow Docker Desktop through firewall
3. Allow port 3000 through firewall

**Run as Administrator:**
```bash
# Run PowerShell as Administrator and try:
curl http://localhost:3000
```

### **3. Docker Desktop Issues**

**Restart Docker Desktop:**
1. Right-click Docker Desktop in system tray
2. Select "Restart Docker Desktop"
3. Wait for Docker to fully restart
4. Try accessing again

**Check Docker Desktop Settings:**
1. Open Docker Desktop
2. Go to Settings > Resources > Network
3. Ensure "Use kernel networking for DNS resolution" is enabled

### **4. Alternative: Run Frontend Locally**

If Docker continues to have issues, run the frontend directly:

```bash
# Navigate to UI dashboard directory
cd Inte-platform/ui-dashboard

# Install dependencies (if not already installed)
npm install

# Start development server
npm start
```

This will start the frontend on http://localhost:3000 without Docker.

### **5. Port Conflict Check**

**Check what's using port 3000:**
```bash
netstat -ano | findstr :3000
```

**If another process is using port 3000, change the port:**
```bash
# In ui-dashboard directory
set PORT=3001 && npm start
```

### **6. Network Connectivity Test**

**Test from command line:**
```bash
# Test if the port is accessible
telnet localhost 3000

# Test HTTP response
curl -v http://localhost:3000
```

## 🚀 Quick Fix Commands:

### **Option 1: Restart Everything**
```bash
cd Inte-platform/deployments
docker-compose down
docker-compose up -d postgres platform-backend ui-dashboard
```

### **Option 2: Run Frontend Locally**
```bash
cd Inte-platform/ui-dashboard
npm install
npm start
```

### **Option 3: Use Different Port**
```bash
cd Inte-platform/ui-dashboard
set PORT=3001 && npm start
```

## 🎯 Expected Result:

When working, you should see:
- **Dashboard URL:** http://localhost:3000
- **Real Salesforce Data:** Live cases from your external app
- **Connection Status:** Shows "Connected" when external app is available
- **No Mock Data:** Only real data from port 5173

## 🔍 Debug Information:

**Container Logs:**
```bash
docker logs deployments-ui-dashboard-1 --tail 50
```

**Container Status:**
```bash
docker ps | findstr ui-dashboard
```

**Port Check:**
```bash
netstat -ano | findstr :3000
```

## 📞 If Still Not Working:

1. **Try the local npm start approach** (most reliable)
2. **Check Windows Defender/Antivirus** settings
3. **Restart your computer** (sometimes helps with Docker networking)
4. **Use a different browser** to rule out browser-specific issues

The frontend is compiled and running - it's likely a network/access issue that can be resolved with the above steps! 🎯