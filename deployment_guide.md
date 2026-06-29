# HealthHive: AWS EC2 Deployment Guide

This guide details the step-by-step workflow to deploy code changes from your local Windows development machine to your live AWS EC2 Linux server.

---

## 🌐 The Conceptual Architecture

We use **GitHub** as the bridge to securely sync local edits to the cloud:

1. **Local PC:** You write and save code changes locally.
2. **GitHub:** You push changes from your local PC to a remote repository.
3. **AWS EC2:** You connect to the server and pull the updated files from GitHub.
4. **Systemd Services:** You restart Gunicorn and Nginx to load the changes into memory.

---

## 🛠️ Step-by-Step Deployment Walkthrough

### Step 1: Push Changes from Your Local PC to GitHub
Ensure you are inside the root folder of your project (`c:\Users\Anuj\Desktop\HealthHive`) and run these Git commands sequentially in your local terminal:

```bash
# 1. Stage all your modified and new files (like price_scraper.py, templates)
git add -A

# 2. Package your staged changes with a descriptive message
git commit -m "Fix scraper matching, add search fallback and theme toggle"

# 3. Upload your commits to your GitHub repository ('main' branch)
git push origin main
```

---

### Step 2: SSH into Your AWS EC2 Server
Connect to your remote virtual machine over SSH using your AWS private key.

Run this command in your local terminal:
```bash
ssh -i C:\Users\Anuj\Downloads\test-key.pem ec2-user@13.233.149.34
```
* **Authentication Logic:** The private key (`test-key.pem`) acts as a secure, password-free login token corresponding to the public key stored on your AWS instance.

---

### Step 3: Pull the Latest Code Updates on EC2
Once logged into the server (your prompt will show `[ec2-user@...]$`), execute the following commands to download your code:

```bash
# 1. Navigate to the project directory on the server
cd /home/ec2-user/HealthHive

# 2. Pull the updates directly from GitHub
git pull origin main
```
* **Pulling Logic:** This replaces the old files on the server with the new files you pushed in **Step 1**.

---

### Step 4: Configure the Server Secrets (`.env` File)
Since API keys and database passwords are excluded from Git commits for security (using `.gitignore`), you must configure them directly on the server's filesystem.

Run this command on your EC2 terminal:
```bash
# Open the .env file in the Nano editor
nano /home/ec2-user/HealthHive/.env
```
1. Find the `GEMINI_API_KEY` line and verify or update it:
   ```env
   GEMINI_API_KEY=your-gemini-api-key-here
   ```
2. Press `Ctrl + O` and `Enter` to save changes.
3. Press `Ctrl + X` to close the editor.

---

### Step 5: Reload and Restart Web Services
Python caches loaded modules in memory when executing long-running processes. You must tell Systemd (the Linux system controller) to reload Gunicorn and Nginx to activate the new logic.

Run this command on your EC2 terminal:
```bash
# Restart Gunicorn (healthhive) and Nginx reverse proxy
sudo systemctl restart healthhive nginx
```
* **Service Logic:**
  * **`healthhive` (Gunicorn/Flask):** Shuts down old worker processes and spins up new ones to load updated Python code.
  * **`nginx`:** Reloads configurations to proxy incoming port 80 traffic down to Gunicorn's Unix socket file.

---

## 📈 Verification Steps

Open your browser and load the live IP: **[http://13.233.149.34](http://13.233.149.34)**

1. **Verify Scraper:** Search for `"Dolo 650"` and check if correct prices are matched and displayed.
2. **Verify Database Fallback:** Search for a non-existent medicine (e.g., `"Augumentine"`) and ensure the live comparison table is loaded with a warning box.
3. **Verify Theme Switching:** Toggle the theme using the navbar button and verify color transitions.
