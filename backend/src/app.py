from flask import Flask, jsonify, request, render_template_string
import jwt
from datetime import datetime, timedelta
import os
import secrets
import logging
from functools import wraps

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# In production, use environment variable or secure secret management
SECRET_KEY = os.getenv('JWT_SECRET_KEY', secrets.token_hex(32))

# JWT validation decorator
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        
        # Check for token in Authorization header
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            try:
                token = auth_header.split(" ")[1]  # Bearer <token>
            except IndexError:
                return jsonify({'error': 'Invalid token format'}), 401
        
        if not token:
            return jsonify({'error': 'Token is missing'}), 401
        
        try:
            # Decode and validate the token
            data = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
            request.current_user = data
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token has expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Invalid token'}), 401
        
        return f(*args, **kwargs)
    
    return decorated

@app.route('/app', methods=['GET'])
def get_token():
    """
    Returns a JWT token with a session and custom role claim
    If a valid bearer token is provided, returns the same token
    """
    # Check for existing token in Authorization header
    if 'Authorization' in request.headers:
        auth_header = request.headers['Authorization']
        try:
            existing_token = auth_header.split(" ")[1]  # Bearer <token>
            
            # Try to decode and validate the existing token
            decoded = jwt.decode(existing_token, SECRET_KEY, algorithms=['HS256'])
            
            # Token is valid, return it
            session_id = decoded.get('session')
            role = decoded.get('role')
            
            logger.info(f"Valid token reused for session: {session_id}")
            
            return jsonify({
                'token': existing_token,
                'session': session_id,
                'role': role,
                'reused': True
            }), 200
            
        except (IndexError, jwt.ExpiredSignatureError, jwt.InvalidTokenError) as e:
            # Token invalid or expired, generate new one
            logger.info(f"Invalid/expired token provided, generating new token. Error: {str(e)}")
    
    # Generate a unique session identifier
    session_id = secrets.token_hex(16)
    
    # Create the JWT payload
    payload = {
        'session': session_id,
        'role': 'User',
        'iat': datetime.utcnow(),  # Issued at
        'exp': datetime.utcnow() + timedelta(hours=24)  # Expires in 24 hours
    }
    
    # Generate the JWT token
    token = jwt.encode(payload, SECRET_KEY, algorithm='HS256')
    
    logger.info(f"New token generated for session: {session_id}")
    
    return jsonify({
        'token': token,
        'session': session_id,
        'role': 'User',
        'reused': False
    }), 200

@app.route('/validate', methods=['POST'])
def validate_session():
    """
    Validates session information and logs diagnostics
    Accepts JSON with session data and optional JWT token
    """
    data = request.get_json() or {}
    
    # Extract information from request
    session_id = data.get('session')
    token = data.get('token')
    client_info = data.get('client_info', {})
    
    logger.info("=" * 80)
    logger.info("VALIDATION REQUEST RECEIVED")
    logger.info("=" * 80)
    
    # Log request metadata
    logger.info(f"Client IP: {request.remote_addr}")
    logger.info(f"User-Agent: {request.headers.get('User-Agent', 'N/A')}")
    logger.info(f"Content-Type: {request.headers.get('Content-Type', 'N/A')}")
    logger.info(f"Request Method: {request.method}")
    
    # Log session information
    logger.info("-" * 80)
    logger.info("SESSION INFORMATION")
    logger.info("-" * 80)
    logger.info(f"Session ID: {session_id}")
    
    # Log client info if provided
    if client_info:
        logger.info("-" * 80)
        logger.info("CLIENT INFORMATION")
        logger.info("-" * 80)
        for key, value in client_info.items():
            logger.info(f"{key}: {value}")
    
    # Validate and log token information if provided
    token_valid = False
    token_info = {}
    
    if token:
        logger.info("-" * 80)
        logger.info("TOKEN VALIDATION")
        logger.info("-" * 80)
        logger.info(f"Token (first 20 chars): {token[:20]}...")
        
        try:
            decoded = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
            token_valid = True
            token_info = decoded
            
            logger.info("✓ Token is VALID")
            logger.info(f"Token Session: {decoded.get('session')}")
            logger.info(f"Token Role: {decoded.get('role')}")
            logger.info(f"Token Issued At: {datetime.fromtimestamp(decoded.get('iat')).isoformat()}")
            logger.info(f"Token Expires At: {datetime.fromtimestamp(decoded.get('exp')).isoformat()}")
            
            # Check if session matches token
            if session_id and session_id != decoded.get('session'):
                logger.warning(f"⚠ Session ID mismatch! Provided: {session_id}, Token: {decoded.get('session')}")
            else:
                logger.info("✓ Session ID matches token")
                
        except jwt.ExpiredSignatureError:
            logger.error("✗ Token has EXPIRED")
            token_info['error'] = 'Token expired'
        except jwt.InvalidTokenError as e:
            logger.error(f"✗ Token is INVALID: {str(e)}")
            token_info['error'] = 'Invalid token'
    else:
        logger.info("No token provided in request")
    
    # Log all request data
    logger.info("-" * 80)
    logger.info("FULL REQUEST DATA")
    logger.info("-" * 80)
    logger.info(f"{data}")
    logger.info("=" * 80)
    
    # Prepare response
    response = {
        'status': 'validation_complete',
        'session_received': session_id,
        'token_valid': token_valid,
        'timestamp': datetime.utcnow().isoformat(),
        'diagnostics': {
            'client_ip': request.remote_addr,
            'user_agent': request.headers.get('User-Agent', 'N/A'),
            'token_provided': token is not None,
            'session_provided': session_id is not None,
        }
    }
    
    if token_valid:
        response['token_info'] = token_info
    elif token:
        response['token_error'] = token_info.get('error', 'Unknown error')
    
    return jsonify(response), 200

