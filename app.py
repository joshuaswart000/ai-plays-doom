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
weights = np.random.rand(19200, 3) - 0.5
best_weights = np.copy(weights)
best_score = -1
generation = 1
start_time = time.time()

def mutate_brain(intensity=0.05):
    global weights, generation, best_weights
    # Always start mutating from the BEST known version
    weights = np.copy(best_weights) 
    mutation = (np.random.rand(19200, 3) - 0.5) * intensity
    weights += mutation
    generation += 1
    print(f"Gen {generation} | Tweak intensity: {intensity}")

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
        time.sleep(600)

# --- AI AGENT ---
stats = {"deaths": 0, "level": "E1M1", "kills": 0, "gen": 1, "best": 0}

def run_ai_agent():
    global stats, best_score, best_weights, start_time
    game = vzd.DoomGame()
    game.set_doom_game_path("doom1.wad") 
    game.load_config(os.path.join(vzd.scenarios_path, "basic.cfg"))
    
    game.set_screen_resolution(vzd.ScreenResolution.RES_160X120)
    game.set_screen_format(vzd.ScreenFormat.GRAY8)
    game.set_render_hud(False)
    game.set_window_visible(False)
    game.init()

    start_time = time.time()

    while True:
        if game.is_episode_finished():
            # SCORING LOGIC
            duration = time.time() - start_time
            kills = game.get_game_variable(vzd.GameVariable.KILLCOUNT)
            # Score = 1 point per second alive + 100 per kill
            current_score = duration + (kills * 100)

            if current_score > best_score:
                best_score = current_score
                best_weights = np.copy(weights)
                stats["best"] = round(best_score, 1)
                print(f"NEW BEST: {stats['best']}")

            stats["deaths"] += 1
            mutate_brain()
            stats["gen"] = generation
            socketio.emit('stats_update', stats)
            
            game.new_episode()
            start_time = time.time()

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
        time.sleep(0.04)

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
                .stats { display: flex; justify-content: center; gap: 20px; font-size: 1.1rem; margin: 20px 0; flex-wrap: wrap; }
                #doomCanvas { border: 4px solid #333; box-shadow: 0 0 20px #0f0; width: 640px; height: 480px; image-rendering: pixelated; }
                .val { color: #fff; }
                .best-tag { color: #ff0; font-weight: bold; }
            </style>
        </head>
        <body>
            <h1>AI DOOM SLAYER</h1>
            <div class="stats">
                <div>GEN: <span id="gen" class="val">1</span></div>
                <div>DEATHS: <span id="deaths" class="val">0</span></div>
                <div>KILLS: <span id="kills" class="val">0</span></div>
                <div class="best-tag">HI-SCORE: <span id="best">0</span></div>
            </div>
            <canvas id="doomCanvas" width="160" height="120"></canvas>
            <p style="color: #666;">Evolutionary Neural Network (Numpy) | Mutation on Death</p>

            <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
            <script>
                var socket = io();
                var canvas = document.getElementById('doomCanvas');
                var ctx = canvas.getContext('2d');

                socket.on('stats_update', (data) => {
                    document.getElementById('deaths').innerText = data.deaths;
                    document.getElementById('kills').innerText = data.kills;
                    document.getElementById('gen').innerText = data.gen;
                    document.getElementById('best').innerText = data.best;
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
