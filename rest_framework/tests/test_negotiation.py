from __future__ import unicode_literals
from django.test import TestCase
from rest_framework.negotiation import DefaultContentNegotiation, _MediaType
from rest_framework.request import Request
from rest_framework.renderers import BaseRenderer
from rest_framework.test import APIRequestFactory


factory = APIRequestFactory()


class MockJSONRenderer(BaseRenderer):
    media_type = 'application/json'

class MockXMLRenderer(BaseRenderer):
    media_type = 'application/xml'

class MockHTMLRenderer(BaseRenderer):
    media_type = 'text/html'


class NoCharsetSpecifiedRenderer(BaseRenderer):
    media_type = 'my/media'


class TestAcceptedMediaType(TestCase):
    def setUp(self):
        self.renderers = [MockJSONRenderer(), MockHTMLRenderer()]
        self.negotiator = DefaultContentNegotiation()

    def select_renderer(self, request):
        return self.negotiator.select_renderer(request, self.renderers)

    def test_client_without_accept_use_renderer(self):
        request = Request(factory.get('/'))
        accepted_renderer, accepted_media_type = self.select_renderer(request)
        self.assertEqual(accepted_media_type, 'application/json')

    def test_client_underspecifies_accept_use_renderer(self):
        request = Request(factory.get('/', HTTP_ACCEPT='*/*'))
        accepted_renderer, accepted_media_type = self.select_renderer(request)
        self.assertEqual(accepted_media_type, 'application/json')

    def test_client_overspecifies_accept_use_client(self):
        request = Request(factory.get('/', HTTP_ACCEPT='application/json; indent=8'))
        accepted_renderer, accepted_media_type = self.select_renderer(request)
        self.assertEqual(accepted_media_type, 'application/json; indent=8')


    def test_complex_accept(self):
        accepts = u'text/html, application/xhtml+xml, application/xml;q=0.9, image/webp, */*;q=0.8'
        self.renderers = [MockJSONRenderer(), MockXMLRenderer(), MockHTMLRenderer()]

        request = Request(factory.get('/', HTTP_ACCEPT=accepts))
        accepted_renderer, accepted_media_type = self.select_renderer(request)
        self.assertEqual(u'text/html', accepted_media_type)

        
    def test_media_type_match(self):
        def match(one, another):
            return _MediaType(one).match(_MediaType(another))

        self.assertEqual(True, match('text/html', 'text/html'))
        self.assertEqual(True, match('text/html', 'text/*'))
        self.assertEqual(True, match('text/html', '*/*'))

        self.assertEqual(False, match('text/html', 'text/plain'))
        self.assertEqual(False, match('text/html', 'application/json'))

        self.assertEqual(True, match('text/html', 'text/html; q=0.7'))
        self.assertEqual(True, match('text/html', 'text/html; what=42'))


    def test_media_type_sorting(self):
        def sortem(*types):
            types = [_MediaType(item) for item in types]
            types.sort(key=lambda x: x.precedence, reverse=True)
            return [item.orig for item in types]

        self.assertEqual([u'text/html', u'application/xhtml+xml', u'image/webp', u'application/xml;q=0.9', u'*/*;q=0.8'],
            sortem(u'text/html', u'application/xhtml+xml', u'application/xml;q=0.9', u'image/webp', u'*/*;q=0.8'))

        self.assertEqual([u'text/plain; width=80', u'text/html', 'text/plain'],
            sortem(u'text/html', u'text/plain', u'text/plain; width=80'))
