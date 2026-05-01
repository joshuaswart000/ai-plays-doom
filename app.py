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
def run_ai_agent():
    game = vzd.DoomGame()
    # Use 'basic.cfg' (standard test map)
    game.load_config(os.path.join(vzd.scenarios_path, "basic.cfg"))
    game.set_window_visible(False) # MUST BE HEADLESS FOR RENDER
    game.init()
    
    print("AI Agent Started.")
    while True:
        if game.is_episode_finished():
            game.new_episode()
        
        state = game.get_state()
        # AI Logic: Replace this with model.predict(state.screen_buffer) later
        # For now, let's just make it move/shoot randomly
        game.make_action([1, 0, 1]) 
        
        # Every few frames, we could emit data to the front-end here
        # socketio.emit('frame', {'data': 'image_base64_here'})
        
        time.sleep(0.05)

# --- WEB ROUTES ---
@app.route('/')
def index():
    return render_template_string('''
        <h1>AI Playing Doom 24/7</h1>
        <p>Status: Running on Render Free Tier</p>
        <div id="status">Connecting to AI stream...</div>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
        <script>
            var socket = io();
            socket.on('connect', () => { document.getElementById('status').innerText = "AI Online"; });
        </script>
    ''')

if __name__ == '__main__':
    # Start the keep-awake thread
    threading.Thread(target=keep_awake, daemon=True).start()
    # Start the AI thread
    threading.Thread(target=run_ai_agent, daemon=True).start()
    
    # Run the server
    port = int(os.environ.get('PORT', 3000))
    socketio.run(app, host='0.0.0.0', port=port)
