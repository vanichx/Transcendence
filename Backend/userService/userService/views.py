# **************************************************************************** #
#                                                                              #
#                                                         :::      ::::::::    #
#    views.py                                           :+:      :+:    :+:    #
#                                                     +:+ +:+         +:+      #
#    By: ipetruni <ipetruni@student.42.fr>          +#+  +:+       +#+         #
#                                                 +#+#+#+#+#+   +#+            #
#    Created: 2024/11/19 12:10:18 by ipetruni          #+#    #+#              #
#    Updated: 2025/01/22 18:39:26 by ipetruni         ###   ########.fr        #
#                                                                              #
# **************************************************************************** #

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from rest_framework import status, viewsets, filters
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from rest_framework.views import APIView
from rest_framework.decorators import api_view
from rest_framework import generics
from .serializers import UserSerializer, UserProfileSerializer
from .models import Profile, Friendship, ChatModel
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import permission_classes
from django.db.models import Q
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.contrib.messages.api import *  # NOQA
from django.contrib.messages.constants import *  # NOQA
from django.contrib.messages.storage.base import Message  # NOQA
from django.views.generic import DetailView 
import json
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.shortcuts import render
from django.contrib.auth import get_user_model
import logging
from django.views import View
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views import View
from django.contrib.auth.models import User
from .models import ChatModel
import json
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication

logger = logging.getLogger(__name__)

