# Habit Up

A habit tracker that looks like a paper monthly planner. Tick off daily habits, build streaks, earn badges and compete with friends on a leaderboard.

## Features
- Sign up and log in with a name and password (each name has its own data)
- Daily habit grid with colour-coded circles, weekly and monthly goals, monthly notes
- Streaks, points and badges (first check-in, 7-day, 30-day)
- Circle percentage charts for the month and for each habit
- Group invite link and a friends leaderboard
- Installable as a PWA app

## How to run it on your computer

1. Install **Python 3** from https://www.python.org/downloads/ (tick **Add Python to PATH** during install).
2. Download this project: click the green **Code** button, then **Download ZIP**, and unzip it.
3. Open a terminal inside the unzipped folder (on Windows: open the folder, click the address bar, type `cmd`, press Enter).
4. Install the one package it needs:
   ```
   pip install flask
   ```
5. Start the app:
   ```
   python habitup.py
   ```
6. Open **http://localhost:5000** in your browser.

## Play with friends
Friends on the **same Wi-Fi** can open `http://YOUR-COMPUTER-IP:5000` while the app is running on your computer.
- Windows: run `ipconfig` and read the **IPv4 Address**.
- If it does not open, allow Python through the Windows firewall.

Sign up, tap **Add members +** and send your invite link. Friends who join your group appear on your leaderboard.

## Tech
Python (Flask), SQLite, plain HTML, CSS and JavaScript. The whole app is in one file, `habitup.py`. Data is saved in `habitup.db`, created next to it.
