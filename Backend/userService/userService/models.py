from django.db import models
from django.db.models import Q
from django.contrib.auth.models import User

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    display_name = models.CharField(max_length=100)
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    is_online = models.BooleanField(default=False)
    blocked_users = models.ManyToManyField(User, related_name='blocked_users')

    DEFAULT_AVATAR_PATH = 'default.png'

    def get_avatar_url(self):
        if self.avatar:
            return self.avatar.url
        return f"/media/{self.DEFAULT_AVATAR_PATH}"

    def get_friends(self):
        friendships = Friendship.objects.filter(
            (Q(from_profile=self) | Q(to_profile=self)) & Q(status='accepted')
        )
        friends = []
        for friendship in friendships:
            if friendship.from_profile == self:
                friends.append(friendship.to_profile)
            else:
                friends.append(friendship.from_profile)
        return friends
    
    def is_blocked(self, user):
        return self.blocked_users.filter(id=user.id).exists()

    def get_blocked_users(self):
        return self.blocked_users.all()

class Friendship(models.Model):
    from_profile = models.ForeignKey(Profile, related_name='from_friend_set', on_delete=models.CASCADE)
    to_profile = models.ForeignKey(Profile, related_name='to_friend_set', on_delete=models.CASCADE)
    status = models.CharField(max_length=10, choices=[('pending', 'Pending'), ('accepted', 'Accepted')], default='pending')
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('from_profile', 'to_profile')
