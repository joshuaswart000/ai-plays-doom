import os
import time
import threading
import requests
import vizdoom as vzd
from flask import Flask, render_template_string
from flask_socketio import SocketIO
import base64
import cv2
import random

app = Flask(__name__)
# Using 'threading' mode is more stable for Render's limited CPU
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# --- STAY AWAKE LOGIC ---
def keep_awake():
    while True:
        try:
            requests.get("https://ai-plays-doom.onrender.com", timeout=5)
            print("Self-ping: Awake")
        except:
            print("Ping failed")
        time.sleep(5*60) # 14 minutes

# --- AI AGENT LOGIC ---
stats = {"deaths": 0, "level": "E1M1", "kills": 0}

def run_ai_agent():
    global stats
    game = vzd.DoomGame()
    
    # Ensure this matches your filename on GitHub exactly
    game.set_doom_game_path("doom1.wad") 
    game.load_config(os.path.join(vzd.scenarios_path, "basic.cfg"))
    
    # RAM SAVERS: Essential for Render Free Tier
    game.set_screen_resolution(vzd.ScreenResolution.RES_160X120)
    game.set_screen_format(vzd.ScreenFormat.GRAY8)
    game.set_render_hud(False)
    game.set_window_visible(False)
    game.init()

    print("AI Agent Started")
    
    while True:
        if game.is_episode_finished():
            stats["deaths"] += 1
            socketio.emit('stats_update', stats)
            game.new_episode()

        state = game.get_state()
        if state:
            # Convert frame to image for the website
            frame = state.screen_buffer
            _, buffer = cv2.imencode('.jpg', frame)
            jpg_as_text = base64.b64encode(buffer).decode('utf-8')
            socketio.emit('new_frame', {'image': jpg_as_text})

            # Update Kills
            curr_kills = game.get_game_variable(vzd.GameVariable.KILLCOUNT)
            if curr_kills != stats["kills"]:
                stats["kills"] = curr_kills
                socketio.emit('stats_update', stats)

        # AI INPUT: Random actions to keep it moving/unfrozen
        # [Left, Right, Attack]
        action = [random.choice([0,1]), random.choice([0,1]), random.choice([0,1])]
        game.make_action(action)
        
        # Give the CPU a breath (approx 5-10 FPS)
        time.sleep(0.1)

# --- WEB ROUTES ---
@app.route('/')
def index():
    return render_template_string('''
        <!DOCTYPE html>
        <html>
        <head>
            <title>AI DOOM SLAYER</title>
            <style>
                body { background: #000; color: #0f0; font-family: monospace; text-align: center; margin: 0; padding: 20px; }
                h1 { color: #f00; text-shadow: 0 0 10px #f00; margin: 10px 0; }
                .stats { display: flex; justify-content: center; gap: 30px; font-size: 1.2rem; margin: 20px 0; }
                #doomCanvas { border: 4px solid #333; box-shadow: 0 0 20px #0f0; width: 640px; height: 480px; image-rendering: pixelated; }
            </style>
        </head>
        <body>
            <h1>AI DOOM SLAYER</h1>
            <div class="stats">
                <div>LEVEL: <span id="level">E1M1</span></div>
                <div>DEATHS: <span id="deaths">0</span></div>
                <div>KILLS: <span id="kills">0</span></div>
            </div>
            <canvas id="doomCanvas" width="160" height="120"></canvas>
            <p>Live AI Feed - Render Free Tier</p>

            <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
            <script>
                var socket = io();
                var canvas = document.getElementById('doomCanvas');
                var ctx = canvas.getContext('2d');

                socket.on('stats_update', (data) => {
                    document.getElementById('deaths').innerText = data.deaths;
                    document.getElementById('kills').innerText = data.kills;
                });

                socket.on('new_frame', (data) => {
                    var img = new Image();
                    img.onload = function() {
                        ctx.drawImage(img, 0, 0);
                    };
                    img.src = "data:image/jpeg;base64," + data.image;
                });
            </script>
        </body>
        </html>
    ''')

if __name__ == '__main__':
    threading.Thread(target=keep_awake, daemon=True).start()
    threading.Thread(target=run_ai_agent, daemon=True).start()
    
    port = int(os.environ.get('PORT', 10000))
    # Add allow_unsafe_werkzeug=True here:
    socketio.run(app, host='0.0.0.0', port=port, allow_unsafe_werkzeug=True)

