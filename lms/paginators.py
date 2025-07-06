from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class CourseLessonPaginator(PageNumberPagination):
    """
    Пагинатор для курсов и уроков
    """
    page_size = 10  # Количество элементов на странице по умолчанию
    page_size_query_param = 'page_size'  # Параметр для изменения размера страницы
    max_page_size = 50  # Максимальное количество элементов на странице

    def get_paginated_response(self, data):
        """
        Кастомный ответ с дополнительной информацией о пагинации
        """
        return Response({
            'links': {
                'next': self.get_next_link(),
                'previous': self.get_previous_link()
            },
            'pagination': {
                'count': self.page.paginator.count,
                'current_page': self.page.number,
                'total_pages': self.page.paginator.num_pages,
                'page_size': self.get_page_size(self.request),
                'has_next': self.page.has_next(),
                'has_previous': self.page.has_previous(),
            },
            'results': data
        })


class UserPaginator(PageNumberPagination):
    """
    Пагинатор для пользователей (больший размер страницы)
    """
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100

    def get_paginated_response(self, data):
        return Response({
            'links': {
                'next': self.get_next_link(),
                'previous': self.get_previous_link()
            },
            'pagination': {
                'count': self.page.paginator.count,
                'current_page': self.page.number,
                'total_pages': self.page.paginator.num_pages,
                'page_size': self.get_page_size(self.request),
            },
            'results': data
        })


class PaymentPaginator(PageNumberPagination):
    """
    Пагинатор для платежей (меньший размер страницы для детального просмотра)
    """
    page_size = 15
    page_size_query_param = 'page_size'
    max_page_size = 50