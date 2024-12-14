from flask import Flask, request, Response, stream_with_context, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import datetime

from agent.initialize_agent import initialize_agent
from agent.run_agent import run_agent
from db.setup import setup
from db.tokens import get_tokens
from db.nfts import get_nfts

load_dotenv()
app = Flask(__name__)
CORS(app)

# Setup SQLite tables
setup()

# Initialize the agent
agent_executor = initialize_agent()
app.agent_executor = agent_executor

# Interact with the agent
@app.route("/api/chat", methods=['POST'])
def chat():
    try:
        data = request.get_json()
        # Parse the user input from the request
        input = data['input']
        # Use the conversation_id passed in the request for conversation memory
        config = {"configurable": {"thread_id": data['conversation_id']}}
        return Response(
            stream_with_context(run_agent(input, app.agent_executor, config)),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'Content-Type': 'text/event-stream',
                'Connection': 'keep-alive',
                'X-Accel-Buffering': 'no'
            }
        )
    except Exception as e:
        app.logger.error(f"Unexpected error in chat endpoint: {str(e)}")
        return jsonify({'error': 'An unexpected error occurred'}), 500
    
# Retrieve a list of tokens the agent has deployed
@app.route("/tokens", methods=['GET'])
def tokens():
    try:
        tokens = get_tokens()
        return jsonify({'tokens': tokens}), 200
    except Exception as e:
        app.logger.error(f"Unexpected error in tokens endpoint: {str(e)}")
        return jsonify({'error': 'An unexpected error occurred'}), 500
    
# Retrieve a list of tokens the agent has deployed
@app.route("/nfts", methods=['GET'])
def nfts():
    try:
        nfts = get_nfts()
        return jsonify({'nfts': nfts}), 200
    except Exception as e:
        app.logger.error(f"Unexpected error in nfts endpoint: {str(e)}")
        return jsonify({'error': 'An unexpected error occurred'}), 500

@app.route("/api/conversations/<conversation_id>", methods=['GET'])
def get_conversation(conversation_id):
    try:
        # Access the memory directly from the agent_executor
        memory = app.agent_executor.checkpointer
        print(f"Memory object type: {type(memory)}")
        
        # Get the conversation history for the specific thread
        history = memory.get({"configurable": {"thread_id": conversation_id}})
        print(f"Raw history: {history}")
        
        if not history:
            print(f"No history found for conversation {conversation_id}")
            return jsonify({'messages': []}), 200
            
        # Extract messages from the channel_values
        messages = []
        if 'channel_values' in history and 'messages' in history['channel_values']:
            message_list = history['channel_values']['messages']
            for msg in message_list:
                print(f"Processing message: {msg}")
                
                if hasattr(msg, 'type') and msg.type == 'human':
                    messages.append({
                        "role": "human",
                        "content": msg.content
                    })
                elif hasattr(msg, 'type') and msg.type == 'ai':
                    messages.append({
                        "role": "agent",
                        "content": msg.content
                    })
                # You might need to add additional conditions for tool messages
        
        print(f"Final messages array: {messages}")
        return jsonify({'messages': messages}), 200
    except Exception as e:
        app.logger.error(f"Error fetching conversation {conversation_id}: {str(e)}")
        print(f"Full error details: {str(e)}")
        return jsonify({'error': 'An unexpected error occurred'}), 500

@app.route("/health", methods=['GET'])
def health():
    try:
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.datetime.utcnow().isoformat()
        }), 200
    except Exception as e:
        app.logger.error(f"Health check failed: {str(e)}")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 500

if __name__ == "__main__":
    app.run()
    