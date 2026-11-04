from django.http import HttpResponseNotFound


class PrivateRecipientResponses:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith(('/admin/', '/api-auth/')):
            return HttpResponseNotFound()
        response = self.get_response(request)
        if request.path.startswith(('/view/', '/api/v1/links/', '/api/v1/dealroom/recipient/', '/api/v1/page-views/', '/api/v1/link-clicks/', '/api/v1/view-sessions/')):
            response['Cache-Control'] = 'private, no-store'
            response['Referrer-Policy'] = 'no-referrer'
            response['Vary'] = 'Cookie, Authorization'
            for key in ('ETag', 'Last-Modified'):
                if key in response:
                    del response[key]
        return response
