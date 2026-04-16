from django.contrib import admin

from .models import AuditLog, Company, Notification, UserBranch, UserCompany, UserProfile


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'display_name',
        'support_email',
        'support_phone',
        'primary_color',
        'active',
        'created_at',
    )
    search_fields = ('name', 'display_name', 'support_email', 'support_phone')
    list_filter = ('active',)


@admin.register(UserBranch)
class UserBranchAdmin(admin.ModelAdmin):
    list_display = ('user', 'branch')
    search_fields = ('user__username', 'branch__name')


@admin.register(UserCompany)
class UserCompanyAdmin(admin.ModelAdmin):
    list_display = ('user', 'company')
    search_fields = ('user__username', 'company__name')
    list_filter = ('company',)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'must_change_password', 'created_at')
    search_fields = ('user__username',)
    list_filter = ('must_change_password',)


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'company', 'user', 'action', 'target_type', 'target_id')
    search_fields = ('action', 'target_type', 'target_id', 'description', 'user__username', 'company__name')
    list_filter = ('company', 'action', 'target_type', 'created_at')


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'company', 'user', 'title', 'is_read')
    search_fields = ('title', 'message', 'user__username', 'company__name')
    list_filter = ('company', 'is_read', 'created_at')