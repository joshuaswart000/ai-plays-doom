import os
import time
import threading
import requests
import vizdoom as vzd
from flask import Flask, render_template_string
from flask_socketio import SocketIO, emit

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

# --- STAY AWAKE LOGIC ---
def keep_awake():
    """Pings the app every 14 minutes to prevent Render sleep."""
    # Use the RENDER_EXTERNAL_HOSTNAME env var provided by Render
    url = f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME')}.onrender.com"
    while True:
        try:
            requests.get(url)
            print("Self-ping successful.")
        except Exception as e:
            print(f"Ping failed: {e}")
        time.sleep(14 * 60) # 14 minutes

# --- AI AGENT LOGIC ---
# Initialize global stats
stats = {"deaths": 0, "level": "E1M1", "kills": 0}

def run_ai_agent():
    global stats
    game = vzd.DoomGame()
    game.set_doom_game_path("doom1.wad")
    game.load_config(os.path.join(vzd.scenarios_path, "basic.cfg"))

    game.set_screen_resolution(vzd.ScreenResolution.RES_160X120) # Tiny resolution
    game.set_screen_format(vzd.ScreenFormat.GRAY8) # Grayscale uses 3x less RAM
    game.set_render_hud(False) 
    
    game.set_window_visible(False)
    game.init()

    while True:
        if game.is_episode_finished():
            stats["deaths"] += 1  # Increment death counter
            socketio.emit('stats_update', stats) # Send to website
            game.new_episode()

        # Update other stats periodically
        current_kills = game.get_game_variable(vzd.GameVariable.KILLCOUNT)
        if current_kills != stats["kills"]:
            stats["kills"] = current_kills
            socketio.emit('stats_update', stats)

        game.make_action([1, 0, 1])
        time.sleep(0.02)



# --- WEB ROUTES ---
@app.route('/')
def index():
    return render_template_string('''
        <body style="background:#000; color:#0f0; font-family:monospace; text-align:center;">
            <h1 style="text-shadow: 0 0 10px #f00; color:#f00;">AI DOOM SLAYER</h1>
            
            <div style="display:flex; justify-content:center; gap:20px; font-size:1.5rem; margin-bottom:20px;">
                <div>LEVEL: <span id="level">E1M1</span></div>
                <div>DEATHS: <span id="deaths">0</span></div>
                <div>KILLS: <span id="kills">0</span></div>
            </div>

            <canvas id="doomCanvas" style="border:4px solid #333; box-shadow: 0 0 20px #0f0;"></canvas>

            <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
            <script>
                var socket = io();
                socket.on('stats_update', (data) => {
                    document.getElementById('deaths').innerText = data.deaths;
                    document.getElementById('level').innerText = data.level;
                    document.getElementById('kills').innerText = data.kills;
                });
            </script>
        </body>
    ''')

if __name__ == '__main__':
    # Start the keep-awake thread
    threading.Thread(target=keep_awake, daemon=True).start()
    # Start the AI thread
    threading.Thread(target=run_ai_agent, daemon=True).start()
    
    # Run the server
    port = int(os.environ.get('PORT', 3000))
    socketio.run(app, host='0.0.0.0', port=port)
