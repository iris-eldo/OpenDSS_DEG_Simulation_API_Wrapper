from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import google.generativeai as genai
import os
import webbrowser
import threading
import time
import signal
import sys
import atexit
from dotenv import load_dotenv
from functools import partial

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Global variable to control the server
server = None

# Configure Gemini API
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
if not GOOGLE_API_KEY:
    raise ValueError("No GOOGLE_API_KEY found in environment variables")

genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel('gemini-pro')

def open_browser():
    # Wait for the server to start
    time.sleep(1.5)
    webbrowser.open_new('http://127.0.0.1:5000')

@app.route('/')
def index():
    return render_template('index.html')

def shutdown_server():
    """Shutdown the server and exit the application."""
    print("\nShutting down server...")
    func = request.environ.get('werkzeug.server.shutdown')
    if func is None:
        print("Not running with the Werkzeug Server")
        return 'Server shutting down...', 200
    func()
    return 'Server shutting down...', 200

@app.route('/shutdown', methods=['POST'])
def shutdown():
    """Handle shutdown request from the client."""
    print("Received shutdown request from client")
    # Start a new thread to handle the shutdown
    def shutdown_thread():
        time.sleep(1)  # Give the response time to be sent
        shutdown_server()
        os._exit(0)  # Force exit the application
    
    threading.Thread(target=shutdown_thread).start()
    return 'Server shutting down...', 200

@app.route('/chat', methods=['POST'])
def chat():
    user_message = request.json.get('message', '')
    if not user_message.strip():
        return jsonify({'error': 'Empty message'}), 400
    
    try:
        # Get chat history from session or initialize
        if 'chat_history' not in session:
            session['chat_history'] = []
        
        # Add user message to history
        session['chat_history'].append({"role": "user", "parts": [user_message]})
        
        # Generate response
        response = model.generate_content(user_message)
        
        # Add AI response to history
        ai_response = response.text
        session['chat_history'].append({"role": "model", "parts": [ai_response]})
        
        # Keep only the last 10 messages to avoid session size limits
        session['chat_history'] = session['chat_history'][-10:]
        
        return jsonify({'response': ai_response})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def signal_handler(sig, frame, server):
    print('\nShutting down server...')
    if server:
        server.shutdown()
    sys.exit(0)

def signal_handler(signum, frame, server):
    print(f"\nReceived signal {signum}, shutting down...")
    if server:
        server.close()
    sys.exit(0)

if __name__ == '__main__':
    # Set up signal handlers
    signal.signal(signal.SIGINT, lambda s, f: signal_handler(s, f, None))
    signal.signal(signal.SIGTERM, lambda s, f: signal_handler(s, f, None))
    
    # Start the browser in a separate thread
    threading.Thread(target=open_browser).start()
    
    # Run the Flask app
    from waitress import serve
    server = serve(app, host='0.0.0.0', port=5000, threads=4)
    
    # Register cleanup function
    atexit.register(lambda: print("\nCleaning up before exit..."))
    
    try:
        print("Server starting...")
        server.run()
    except KeyboardInterrupt:
        print("\nKeyboard interrupt received, shutting down...")
    except Exception as e:
        print(f"\nError: {e}")
    finally:
        print("Server has been stopped")
        server.close()
        sys.exit(0)
