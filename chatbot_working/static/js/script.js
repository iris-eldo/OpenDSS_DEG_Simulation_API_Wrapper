document.addEventListener('DOMContentLoaded', function() {
    // DOM Elements
    const chatToggle = document.getElementById('chat-toggle');
    const chatContainer = document.getElementById('chat-container');
    const chatMessages = document.getElementById('chat-messages');
    const userInput = document.getElementById('user-input');
    const sendBtn = document.getElementById('send-btn');
    const minimizeBtn = document.getElementById('minimize-chat');
    const closeAppBtn = document.getElementById('close-app');
    const chatHeader = document.querySelector('.chat-header');
    const refreshBtn = document.getElementById('refresh-btn');
    const analyticsContent = document.getElementById('analytics-content');
    
    // Debug logging
    function debugLog(message, data = null) {
        const timestamp = new Date().toISOString();
        console.log(`[${timestamp}] ${message}`, data || '');
    }
    
    // Close the application
    async function closeApplication() {
        debugLog('Closing application');
        try {
            // Notify the server to shut down
            const response = await fetch('/shutdown', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
            });
            
            debugLog('Shutdown response status:', response.status);
            
            // Close the browser tab after a short delay
            setTimeout(() => {
                debugLog('Closing window');
                window.close();
            }, 300);
            
        } catch (error) {
            console.error('Error shutting down:', error);
            debugLog('Error during shutdown', error);
            window.close(); // Still try to close the tab even if server shutdown fails
        }
    }
    
    // State
    let isChatOpen = false;
    let isMinimized = false;
    let isDragging = false;
    let startX, startY, startLeft, startTop;
    let isResizing = false;
    let startWidth, startHeight, startYResize, startXResize;
    
    // Initialize
    function init() {
        // Set initial chat state
        chatContainer.style.display = 'flex'; // Make sure chat container is flex
        chatContainer.style.flexDirection = 'column';
        
        // Load any saved chat state from localStorage
        const savedState = localStorage.getItem('chatState');
        if (savedState === 'open') {
            toggleChat();
        } else {
            // Make sure toggle button is visible if chat is closed
            chatToggle.style.display = 'flex';
            chatToggle.style.opacity = '1';
        }
        
        // Load chat history if available
        loadChatHistory();
        
        // Set up event listeners
        setupEventListeners();
        
        // Ensure proper initial state
        setTimeout(() => {
            chatMessages.scrollTop = chatMessages.scrollHeight;
        }, 100);
    }
    
    // Set up event listeners
    function setupEventListeners() {
        debugLog('Setting up event listeners');
        
        // Chat toggle
        chatToggle.addEventListener('click', (e) => {
            e.stopPropagation();
            toggleChat();
        });
        
        // Minimize chat
        minimizeBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            toggleMinimize();
        });
        
        // Close application
        closeAppBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            if (confirm('Are you sure you want to close the application?')) {
                closeApplication();
            }
        });
        
        // Send message on button click or Enter key
        sendBtn.addEventListener('click', sendMessage);
        userInput.addEventListener('keydown', function(e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });
        
        // Auto-resize textarea
        userInput.addEventListener('input', autoResizeTextarea);
        
        // Make chat draggable
        chatHeader.addEventListener('mousedown', startDrag);
        document.addEventListener('mousemove', drag);
        document.addEventListener('mouseup', stopDrag);
        
        // Make chat resizable
        const resizeHandle = document.createElement('div');
        resizeHandle.className = 'resize-handle';
        chatContainer.appendChild(resizeHandle);
        
        // Store initial position and size for resizing
        let startX, startY, startWidth, startHeight, startRight, startBottom;
        
        function startResize(e) {
            e.preventDefault();
            e.stopPropagation();
            debugLog('Starting resize');
            
            startX = e.clientX;
            startY = e.clientY;
            startWidth = parseInt(document.defaultView.getComputedStyle(chatContainer).width, 10);
            startHeight = parseInt(document.defaultView.getComputedStyle(chatContainer).height, 10);
            startRight = window.innerWidth - chatContainer.getBoundingClientRect().right;
            startBottom = window.innerHeight - chatContainer.getBoundingClientRect().bottom;
            
            document.addEventListener('mousemove', handleResize);
            document.addEventListener('mouseup', stopResize);
        }
        
        function handleResize(e) {
            e.preventDefault();
            
            // Calculate new width and height
            let newWidth = startWidth + (e.clientX - startX);
            let newHeight = startHeight + (e.clientY - startY);
            
            // Apply minimum and maximum constraints
            newWidth = Math.max(300, Math.min(window.innerWidth * 0.9, newWidth));
            newHeight = Math.max(400, Math.min(window.innerHeight * 0.9, newHeight));
            
            // Resize the container
            chatContainer.style.width = `${newWidth}px`;
            chatContainer.style.height = `${newHeight}px`;
            
            // Adjust position to maintain bottom-right corner
            const newRight = window.innerWidth - (e.clientX + (startWidth - (e.clientX - startX)));
            const newBottom = window.innerHeight - (e.clientY + (startHeight - (e.clientY - startY)));
            
            chatContainer.style.right = `${startRight}px`;
            chatContainer.style.bottom = `${startBottom}px`;
        }
        
        function stopResize() {
            debugLog('Stopping resize');
            document.removeEventListener('mousemove', handleResize);
            document.removeEventListener('mouseup', stopResize);
        }
        
        resizeHandle.addEventListener('mousedown', startResize);
        
        // Refresh analytics
        refreshBtn.addEventListener('click', refreshAnalytics);
        
        // Handle beforeunload to clean up resources
        window.addEventListener('beforeunload', () => {
            debugLog('Window is being unloaded');
            // Clean up any resources if needed
        });
        
        // Close chat when clicking outside
        document.addEventListener('click', (e) => {
            if (isChatOpen && !chatContainer.contains(e.target) && e.target !== chatToggle) {
                toggleChat();
            }
        });
        
        // Prevent chat from closing when clicking inside
        chatContainer.addEventListener('click', (e) => {
            e.stopPropagation();
        });
        
        debugLog('Event listeners set up');
    }
    
    // Toggle chat visibility
    function toggleChat() {
        isChatOpen = !isChatOpen;
        debugLog('Toggling chat', { isChatOpen });
        
        if (isChatOpen) {
            // Show chat container and hide toggle button
            chatContainer.style.display = 'flex';
            setTimeout(() => {
                chatContainer.classList.add('visible');
                chatToggle.style.opacity = '0';
                setTimeout(() => {
                    chatToggle.style.display = 'none';
                }, 300);
            }, 10);
            
            // Focus the input after the animation completes
            setTimeout(() => {
                userInput.focus();
            }, 350);
            
            // Restore chat history if minimized
            if (isMinimized) {
                toggleMinimize();
            }
            
            localStorage.setItem('chatState', 'open');
        } else {
            // Hide chat container and show toggle button
            chatContainer.classList.remove('visible');
            setTimeout(() => {
                chatContainer.style.display = 'none';
                chatToggle.style.display = 'flex';
                setTimeout(() => {
                    chatToggle.style.opacity = '1';
                }, 10);
            }, 300);
            
            localStorage.setItem('chatState', 'closed');
        }
    }
    
    // Toggle minimize chat
    function toggleMinimize() {
        isMinimized = !isMinimized;
        debugLog('Toggling minimize', { isMinimized });
        
        if (isMinimized) {
            // Store current scroll position
            chatMessages.dataset.scrollTop = chatMessages.scrollTop;
            
            // Hide chat content
            chatContainer.style.height = '60px';
            chatContainer.style.overflow = 'hidden';
            chatMessages.style.display = 'none';
            document.querySelector('.chat-input').style.display = 'none';
            minimizeBtn.innerHTML = '<i class="fas fa-plus"></i>';
            
            // Close keyboard on mobile
            userInput.blur();
        } else {
            // Show chat content
            chatContainer.style.height = 'calc(100vh - 40px)';
            chatContainer.style.overflow = 'hidden';
            chatMessages.style.display = 'flex';
            document.querySelector('.chat-input').style.display = 'flex';
            minimizeBtn.innerHTML = '<i class="fas fa-minus"></i>';
            
            // Restore scroll position
            setTimeout(() => {
                chatMessages.scrollTop = chatMessages.dataset.scrollTop || chatMessages.scrollHeight;
            }, 10);
        }
    }
    
    // Auto-resize textarea
    function autoResizeTextarea() {
        this.style.height = 'auto';
        this.style.height = (Math.min(this.scrollHeight, 120)) + 'px';
        
        // Adjust chat messages padding when input expands
        if (chatMessages) {
            const inputHeight = this.offsetHeight;
            chatMessages.style.paddingBottom = (80 + Math.max(0, inputHeight - 40)) + 'px';
            chatMessages.scrollTop = chatMessages.scrollHeight;
        }
    }
    
    // Send message to AI
    async function sendMessage() {
        const message = userInput.value.trim();
        if (!message) return;
        
        // Add user message to chat
        addMessage(message, 'user');
        
        // Clear input
        userInput.value = '';
        autoResizeTextarea.call(userInput);
        
        // Show typing indicator
        const typingIndicator = addTypingIndicator();
        
        try {
            // Send message to server
            const response = await fetch('/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ message })
            });
            
            // Remove typing indicator
            if (typingIndicator && typingIndicator.parentNode) {
                typingIndicator.remove();
            }
            
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            
            const data = await response.json();
            
            // Add AI response to chat
            if (data.response) {
                addMessage(data.response, 'ai');
            } else if (data.error) {
                addMessage(`Error: ${data.error}`, 'ai');
            }
            
        } catch (error) {
            console.error('Error:', error);
            if (typingIndicator && typingIndicator.parentNode) {
                typingIndicator.remove();
            }
            addMessage('Sorry, there was an error processing your request. Please try again.', 'ai');
        }
    }
    
    // Add message to chat
    function addMessage(text, sender) {
        // Remove the initial greeting if it's the first user message
        const initialGreeting = document.querySelector('.initial-greeting');
        if (initialGreeting && sender === 'user') {
            initialGreeting.remove();
        }
        
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender}-message`;
        
        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        contentDiv.textContent = text;
        
        messageDiv.appendChild(contentDiv);
        chatMessages.appendChild(messageDiv);
        
        // Scroll to bottom with smooth behavior
        setTimeout(() => {
            messageDiv.scrollIntoView({ behavior: 'smooth', block: 'end' });
        }, 10);
        
        // Save to chat history
        saveChatMessage(text, sender);
    }
    
    // Add typing indicator
    function addTypingIndicator() {
        const typingDiv = document.createElement('div');
        typingDiv.className = 'message ai-message typing-indicator';
        typingDiv.innerHTML = `
            <div class="typing">
                <span></span>
                <span></span>
                <span></span>
            </div>
        `;
        chatMessages.appendChild(typingDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
        return typingDiv;
    }
    
    // Save chat message to localStorage
    function saveChatMessage(text, sender) {
        const chatHistory = JSON.parse(localStorage.getItem('chatHistory') || '[]');
        chatHistory.push({ text, sender, timestamp: new Date().toISOString() });
        
        // Keep only the last 50 messages
        if (chatHistory.length > 50) {
            chatHistory.splice(0, chatHistory.length - 50);
        }
        
        localStorage.setItem('chatHistory', JSON.stringify(chatHistory));
    }
    
    // Load chat history from localStorage
    function loadChatHistory() {
        const chatHistory = JSON.parse(localStorage.getItem('chatHistory') || '[]');
        
        // Clear existing messages except the initial greeting
        while (chatMessages.children.length > 1) {
            chatMessages.removeChild(chatMessages.lastChild);
        }
        
        // Add messages from history
        chatHistory.forEach(msg => {
            addMessage(msg.text, msg.sender);
        });
    }
    
    // Refresh analytics data
    function refreshAnalytics() {
        // In a real app, this would fetch fresh analytics data
        analyticsContent.innerHTML = `
            <div class="analytics-placeholder">
                <i class="fas fa-chart-line"></i>
                <p>Analytics data refreshed at ${new Date().toLocaleTimeString()}</p>
                <p>This is a placeholder for your analytics dashboard.</p>
                <p>Connect to your data source to display real-time analytics here.</p>
            </div>
        `;
    }
    
    // Draggable functionality
    function startDrag(e) {
        if (e.target === minimizeBtn) return;
        isDragging = true;
        startX = e.clientX;
        startY = e.clientY;
        startLeft = chatContainer.offsetLeft;
        startTop = chatContainer.offsetTop;
        chatContainer.style.cursor = 'grabbing';
        e.preventDefault();
    }
    
    function drag(e) {
        if (!isDragging) return;
        const dx = e.clientX - startX;
        const dy = e.clientY - startY;
        chatContainer.style.left = `${startLeft + dx}px`;
        chatContainer.style.top = `${startTop + dy}px`;
    }
    
    function stopDrag() {
        isDragging = false;
        chatContainer.style.cursor = 'default';
    }
    
    // Resizable functionality
    function startResize(e) {
        isResizing = true;
        startXResize = e.clientX;
        startYResize = e.clientY;
        startWidth = parseInt(document.defaultView.getComputedStyle(chatContainer).width, 10);
        startHeight = parseInt(document.defaultView.getComputedStyle(chatContainer).height, 10);
        e.preventDefault();
    }
    
    function resize(e) {
        if (!isResizing) return;
        
        const width = startWidth + (e.clientX - startXResize);
        const height = startHeight + (e.clientY - startYResize);
        
        // Set minimum dimensions
        if (width > 300 && width < window.innerWidth * 0.9) {
            chatContainer.style.width = `${width}px`;
        }
        
        if (height > 200 && height < window.innerHeight * 0.8) {
            chatContainer.style.height = `${height}px`;
        }
    }
    
    function stopResize() {
        isResizing = false;
    }
    
    // Initialize the app
    init();
});
