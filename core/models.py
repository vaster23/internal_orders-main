from django.contrib.auth.models import User
from django.db import models


class Company(models.Model):
    name = models.CharField(max_length=255, unique=True)
    display_name = models.CharField(max_length=255, blank=True, default='')
    support_email = models.EmailField(blank=True, default='')
    support_phone = models.CharField(max_length=50, blank=True, default='')
    primary_color = models.CharField(max_length=20, blank=True, default='#0f172a')
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Company'
        verbose_name_plural = 'Companies'

    def __str__(self):
        return self.display_name or self.name


class UserBranch(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='user_branch')
    branch = models.ForeignKey('products.Branch', on_delete=models.CASCADE)

    class Meta:
        verbose_name = 'User Branch'
        verbose_name_plural = 'User Branches'

    def __str__(self):
        return f'{self.user.username} -> {self.branch.name}'


class UserCompany(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='user_company')
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='user_companies')

    class Meta:
        verbose_name = 'User Company'
        verbose_name_plural = 'User Companies'

    def __str__(self):
        return f'{self.user.username} -> {self.company.name}'


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    must_change_password = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'User Profile'
        verbose_name_plural = 'User Profiles'

    def __str__(self):
        return f'Profile - {self.user.username}'


class AuditLog(models.Model):
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name='audit_logs',
        null=True,
        blank=True,
    )
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs',
    )
    action = models.CharField(max_length=100)
    target_type = models.CharField(max_length=100)
    target_id = models.CharField(max_length=100, blank=True, default='')
    description = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Audit Log'
        verbose_name_plural = 'Audit Logs'

    def __str__(self):
        company_name = self.company.name if self.company else 'No Company'
        username = self.user.username if self.user else 'System'
        return f'[{company_name}] {username} - {self.action}'


class Notification(models.Model):
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    title = models.CharField(max_length=255)
    message = models.TextField(blank=True, default='')
    url = models.CharField(max_length=255, blank=True, default='')
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Notification'
        verbose_name_plural = 'Notifications'

    def __str__(self):
        return f'{self.user.username} - {self.title}'