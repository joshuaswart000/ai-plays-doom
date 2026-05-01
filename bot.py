import vizdoom as vzd
import numpy as np
from stable_baselines3 import PPO
import time

def run_ai():
    # 1. Initialize the Doom Environment
    game = vzd.DoomGame()
    game.load_config("basic.cfg") # We'll need to add this file too
    game.set_window_visible(False) # Essential for headless servers
    game.init()

    # 2. Load the Pre-trained 'Brain'
    # For now, we use a random action placeholder until you upload a .zip model
    model = None 

    print("AI is entering the zone...")

    while True:
        if game.is_episode_finished():
            game.new_episode()

        state = game.get_state()
        img = state.screen_buffer # This is what the AI "sees"
        
        # AI decides what to do (placeholder logic)
        action = [0, 0, 1] # e.g., Shoot!
        game.make_action(action)
        
        # In a real setup, we would emit 'img' to the web-client here
        time.sleep(0.02) 

if __name__ == "__main__":
    run_ai()
