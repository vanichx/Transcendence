<template>
  <div class="friends-container">
    <!-- Friends Section with Chat -->
    <div class="profile-section">
      <h2>Friends</h2>
      <div v-if="profile.friends && profile.friends.length > 0">
        <div v-for="friend in profile.friends" :key="friend.id" class="profile-item" @click="showFriendInfo(friend)">
          <img :src="friend.avatar" :alt="friend.display_name" class="profile-avatar">
          <span class="profile-name">{{ friend.display_name }}</span>
          <span :class="['status', friend.is_online ? 'online' : 'offline']">
            {{ friend.is_online ? 'Online' : 'Offline' }}
          </span>
          <div class="friend-actions">
            <button @click.stop="showFriendInfo(friend)" class="btn primary-btn">Info</button>
            <button @click="removeFriend(friend.id)" class="btn secondary-btn">Remove</button>
          </div>
        </div>
      </div>
      <p v-else>No friends yet</p>
    </div>

    <!-- Replace the existing friend-profile-modal div with this -->
    <transition name="fade">
      <div v-if="showFriendProfile && selectedFriend" class="overlay">
        <div class="friend-profile-modal">
          <div class="friend-profile-header">
            <h4 class="profile-title">Profile: {{ selectedFriend.display_name }}</h4>
            <button @click="showFriendProfile = false" class="btn secondary-btn">Close</button>
          </div>

          <div class="profile-details">
            <div class="detail-group">
              <h5>Display Name</h5>
              <p>{{ selectedFriend.display_name }}</p>
            </div>
            
            <div class="detail-group" v-if="selectedFriend.bio">
              <h5>Bio</h5>
              <p>{{ selectedFriend.bio }}</p>
            </div>
            
            <div class="detail-group" v-if="selectedFriend.location">
              <h5>Location</h5>
              <p>{{ selectedFriend.location }}</p>
            </div>
            
            <div class="detail-group">
              <h5>Member Since</h5>
              <p>{{ formatDate(selectedFriend.date_joined) }}</p>
            </div>
          </div>

          <div class="friend-profile-footer">
            <button @click="startChat(selectedFriend)" class="btn primary-btn">Start Chat</button>
          </div>
        </div>
      </div>
    </transition>

    <!-- Chat Section -->
    <transition name="fade">
      <div v-if="showChat" class="overlay">
        <div class="chat-container">
          <div class="chat-header">
            <h4 class="chat-title">Chat with {{ activeChat }}</h4>
            <button @click="closeChat" class="btn secondary-btn">Close</button>
          </div>
          <div class="chat-messages" ref="chatMessages">
            <div v-for="message in messages" 
              :key="message.id" 
              :class="['message', { 
                'message-sent': parseInt(message.sender_id) === parseInt(currentUserId),
                'message-received': parseInt(message.sender_id) !== parseInt(currentUserId)
              }]">
              <div class="message-content" :class="{ 
                  'content-sent': parseInt(message.sender_id) === currentUserId,
                  'content-received': parseInt(message.sender_id) !== currentUserId
                }">
                <div class="message-header">
                  <small class="message-sender">
                    {{ parseInt(message.sender_id) === currentUserId ? '' : activeChat }} <!-- Hide sender name for own messages -->
                  </small>
                </div>
                <span class="message-text">{{ message.text }}</span>
                <div class="message-footer">
                  <small class="message-time">{{ formatDate(message.created_at) }}</small>
                </div>
              </div>
            </div>
          </div>
          

          <div class="chat-input">
            <input 
              v-model="newMessage" 
              @keyup.enter="sendMessage" 
              placeholder="Type your message..."
              class="input-field"
            />
            <button @click="sendMessage" class="btn primary-btn">Send</button>
          </div>
        </div>
      </div>
    </transition>
  </div>
</template>

<script>
import { mapGetters } from 'vuex';
import { SERVICE_URLS } from '@/config/services';

