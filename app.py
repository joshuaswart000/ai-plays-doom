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

# --- REINFORCED BRAIN SETUP ---
np.random.seed(42)
# 160x120 pixels = 19200 inputs -> 3 outputs [Forward, Left, Right]
# We use a smaller weight range to prevent "over-steering"
weights = (np.random.rand(19200, 3) - 0.5) * 0.01 
best_weights = np.copy(weights)
best_score = -1
generation = 1

def mutate_brain(intensity=0.05):
    global weights, generation, best_weights
    # Start from the best and apply a "Gaussian" mutation (more natural learning)
    weights = np.copy(best_weights) + np.random.normal(0, intensity, size=(19200, 3))
    generation += 1

def get_ai_action(screen_buffer):
    # Flatten and normalize pixels to -1 to 1 range
    flattened = (screen_buffer.flatten() / 127.5) - 1.0
    # Matrix math + Tanh activation to make decisions "sharper"
    prediction = np.tanh(np.dot(flattened, weights))
    # Action mapping: [Forward, Left, Right]
    # We lower the threshold for Forward (0) to encourage movement
    return [1 if prediction[0] > -0.2 else 0, 1 if prediction[1] > 0.5 else 0, 1 if prediction[2] > 0.5 else 0]

# --- STAY AWAKE ---
def keep_awake():
    url = "https://ai-plays-doom.onrender.com"
    while True:
        try: requests.get(url, timeout=10, headers={'User-Agent': 'Mozilla/5.0'})
        except: pass
        time.sleep(600)

# --- AI AGENT ---
stats = {"deaths": 0, "level": "E1M1", "kills": 0, "gen": 1, "best": 0}

def run_ai_agent():
    global stats, best_score, best_weights
    game = vzd.DoomGame()
    game.set_doom_game_path("doom1.wad") 
    game.load_config(os.path.join(vzd.scenarios_path, "basic.cfg"))
    
    game.set_screen_resolution(vzd.ScreenResolution.RES_160X120)
    game.set_screen_format(vzd.ScreenFormat.GRAY8)
    game.set_render_hud(False)
    game.set_window_visible(False)
    game.init()

    while True:
        game.new_episode()
        start_time = time.time()
        dist_traveled = 0
        last_x, last_y = 0, 0
        episode_kills = 0

        while not game.is_episode_finished():
            state = game.get_state()
            if state:
                # 1. Track Movement
                curr_x = game.get_game_variable(vzd.GameVariable.POSITION_X)
                curr_y = game.get_game_variable(vzd.GameVariable.POSITION_Y)
                dist_traveled += np.sqrt((curr_x - last_x)**2 + (curr_y - last_y)**2)
                last_x, last_y = curr_x, curr_y

                # 2. AI Decision
                frame = state.screen_buffer
                action = get_ai_action(frame)
                # Force "Fire" button occasionally to clear paths
                action.append(1 if np.random.random() > 0.95 else 0)
                game.make_action(action)

                # 3. UI Update (Streaming)
                _, buffer = cv2.imencode('.jpg', frame)
                jpg_as_text = base64.b64encode(buffer).decode('utf-8')
                socketio.emit('new_frame', {'image': jpg_as_text})

            socketio.sleep(0)
            time.sleep(0.03) # Speed up slightly for faster training

        # --- EVALUATE ---
        kills = game.get_game_variable(vzd.GameVariable.KILLCOUNT)
        # Score favors Distance > Survival Time
        current_score = (dist_traveled / 5.0) + (kills * 1000)
        
        if dist_traveled < 100: # Penalty for not moving
            current_score = 0

        if current_score >= best_score:
            best_score = current_score
            best_weights = np.copy(weights)
            stats["best"] = round(best_score, 1)

        stats["deaths"] += 1
        stats["kills"] += kills
        mutate_brain(intensity=0.04) # Lower intensity for more stable learning
        stats["gen"] = generation
        socketio.emit('stats_update', stats)

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
                h1 { color: #f00; text-shadow: 0 0 10px #f00; }
                .stats { display: flex; justify-content: center; gap: 20px; font-size: 1.2rem; margin: 20px 0; border-bottom: 1px solid #333; padding-bottom: 10px; }
                #doomCanvas { border: 4px solid #333; box-shadow: 0 0 20px #0f0; width: 640px; height: 480px; image-rendering: pixelated; background: #111; }
                .val { color: #fff; font-weight: bold; }
            </style>
        </head>
        <body>
            <h1>AI DOOM SLAYER</h1>
            <div class="stats">
                <div>GEN: <span id="gen" class="val">1</span></div>
                <div>DEATHS: <span id="deaths" class="val">0</span></div>
                <div>KILLS: <span id="kills" class="val">0</span></div>
                <div style="color:#ff0">HI-SCORE: <span id="best">0</span></div>
            </div>
            <canvas id="doomCanvas" width="160" height="120"></canvas>
            <p style="color: #888; margin-top: 20px;">Deep Learning Inference via Matrix Tanh | Fitness: Distance + Kills</p>
            <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
            <script>
                var socket = io();
                var ctx = document.getElementById('doomCanvas').getContext('2d');
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
