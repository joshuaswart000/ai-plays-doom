const express = require('express');
const fetch = require('node-fetch');
const app = express();
const PORT = process.env.PORT || 3000;

// 1. The Stay-Awake Logic
const URL = `https://${process.env.RENDER_EXTERNAL_HOSTNAME}.onrender.com`;
const INTERVAL = 14 * 60 * 1000; 

function keepAlive() {
  setInterval(async () => {
    try {
      await fetch(URL);
      console.log('Self-ping: Staying awake.');
    } catch (err) {
      console.error('Ping failed:', err);
    }
  }, INTERVAL);
}

// 2. Serve the Game Screen
app.get('/', (req, res) => {
  res.send(`
    <html>
      <body style="background:black; color:green; display:flex; flex-direction:column; align-items:center;">
        <h1>AI DOOM STREAM</h1>
        <div id="game-container" style="border:2px solid green;">
          <canvas id="doomCanvas" width="640" height="480"></canvas>
        </div>
        <p>Status: AI is thinking...</p>
      </body>
    </html>
  `);
});

app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
  keepAlive();
});