export default {
  name: 'Friends',
  
  data() {
    return {
      profile: {
        friends: []
      },
      showChat: false,
      activeChat: null,
      chatId: null,
      chatSocket: null,
      currentUserId: null,
      messages: [],
      newMessage: '',
      notificationSocket: null,
      wsConnected: false,

      //Friends Profile View
      selectedFriend: null,
      showFriendProfile: false
    };
  },

  computed: {
    ...mapGetters(['getToken', 'isAuthenticated', 'currentUserId']),
  },

  async created() {
    try {
      if (this.isInitialized) return;
      
      const authInitialized = await this.$store.dispatch('initializeAuth');
      
      if (!authInitialized || !this.getToken) {
        this.$router.push('/login');
        return;
      }
      
      this.isInitialized = true;
      await this.fetchProfile();
      this.initNotificationSocket();
    } catch (error) {
      console.error('Initialization error:', error);
      this.$router.push('/login');
    }
  },

  methods: {
    
  async fetchProfile() {
    try {
      const response = await fetch('http://localhost:8000/api/profile/', {
        headers: {
          'Authorization': `Token ${this.getToken}`,
          'Content-Type': 'application/json'
        },
      });
      
      if (!response.ok) {
        console.error('Profile fetch failed:', response.status);
        throw new Error(`Failed to fetch profile: ${response.status}`);
      }
      
      this.profile = await response.json();
      this.currentUserId = this.profile.id; // Set currentUserId here
    } catch (error) {
      console.error('Profile fetch error:', error);
      this.$router.push('/login'); // Redirect on error
    }
  },

  async startChat(friend) {
    try {
      this.activeChat = friend.display_name;
      this.showFriendProfile = false;
      this.showChat = true;
      
      const chatId = [this.currentUserId.toString(), friend.id.toString()]
      .sort()
      .join('_');
      
      const response = await fetch(`${SERVICE_URLS.CHAT_SERVICE}/api/chats/${chatId}/`, {
        method: 'GET',
        headers: {
          'Authorization': `Token ${this.getToken}`,
          'Content-Type': 'application/json'
        }
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        console.error('Chat service error:', errorData);
        throw new Error(`Chat service error: ${response.status}`);
      }
      
      const data = await response.json();
      console.log('Messages data:', {
        currentUserId: this.currentUserId,
        friendId: friend.id,
        messages: data.messages
      });
      
      this.messages = data.messages.map(msg => ({
        id: msg.id,
        chat: msg.chat,
        sender_id: msg.sender_id,
        text: msg.text,
        created_at: msg.created_at
      }));
      
      this.chatId = chatId;
      // Setup WebSocket connection with token
      if (this.chatSocket) {
        this.chatSocket.close();
      }
      
      const wsScheme = window.location.protocol === 'https:' ? 'wss' : 'ws';
      const wsUrl = `${wsScheme}://${window.location.host}/chat/ws/chat/${this.chatId}/?token=${this.getToken}`;
      this.chatSocket = new WebSocket(wsUrl);
      
      // Handle incoming messages with correct structure
      this.chatSocket.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.type === 'chat.message') {
          const newMessage = {
            id: data.message.id,
            chat: data.message.chat,
            sender_id: data.message.sender_id || data.message.sender,
            text: data.message.text,
            created_at: data.message.created_at || new Date().toISOString()
          };
          
          console.log('Message alignment check:', {
            newMessage,
            senderId: newMessage.sender_id,
            currentUserId: this.currentUserId,
            isOwn: parseInt(newMessage.sender_id) === parseInt(this.currentUserId)
          });
          
          this.messages.push(newMessage);
          this.$nextTick(() => {
            this.scrollToBottom();
          });
        }
      };
      
      this.chatSocket.onerror = (error) => {
        console.error('WebSocket error:', error);
      };
    } catch (error) {
      console.error('Error starting chat:', error);
      
      this.showChat = false;
      this.activeChat = null;
    }
  },
      
  showFriendInfo(friend) {
    this.selectedFriend = friend;
    this.showFriendProfile = true;
    this.showChat = false;
  },

  closeChat() {
    if (this.chatSocket) {
      this.chatSocket.close();
      this.chatSocket = null;
      //Console log to check if chatSocket is closed
      console.log('Chat socket closed');
    }

  
    this.showChat = false;
    this.activeChat = null;
    this.chatId = null;
    this.messages = [];
    this.newMessage = '';
  },

  async sendMessage() {
    if (!this.newMessage.trim() || !this.chatSocket) return;
    
    if (this.chatSocket.readyState !== WebSocket.OPEN) {
      console.error('WebSocket is not connected');
      return;
    }

    try {
      const messageData = {
        type: 'chat_message',
        message: {
          chat: this.chatId,
          text: this.newMessage,
          sender_id: this.currentUserId  // Change 'sender' to 'sender_id'
        }
      };

      console.log('Sending message data:', {
        messageContent: messageData,
        socketState: this.chatSocket.readyState,
        currentUserId: this.currentUserId,
        chatId: this.chatId,
        timestamp: new Date().toISOString()
      });

      this.chatSocket.send(JSON.stringify(messageData));
      this.scrollToBottom();
      this.newMessage = '';
    } catch (error) {
      console.error('Error sending message:', error);
    }
  },

  formatDate(timestamp) {
    if (!timestamp) return '';
    const date = new Date(timestamp);
    const options = { 
      year: 'numeric', 
      month: 'long', 
      day: 'numeric',
      hour: '2-digit', 
      minute: '2-digit'
    };
    return new Date(timestamp).toLocaleDateString(undefined, options);
  },
  
  scrollToBottom() {
    this.$nextTick(() => {
      const chatMessages = this.$refs.chatMessages;
      if (chatMessages) {
        chatMessages.scrollTop = chatMessages.scrollHeight;
      }
    });
  },

  async removeFriend(friendId) {
    try {
      const friend = this.profile.friends.find(f => f.id === friendId);
      const response = await fetch('/api/profile/remove_friend/', {
        method: 'POST',
        headers: {
          'Authorization': `Token ${this.getToken}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ friend_profile_id: friendId }),
      });
        
      if (response.ok) {
        this.showStatus('Friend {name} removed successfully', { name: friend.display_name }, 'success');
        
        await this.fetchProfile(); // Refresh sender's profile
      } else {
        console.error('Failed to remove friend');
      }
    } catch (error) {
      console.error('Error removing friend:', error);
    }
  },

	initNotificationSocket() {
      //Get token from store
      const token = this.getToken;
      const wsScheme = window.location.protocol === 'https:' ? 'wss' : 'ws';
      const wsUrl = `${wsScheme}://${window.location.host}/ws/profile/notifications/?token=${this.$store.state.token}`;
      this.notificationSocket = new WebSocket(wsUrl);
      this.notificationSocket.onopen = () => {
        this.wsConnected = true;
      };
      this.notificationSocket.onmessage = (e) => {
        console.log('WebSocket message received:', e.data);  // Debug logging
        const data = JSON.parse(e.data);
        // Handle incoming messages
        switch (data.type) {
          case 'friend_request':
            this.incomingFriendRequests.push({
                id: Date.now(), // Generate temporary ID
                from_user: {
                    id: data.from_user_id,
                    display_name: data.from_user_name,
                    avatar: this.buildAvatarUrl(data.from_user_avatar, 'http://localhost:8000'),
                    is_online: true // Assume online since they just sent request
                }
            });
            this.showStatus(`New friend request from ${data.from_user_name}`, {}, 'success');
            break;

            case 'friend_status':
              const friendId = data.user_id;
              const status = data.status;
              // First try to find friend in the profile.friends array
              const friend = this.profile.friends.find(f => 
                  f.user_id === friendId || // Check user_id
                  f.id === friendId || // Check profile id
                  (f.user && f.user.id === friendId) // Check nested user object
              );
              
              if (friend) {
                  friend.is_online = (status === 'online');
                  console.log(`Updated status for friend ${friend.display_name} to ${status}`);
              } else {
                  console.log('Friend status update failed:', {
                      receivedId: friendId,
                      status: status,
                      friendsList: this.profile.friends
                  });
              }
              break;

          case 'friend_request_accepted':
            this.fetchProfile();
            break;

          case 'friend_request_declined':
            this.fetchProfile();
            break;

          case 'friend_removed':
            this.fetchProfile(); // Refresh receiver's profile
            break;

          default:
            console.warn('Unhandled WebSocket message type:', data.type);
            break;
        }
      };
      this.notificationSocket.onclose = () => {
        this.wsConnected = false;
      };
    },

  },

  messages: {
    handler() {
      this.scrollToBottom();
    },
    deep: true
  },

  beforeDestroy() {
    if (this.notificationSocket) {
      this.notificationSocket.close();
    }
    if (this.chatSocket) {
      this.chatSocket.close();
    }
  }
};
</script>

<style scoped>
.friends-container {
  padding: 20px;
  max-width: 800px;
  margin: 0 auto;
}

.profile-section {
  margin-bottom: 20px;
}

.profile-item {
  display: flex;
  align-items: center;
  margin-bottom: 1%;
  padding: 10px;
  border-radius: 8px;
  background: #1a1a1a;
}

.profile-avatar {
  width: 50px;
  height: 50px;
  border-radius: 50%;
  margin-right: 5%;
}

.profile-name {
  font-size: 16px;
  flex-grow: 1;
  color: #ffffff;
}

.status {
  padding: 0 15px;
}

.status.online {
  color: #03a670;
}

.status.offline {
  color: #a60303;
}

.friend-actions {
  display: flex;
  gap: 10px;
}

.btn {
  padding: 0.75rem 1.5rem;
  border-radius: 4px;
  border: none;
  font-weight: 500;
  cursor: pointer;
  transition: background-color 0.2s;
}

.primary-btn {
  background: #03a670;
  color: white;
}

.secondary-btn {
  background: #333333;
  color: #ffffff;
}

.secondary-btn:hover {
  background: #a60303;
}

.chat-container {
  height: 500px;
  display: flex;
  flex-direction: column;
  border-radius: 10px;
  box-shadow: 2px 2px 30px #03a670;
  margin-top: 20px;
}

.chat-header {
  padding: 1rem;
  background: #2d2d2d;
  display: flex;
  justify-content: space-between;
  align-items: center;
  color: #ffffff;
  border-radius: 10px 10px 0 0;
}

.chat-messages {
  flex-grow: 1;
  overflow: auto;
  padding: 1rem;
  display: flex;
  flex-direction: column;
  gap: 1rem;
  background: #1a1a1a;
}

.message {
  display: flex;
  max-width: 70%;
  margin-bottom: 1rem;
}

.message-sent {
  margin-left: auto;
}

.message-received {
  margin-right: auto;
}

.message-content {
  padding: 1rem;
  border-radius: 1rem;
  position: relative;
}

.content-sent {
  background: #03a670;
  color: #ffffff;
  border-radius: 1rem 1rem 0 1rem;
}

.content-received {
  background: #333333;
  color: #ffffff;
  border-radius: 1rem 1rem 1rem 0;
}

.message-time {
  font-size: 0.7rem;
  color: rgba(255, 255, 255, 0.7);
  margin-top: 0.5rem;
}

.chat-input {
  padding: 1rem;
  background: #2d2d2d;
  border-top: 1px solid #404040;
  display: flex;
  gap: 0.5rem;
}

.input-field {
  flex-grow: 1;
  border: 1px solid #404040;
  padding: 0.75rem 1rem;
  border-radius: 4px;
  background: #1a1a1a;
  color: #ffffff;
}

.input-field::placeholder {
  color: #808080;
}

.overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-color: rgba(0, 0, 0, 0.75);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
}

.friend-profile-modal {
  width: 90%;
  max-width: 500px;
  background: #1a1a1a;
  border-radius: 10px;
  box-shadow: 0 4px 20px rgba(3, 166, 112, 0.4);
  z-index: 1001;
  display: flex;
  flex-direction: column;
  max-height: 80vh;
}

.friend-profile-header {
  padding: 1rem;
  background: #2d2d2d;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-radius: 10px 10px 0 0;
}

.profile-details {
  flex: 1;
  padding: 1.5rem;
  overflow-y: auto;
}

.detail-group {
  margin-bottom: 1.5rem;
  padding-bottom: 1.5rem;
  border-bottom: 1px solid #404040;
}

.detail-group:last-child {
  margin-bottom: 0;
  padding-bottom: 0;
  border-bottom: none;
}

.detail-group h5 {
  color: #03a670;
  margin: 0 0 0.5rem 0;
  font-size: 1rem;
}

.detail-group p {
  margin: 0;
  color: #ffffff;
  line-height: 1.4;
}

.friend-profile-footer {
  padding: 1rem;
  background: #2d2d2d;
  border-top: 1px solid #404040;
  border-radius: 0 0 10px 10px;
  display: flex;
  justify-content: center;
}

/* Add transition styles */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>