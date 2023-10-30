from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
import boto3
import os
import json
import time

# Initialize Flask and Socket.IO
app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

# Initialize Boto3 client
aws_access_key_id = os.getenv('AWS_ACCESS_KEY_ID')
aws_secret_access_key = os.getenv('AWS_SECRET_ACCESS_KEY')
aws_session = boto3.Session(
    aws_access_key_id=aws_access_key_id,
    aws_secret_access_key=aws_secret_access_key,
    profile_name='Sandbox'
)
bedrock = aws_session.client(
    service_name='bedrock-runtime',
    region_name='us-east-1',
    endpoint_url='https://bedrock-runtime.us-east-1.amazonaws.com'
)

# Initialize conversation history
conversation_history = []

@app.route('/')
def index():
    return render_template('index.html')

# WebSocket event for handling queries
# Initialize conversation history as a string
conversation_history = ""

# WebSocket event for handling queries
@socketio.on('query')
def handle_query_event(user_input):
    global conversation_history

    # Append the user's message to the conversation history
    conversation_history += f"\nHuman: {user_input}"

    body_dict = {
        "prompt": f"{conversation_history}\nAssistant:",
        "max_tokens_to_sample": 15000,
        "temperature": 0.6,
        "top_k": 350,
        "top_p": 0.999,

    }

    body = json.dumps(body_dict).encode('utf-8')

    try:
        response = bedrock.invoke_model_with_response_stream(
            modelId='anthropic.claude-v2',
            body=body
        )
    except Exception as e:
        emit('response', {'error': str(e)})
        return

    stream = response.get('body')
    if stream:
        for event in stream:
            chunk = event.get('chunk')
            if chunk:
                chunk_json = json.loads(chunk.get('bytes').decode())
                completion = chunk_json.get('completion', '')
                
                # Append assistant's reply to the conversation history
                conversation_history += f"\nAssistant: {completion}"

                emit('response', {"response": completion})

            stop_reason = chunk_json.get('stop_reason', None)
            if stop_reason == 'stop_sequence':
                break

if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=5500)