class RegisterView(generics.CreateAPIView):
    serializer_class = UserSerializer

    def post(self, request, *args, **kwargs):
        logger.debug("Received registration data: %s", request.data)
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            username = serializer.validated_data['username']
            if User.objects.filter(username=username).exists():
                return Response({"error": "Username already exists."}, status=status.HTTP_400_BAD_REQUEST)
            
            serializer.save()
            return Response({"message": "Registration successful"}, status=status.HTTP_201_CREATED)
        
        logger.debug("Registration errors: %s", serializer.errors)
        return Response({"error": "Registration failed", "details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)


class LoginView(APIView):
    def post(self, request, *args, **kwargs):
        print("Raw request data:", request.body)
        username = request.data.get("username")
        password = request.data.get("password")
        print(f"Username: {username}, Password length: {len(password) if password else 0}")

        if not username or not password:
            return Response(
                {"message": "Username and password are required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        user = authenticate(request, username=username, password=password)
        print('Request received:', request.data)
        
        if user:
            # Get or create token using correct import
            token, created = Token.objects.get_or_create(user=user)
            
            user_data = {
                'id': user.id,
                'username': user.username,
                'email': user.email,
            }
            
            return Response({
                'token': token.key,
                'user': user_data
            }, status=status.HTTP_200_OK)
        
        return Response(
            {"message": "Invalid username or password."},
            status=status.HTTP_401_UNAUTHORIZED
        )

class ProfileView(APIView):
    authentication_classes = [TokenAuthentication]  # First: Validates authToken
    permission_classes = [IsAuthenticated]         # Then: Checks if identified user has access

    def get(self, request):
        try:
            logger.debug(f"Fetching profile for user: {request.user.username}")
            
            # Use get_object_or_404 instead of direct get()
            user_profile = get_object_or_404(Profile, user=request.user)
            
            # Fetch friends
            friends = user_profile.get_friends()
            
            # Serialize data
            serializer_context = {"request": request}
            friends_data = UserProfileSerializer(friends, many=True, context=serializer_context).data
            profile_data = UserProfileSerializer(user_profile, context=serializer_context).data
            profile_data['friends'] = friends_data
            
            logger.debug(f"Successfully retrieved profile for user: {request.user.username}")
            return Response(profile_data, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error fetching profile: {str(e)}")
            return Response(
                {"error": "Failed to retrieve profile"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def delete(self, request):
        """Handle avatar deletion"""
        try:
            user_profile = request.user.profile
            
            if not user_profile.avatar:
                return Response(
                    {"message": "Already using default avatar"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )

            user_profile.avatar.delete(save=False)
            user_profile.avatar = None
            user_profile.save()
            
            logger.info(f"Reset avatar to default for user {request.user.username}")
            
            serializer = UserProfileSerializer(user_profile, context={"request": request})
            return Response(serializer.data, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Avatar deletion error: {str(e)}")
            return Response(
                {"message": "Failed to delete avatar"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def put(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return Response({"message": "You are not authenticated"}, status=status.HTTP_401_UNAUTHORIZED)

        user_profile = request.user.profile
        data = request.data

        if 'display_name' in data:
            display_name = data['display_name'].strip()

            if Profile.objects.filter(display_name=display_name).exclude(user=request.user).exists():
                return Response({"message": "Display name is already taken"}, status=status.HTTP_400_BAD_REQUEST)
            user_profile.display_name = display_name
            logger.info(f"Updated display name for user {request.user.username}")
            
        if 'avatar' in request.FILES:
                avatar = request.FILES['avatar']
                
                # Validate file type
                if not avatar.content_type.startswith('image/'):
                    return Response(
                        {"message": "Invalid file type. Please upload an image"}, 
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                # Validate file size (5MB limit)
                if avatar.size > 5 * 1024 * 1024:
                    return Response(
                        {"message": "File too large. Maximum size is 5MB"}, 
                        status=status.HTTP_400_BAD_REQUEST
                    )

                # Delete old avatar if exists
                if user_profile.avatar:
                    user_profile.avatar.delete(save=False)
                
                user_profile.avatar = avatar
                logger.info(f"Updated avatar for user {request.user.username}")

        user_profile.save()
        
        # Return updated profile data
        serializer = UserProfileSerializer(user_profile, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)

class SearchProfilesView(generics.ListAPIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = UserProfileSerializer

    def get_queryset(self):
        search_query = self.request.query_params.get('q', '').strip()
        if not search_query:
            return Profile.objects.none()
            
        current_user_profile = self.request.user.profile
        queryset = Profile.objects.filter(
            display_name__icontains=search_query
        ).exclude(
            user=self.request.user
        )
            
        return queryset

@permission_classes([IsAuthenticated])
class AddFriendView(APIView):
    def post(self, request):
        from_profile = request.user.profile
        to_profile_id = request.data.get('friend_profile_id')  # Adjust key as per frontend

        if not to_profile_id:
            return Response({'error': 'Friend profile ID is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            to_profile = Profile.objects.get(id=to_profile_id)
        except Profile.DoesNotExist:
            return Response({'error': 'Profile not found'}, status=status.HTTP_404_NOT_FOUND)

        # Check if friendship already exists or if there's a pending request
        existing_friendship = Friendship.objects.filter(
            Q(from_profile=from_profile, to_profile=to_profile) |
            Q(from_profile=to_profile, to_profile=from_profile)
        ).first()

        if existing_friendship:
            if existing_friendship.status == 'accepted':
                return Response({'message': 'You are already friends'}, status=status.HTTP_200_OK)
            elif existing_friendship.status == 'pending':
                return Response({'message': 'Friend request already sent or received'}, status=status.HTTP_200_OK)

        # Create a new friendship request
        Friendship.objects.create(from_profile=from_profile, to_profile=to_profile, status='pending')

        # Send a WebSocket notification to the recipient
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"user_{to_profile.user.id}",
            {
                'type': 'send_notification',
                'message': {
                    'type': 'friend_request',
                    'from_user_id': from_profile.user.id,
                    'from_user_name': from_profile.display_name,
                    'from_user_avatar': from_profile.avatar.url if from_profile.avatar else '',
                },
            }
        )

        return Response({'message': 'Friend request sent successfully'}, status=status.HTTP_201_CREATED)

@permission_classes([IsAuthenticated])
class IncomingFriendRequestsView(APIView):
    def get(self, request, *args, **kwargs):
        user_profile = request.user.profile
        incoming_requests = Friendship.objects.filter(to_profile=user_profile, status='pending')
        serializer = UserProfileSerializer([req.from_profile for req in incoming_requests], many=True, context={"request": request})
        return Response(serializer.data)

@permission_classes([IsAuthenticated])
class DeclineFriendRequestView(APIView):
    def post(self, request, *args, **kwargs):
        user_profile = request.user.profile
        friend_profile_id = request.data.get('friend_profile_id')

        try:
            friend_profile = Profile.objects.get(id=friend_profile_id)
            friendship = Friendship.objects.get(from_profile=friend_profile, to_profile=user_profile, status='pending')
            friendship.delete()

            # Send a WebSocket notification to the sender
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f"user_{friend_profile.user.id}",
                {
                    'type': 'send_notification',
                    'message': {
                        'type': 'friend_request_declined',
                        'user_id': user_profile.user.id,
                        'user_name': user_profile.display_name,
                        'user_avatar': user_profile.avatar.url if user_profile.avatar else '',
                    },
                }
            )

            return Response({"message": "Friend request declined"}, status=status.HTTP_200_OK)
        except (Profile.DoesNotExist, Friendship.DoesNotExist):
            return Response({"message": "Friend request not found"}, status=status.HTTP_404_NOT_FOUND)
        
@permission_classes([IsAuthenticated])
class AcceptFriendRequestView(APIView):
    def post(self, request):
        to_profile = request.user.profile
        from_user_id = request.data.get('from_user_id')

        if not from_user_id:
            return Response({'error': 'From user ID is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            from_profile = Profile.objects.get(user__id=from_user_id)
        except Profile.DoesNotExist:
            return Response({'error': 'Profile not found'}, status=status.HTTP_404_NOT_FOUND)

        friendship = Friendship.objects.filter(from_profile=from_profile, to_profile=to_profile, status='pending').first()

        if not friendship:
            return Response({'error': 'Friend request not found'}, status=status.HTTP_400_BAD_REQUEST)

        friendship.status = 'accepted'
        friendship.save()

        # Send a WebSocket notification to the requester
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"user_{from_profile.user.id}",
            {
                'type': 'send_notification',
                'message': {
                    'type': 'friend_request_accepted',
                    'user_id': to_profile.user.id,
                    'user_name': to_profile.display_name,
                    'user_avatar': to_profile.avatar.url if to_profile.avatar else '',
                },
            }
        )

        return Response({'message': 'Friend request accepted'}, status=status.HTTP_200_OK)

@permission_classes([IsAuthenticated])
class RemoveFriendView(APIView):
    def post(self, request, *args, **kwargs):
        user_profile = request.user.profile
        friend_profile_id = request.data.get('friend_profile_id')

        try:
            friend_profile = Profile.objects.get(id=friend_profile_id)
            friendship = Friendship.objects.filter(
                (Q(from_profile=user_profile, to_profile=friend_profile) |
                 Q(from_profile=friend_profile, to_profile=user_profile)),
                status='accepted'
            ).first()

            if not friendship:
                return Response({"message": "Friendship not found"}, status=status.HTTP_404_NOT_FOUND)

            friendship.delete()

            # Send a WebSocket notification to the friend
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f"user_{friend_profile.user.id}",
                {
                    'type': 'send_notification',
                    'message': {
                        'type': 'friend_removed',
                        'user_id': user_profile.user.id,
                        'user_name': user_profile.display_name,
                        'user_avatar': user_profile.avatar.url if user_profile.avatar else '',
                    },
                }
            )

            return Response({"message": "Friend removed successfully"}, status=status.HTTP_200_OK)
        except Profile.DoesNotExist:
            return Response({"message": "Profile not found"}, status=status.HTTP_404_NOT_FOUND)

class LogoutView(APIView):
    def post(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            user_profile = request.user.profile
            user_profile.is_online = False
            user_profile.save()

            # Notify friends that the user is offline
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f"user_{user_profile.user.id}",
                {
                    'type': 'send_notification',
                    'message': {
                        'type': 'friend_status',
                        'user_id': user_profile.user.id,
                        'status': 'offline',
                    },
                }
            )

            logout(request)
            return Response({"message": "Logout successful"}, status=status.HTTP_200_OK)
            return Response({"message": "Logout not successful"}, status=status.HTTP_200_OK)

class ChatView(View):
    def get(self, request, *args, **kwargs):
        user = request.user
        receiver = get_object_or_404(User, id=self.kwargs['id'])
        
        # Формируем thread_name
        if user.id < receiver.id:
            thread_name = f'chat_{user.id}-{receiver.id}'
        else:
            thread_name = f'chat_{receiver.id}-{user.id}'
        
        # Получаем сообщения из модели
        messages = ChatModel.objects.filter(thread_name=thread_name)
        
        # Исключаем текущего пользователя из списка пользователей
        users = User.objects.exclude(id=user.id)
        
        # Формируем данные для ответа
        data = {
            'users': list(users.values('id', 'username')),
            'user': user.username,
            'messages': list(messages.values('sender', 'message', 'timestamp')),
            'thread_name': thread_name,
            'user_json': json.dumps(user.id),
            'receiver_json': json.dumps(receiver.id),
            'username_json': json.dumps(user.username),
            'receiver_username_json': json.dumps(receiver.username)
        }
        return JsonResponse(data)
