from django.db import models


class Unit(models.Model):
    company = models.ForeignKey(
        'core.Company',
        on_delete=models.CASCADE,
        related_name='units',
        null=True,
        blank=True,
    )
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']
        unique_together = ('company', 'code')

    def __str__(self):
        if self.company:
            return f'{self.company.name} - {self.name} ({self.code})'
        return f'{self.name} ({self.code})'


class Category(models.Model):
    company = models.ForeignKey(
        'core.Company',
        on_delete=models.CASCADE,
        related_name='categories',
        null=True,
        blank=True,
    )
    name = models.CharField(max_length=100)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']
        verbose_name_plural = 'Categories'
        unique_together = ('company', 'name')

    def __str__(self):
        if self.company:
            return f'{self.company.name} - {self.name}'
        return self.name


class Branch(models.Model):
    company = models.ForeignKey(
        'core.Company',
        on_delete=models.CASCADE,
        related_name='branches',
        null=True,
        blank=True,
    )
    name = models.CharField(max_length=150)
    address = models.CharField(max_length=255, blank=True, default='')
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']
        unique_together = ('company', 'name')

    def __str__(self):
        if self.company:
            return f'{self.company.name} - {self.name}'
        return self.name


class Product(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, default='')
    unit = models.ForeignKey(Unit, on_delete=models.PROTECT, related_name='products')
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name='products')
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name='products')
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name