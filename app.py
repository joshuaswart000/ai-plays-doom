import os
import time
import threading
import requests
import vizdoom as vzd
from flask import Flask, render_template_string
from flask_socketio import SocketIO
import base64
import cv2
import numpy as np

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# --- EVOLUTIONARY BRAIN SETUP ---
np.random.seed(42)
# 19200 pixels -> 3 actions
weights = np.random.rand(19200, 3) - 0.5
generation = 1

def mutate_brain(intensity=0.02):
    """Slightly alters the weights to 'learn' new behaviors on death."""
    global weights, generation
    mutation = (np.random.rand(19200, 3) - 0.5) * intensity
    weights += mutation
    generation += 1
    print(f"Brain Mutated. Now at Generation: {generation}")

def get_ai_action(screen_buffer):
    flattened = screen_buffer.flatten() / 255.0
    prediction = np.dot(flattened, weights)
    return [1 if x > 0 else 0 for x in prediction]

# --- STAY AWAKE ---
def keep_awake():
    url = "https://ai-plays-doom.onrender.com"
    while True:
        try:
            requests.get(url, timeout=10, headers={'User-Agent': 'Mozilla/5.0'})
        except:
            pass
        time.sleep(300)

# --- AI AGENT ---
stats = {"deaths": 0, "level": "E1M1", "kills": 0, "gen": 1}

def run_ai_agent():
    global stats
    game = vzd.DoomGame()
    game.set_doom_game_path("doom1.wad") 
    game.load_config(os.path.join(vzd.scenarios_path, "basic.cfg"))
    
    game.set_screen_resolution(vzd.ScreenResolution.RES_160X120)
    game.set_screen_format(vzd.ScreenFormat.GRAY8)
    game.set_render_hud(False)
    game.set_window_visible(False)
    game.init()

    while True:
        if game.is_episode_finished():
            stats["deaths"] += 1
            # EVOLVE: Change the brain slightly every time he dies
            mutate_brain()
            stats["gen"] = generation
            socketio.emit('stats_update', stats)
            game.new_episode()

        state = game.get_state()
        if state:
            frame = state.screen_buffer
            action = get_ai_action(frame)
            game.make_action(action)

            _, buffer = cv2.imencode('.jpg', frame)
            jpg_as_text = base64.b64encode(buffer).decode('utf-8')
            socketio.emit('new_frame', {'image': jpg_as_text})

            curr_kills = game.get_game_variable(vzd.GameVariable.KILLCOUNT)
            if curr_kills != stats["kills"]:
                stats["kills"] = curr_kills
                socketio.emit('stats_update', stats)

        socketio.sleep(0)
        time.sleep(0.05)

# --- WEB UI ---
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
                .gen-tag { color: #555; font-size: 0.8rem; }
            </style>
        </head>
        <body>
            <h1>AI DOOM SLAYER</h1>
            <div class="stats">
                <div>LEVEL: <span id="level">E1M1</span></div>
                <div>DEATHS: <span id="deaths">0</span></div>
                <div>KILLS: <span id="kills">0</span></div>
                <div style="color:#0af">GEN: <span id="gen">1</span></div>
            </div>
            <canvas id="doomCanvas" width="160" height="120"></canvas>
            <p class="gen-tag">Neural Network (Genetic Mutation on Death) - Learning 24/7</p>

            <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
            <script>
                var socket = io();
                var canvas = document.getElementById('doomCanvas');
                var ctx = canvas.getContext('2d');

                socket.on('stats_update', (data) => {
                    document.getElementById('deaths').innerText = data.deaths;
                    document.getElementById('kills').innerText = data.kills;
                    document.getElementById('gen').innerText = data.gen;
                });

                socket.on('new_frame', (data) => {
                    var img = new Image();
                    img.onload = function() { ctx.drawImage(img, 0, 0); };
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
    socketio.run(app, host='0.0.0.0', port=port, allow_unsafe_werkzeug=True)