@app.route('/api/protected', methods=['POST'])
@token_required
def protected_endpoint():
    """
    Protected endpoint that requires a valid JWT token
    Echoes back the data sent with user info from token
    """
    data = request.get_json()
    
    logger.info(f"Protected endpoint accessed by session: {request.current_user.get('session')}")
    
    return jsonify({
        'message': 'Success! You sent authenticated data',
        'your_data': data,
        'user_info': {
            'session': request.current_user.get('session'),
            'role': request.current_user.get('role'),
            'token_issued_at': datetime.fromtimestamp(request.current_user.get('iat')).isoformat(),
            'token_expires_at': datetime.fromtimestamp(request.current_user.get('exp')).isoformat()
        }
    }), 200

@app.route('/test')
def test_page():
    """
    Test page with JavaScript to demonstrate JWT flow
    """
    html = """
<!DOCTYPE html>
<html>
<head>
    <title>JWT Test Page</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            max-width: 900px;
            margin: 50px auto;
            padding: 20px;
            background: #f5f5f5;
        }
        .container {
            background: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        h1 {
            color: #333;
            border-bottom: 3px solid #4CAF50;
            padding-bottom: 10px;
        }
        button {
            background: #4CAF50;
            color: white;
            border: none;
            padding: 12px 24px;
            margin: 10px 5px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 16px;
        }
        button:hover {
            background: #45a049;
        }
        button:disabled {
            background: #ccc;
            cursor: not-allowed;
        }
        .output {
            background: #f9f9f9;
            border: 1px solid #ddd;
            border-radius: 4px;
            padding: 15px;
            margin: 15px 0;
            white-space: pre-wrap;
            font-family: monospace;
            font-size: 12px;
            max-height: 400px;
            overflow-y: auto;
        }
        input {
            width: 100%;
            padding: 10px;
            margin: 10px 0;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 14px;
            box-sizing: border-box;
        }
        .status {
            padding: 10px;
            margin: 10px 0;
            border-radius: 4px;
            font-weight: bold;
        }
        .status.success {
            background: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
        }
        .status.error {
            background: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🔐 JWT Authentication Test</h1>
        
        <div id="status"></div>
        
        <h2>Step 1: Get JWT Token</h2>
        <button onclick="getToken()">Get New Token</button>
        <button id="reuseBtn" onclick="reuseToken()" disabled>Reuse Existing Token</button>
        
        <h2>Step 2: Validate Session</h2>
        <button id="validateBtn" onclick="validateSession()" disabled>Validate Session</button>
        
        <h2>Step 3: Send Authenticated Request</h2>
        <input type="text" id="messageInput" placeholder="Enter a message to send..." value="Hello from the test page!">
        <button id="sendBtn" onclick="sendAuthenticatedRequest()">Send to Protected Endpoint</button>
        <p style="color: #666; font-size: 14px; margin-top: 5px;">💡 Try this without a token to see authorization fail!</p>
        
        <h2>Response:</h2>
        <div id="output" class="output">Click "Get Token" to start...</div>
    </div>

    <script>
        let jwtToken = null;
        let sessionId = null;

        function setStatus(message, isError = false) {
            const statusDiv = document.getElementById('status');
            statusDiv.className = 'status ' + (isError ? 'error' : 'success');
            statusDiv.textContent = message;
        }

        function log(message) {
            const output = document.getElementById('output');
            const timestamp = new Date().toLocaleTimeString();
            output.textContent += `[${timestamp}] ${message}\\n\\n`;
            output.scrollTop = output.scrollHeight;
        }

        async function getToken() {
            log('📡 Fetching token from /app...');
            
            try {
                const response = await fetch('/app');
                const data = await response.json();
                
                jwtToken = data.token;
                sessionId = data.session;
                
                log('✅ Token received!');
                log(JSON.stringify(data, null, 2));
                
                if (data.reused) {
                    setStatus('♻️  Token reused! Session: ' + sessionId.substring(0, 8) + '...');
                } else {
                    setStatus('🆕 New token created! Session: ' + sessionId.substring(0, 8) + '...');
                }
                
                // Enable buttons
                document.getElementById('validateBtn').disabled = false;
                document.getElementById('reuseBtn').disabled = false;
                
            } catch (error) {
                log('❌ Error: ' + error.message);
                setStatus('Error fetching token', true);
            }
        }

        async function reuseToken() {
            if (!jwtToken) {
                setStatus('Get a token first!', true);
                return;
            }
            
            log('📡 Sending existing token to /app to verify reuse...');
            
            try {
                const response = await fetch('/app', {
                    headers: {
                        'Authorization': 'Bearer ' + jwtToken
                    }
                });
                const data = await response.json();
                
                const oldToken = jwtToken;
                jwtToken = data.token;
                sessionId = data.session;
                
                log('✅ Response received!');
                log(JSON.stringify(data, null, 2));
                
                if (data.reused && oldToken === jwtToken) {
                    log('✓ Same token returned! Token was reused.');
                    setStatus('♻️  Token reused successfully!');
                } else {
                    log('⚠️  Different token returned. Old token might be invalid/expired.');
                    setStatus('🆕 New token generated (old token was invalid)');
                }
                
            } catch (error) {
                log('❌ Error: ' + error.message);
                setStatus('Error reusing token', true);
            }
        }

        async function validateSession() {
            if (!jwtToken || !sessionId) {
                setStatus('Get a token first!', true);
                return;
            }
            
            log('📡 Validating session at /validate...');
            
            try {
                const response = await fetch('/validate', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        session: sessionId,
                        token: jwtToken,
                        client_info: {
                            browser: navigator.userAgent,
                            platform: navigator.platform,
                            language: navigator.language,
                            timestamp: new Date().toISOString()
                        }
                    })
                });
                
                const data = await response.json();
                
                log('✅ Validation response:');
                log(JSON.stringify(data, null, 2));
                
                if (data.token_valid) {
                    setStatus('✓ Token is valid! Check server logs for diagnostics.');
                } else {
                    setStatus('⚠ Token validation failed. Check server logs.', true);
                }
                
            } catch (error) {
                log('❌ Error: ' + error.message);
                setStatus('Error validating session', true);
            }
        }

        async function sendAuthenticatedRequest() {
            const message = document.getElementById('messageInput').value;
            
            if (!jwtToken) {
                log('⚠️  No token available - sending request WITHOUT authentication...');
                log('This should fail with 401 Unauthorized');
            } else {
                log('📡 Sending authenticated request to /api/protected...');
                log('Token: ' + jwtToken.substring(0, 20) + '...');
            }
            
            log('Message: ' + message);
            
            try {
                const headers = {
                    'Content-Type': 'application/json'
                };
                
                // Only add Authorization header if we have a token
                if (jwtToken) {
                    headers['Authorization'] = 'Bearer ' + jwtToken;
                }
                
                const response = await fetch('/api/protected', {
                    method: 'POST',
                    headers: headers,
                    body: JSON.stringify({
                        message: message,
                        timestamp: new Date().toISOString()
                    })
                });
                
                const data = await response.json();
                
                if (response.ok) {
                    log('✅ Authenticated request successful!');
                    log(JSON.stringify(data, null, 2));
                    setStatus('✓ Protected endpoint accessed successfully!');
                } else {
                    log('❌ Request rejected - Status: ' + response.status);
                    log('Error: ' + JSON.stringify(data, null, 2));
                    setStatus('❌ ' + (data.error || 'Request failed'), true);
                }
                
            } catch (error) {
                log('❌ Error: ' + error.message);
                setStatus('Error sending request', true);
            }
        }
    </script>
</body>
</html>
    """
    return render_template_string(html)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

