from rest_framework import permissions


class IsModeratorOrOwner(permissions.BasePermission):
    """
    Кастомное разрешение для курсов и уроков:
    - Модераторы могут просматривать и редактировать все объекты
    - Обычные пользователи могут работать только со своими объектами
    - Создание и удаление разрешено только владельцам (модераторы не могут создавать/удалять)
    """

    def has_permission(self, request, view):
        # Только аутентифицированные пользователи
        if not request.user.is_authenticated:
            return False

        # Для создания объектов - только не модераторы (владельцы)
        if view.action == 'create':
            return not request.user.groups.filter(name='Moderators').exists()

        return True

    def has_object_permission(self, request, view, obj):
        # Суперпользователь может все
        if request.user.is_superuser:
            return True

        # Проверяем, является ли пользователь модератором
        is_moderator = request.user.groups.filter(name='Moderators').exists()

        # Модераторы могут просматривать и редактировать, но не удалять
        if is_moderator:
            if view.action == 'destroy':
                return False
            return view.action in ['retrieve', 'update', 'partial_update', 'list']

        # Обычные пользователи могут работать только со своими объектами
        # Проверяем владельца объекта
        if hasattr(obj, 'owner'):
            return obj.owner == request.user
        elif hasattr(obj, 'user'):
            return obj.user == request.user

        return False


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Разрешение для профилей пользователей:
    - Любой аутентифицированный пользователь может просматривать профили
    - Редактировать можно только свой профиль
    """

    def has_permission(self, request, view):
        return request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        # Суперпользователь может все
        if request.user.is_superuser:
            return True

        # Чтение доступно всем аутентифицированным пользователям
        if request.method in permissions.SAFE_METHODS:
            return True

        # Редактирование только своего профиля
        return obj == request.user


class IsModeratorReadOnly(permissions.BasePermission):
    """
    Разрешение только для чтения для модераторов
    """

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False

        is_moderator = request.user.groups.filter(name='Moderators').exists()

        if is_moderator:
            return request.method in permissions.SAFE_METHODS

        return True