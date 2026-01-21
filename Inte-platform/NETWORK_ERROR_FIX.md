# 🔧 Network Error Fix

## ❌ Error:
```
Uncaught runtime errors:
×ERROR Network Error 
AxiosError: Network Error
```

## 🎯 Root Cause:
Frontend (localhost:3000) cannot connect to Backend API (localhost:8080)

## ✅ Quick Fixes:

### **1. Check Backend Status**
```bash
# Check if backend container is running
docker ps | findstr platform-backend

# Check backend logs
docker logs deployments-platform-backend-1 --tail 20
```

### **2. Test Backend Directly**
Open a new browser tab and try:
```
http://localhost:8080/health
http://localhost:8080/api/test
```

If these don't work, the backend isn't accessible.

### **3. Restart Backend**
```bash
cd Inte-platform/deployments
docker-compose restart platform-backend
```

### **4. Check Windows Firewall**
- Windows Defender might be blocking port 8080
- Add exception for Docker Desktop
- Try running browser as Administrator

### **5. Alternative: Run Backend Locally**
If Docker networking issues persist:
```bash
cd Inte-platform/platform-backend
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
```

### **6. Update API Configuration**
If backend is on different port, update `ui-dashboard/src/api.js`:
```javascript
const api = axios.create({
  baseURL: 'http://localhost:8080/api', // Update this URL
  headers: { 'Content-Type': 'application/json' },
});
```

## 🔍 Debug Steps:

### **Step 1: Test Backend**
```bash
# Test health endpoint
curl http://localhost:8080/health

# Should return: {"status":"healthy","service":"platform-backend"}
```

### **Step 2: Check Network**
```bash
# Check if port 8080 is bound
netstat -ano | findstr :8080
```

### **Step 3: Test CORS**
Open browser console (F12) and check for CORS errors.

### **Step 4: Use API Test Component**
The dashboard now includes an API test component that will show:
- ✅ Connection successful
- ❌ Connection failed with details

## 🎯 Expected Result:

When fixed, you should see:
- ✅ API Test shows "Backend connection successful!"
- ✅ Dashboard loads real Salesforce data
- ✅ No network errors in browser console

## 🚀 Most Common Solution:

**Restart both frontend and backend:**
```bash
# Terminal 1: Restart backend
cd Inte-platform/deployments
docker-compose restart platform-backend

# Terminal 2: Restart frontend
cd Inte-platform/ui-dashboard
npm start
```

The API test component will help identify exactly what's failing! 🔧