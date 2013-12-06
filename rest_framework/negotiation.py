# coding: utf-8

"""
Content negotiation deals with selecting an appropriate renderer given the
incoming request.  Typically this will be based on the request's Accept header.
"""
from __future__ import unicode_literals
from django.http import Http404
from rest_framework import exceptions
from rest_framework.settings import api_settings
from rest_framework.utils.mediatypes import order_by_precedence, media_type_matches
from rest_framework.utils.mediatypes import _MediaType


class BaseContentNegotiation(object):
    def select_parser(self, request, parsers):
        raise NotImplementedError('.select_parser() must be implemented')

    def select_renderer(self, request, renderers, format_suffix=None):
        raise NotImplementedError('.select_renderer() must be implemented')


class DefaultContentNegotiation(BaseContentNegotiation):
    settings = api_settings

    def select_parser(self, request, parsers):
        """
        Given a list of parsers and a media type, return the appropriate
        parser to handle the incoming request.
        """
        for parser in parsers:
            if media_type_matches(parser.media_type, request.content_type):
                return parser
        return None

    def select_renderer(self, request, renderers, format_suffix=None):
        """
        Given a request and a list of renderers, return a two-tuple of:
        (renderer, media type).

        This content negotiation algorithms acts as decribed in
        http://www.w3.org/Protocols/rfc2616/rfc2616-sec14.html#14.1
        """
        # Allow URL style format override.  eg. "?format=json
        format_query_param = self.settings.URL_FORMAT_OVERRIDE
        format = format_suffix or request.QUERY_PARAMS.get(format_query_param)

        if format:
            renderers = self.filter_renderers(renderers, format)

        accepts = self.get_accept_list(request)
        accepts = [_MediaType(item) for item in accepts]
        # now sort them in decreasing precedence order
        accepts.sort(key=lambda item: item.precedence, reverse=True)

        # find the best match for each renderer
        # matches will contain a tuples (Found MediaType, renderer)
        matches = []
        for renderer in renderers:
            renderer_media_type = _MediaType(renderer.media_type)
            for media_type in accepts:
                if renderer_media_type.match(media_type):
                    matches.append((media_type, renderer))
                    break

        if matches:
            # now choose better renderer by precedence
            matches.sort(key=lambda item: item[0].precedence, reverse=True)
            media_type, renderer = matches[0]

            if (_MediaType(renderer.media_type).precedence > media_type.precedence):
                # Eg client requests '*/*'
                # Accepted media type is 'application/json'
                return renderer, renderer.media_type
            else:
                # Eg client requests 'application/json; indent=8'
                # Accepted media type is 'application/json; indent=8'
                return renderer, media_type.orig

        raise exceptions.NotAcceptable(available_renderers=renderers)


    def filter_renderers(self, renderers, format):
        """
        If there is a '.json' style format suffix, filter the renderers
        so that we only negotiation against those that accept that format.
        """
        renderers = [renderer for renderer in renderers
                     if renderer.format == format]
        if not renderers:
            raise Http404
        return renderers

    def get_accept_list(self, request):
        """
        Given the incoming request, return a tokenised list of media
        type strings.

        Allows URL style accept override.  eg. "?accept=application/json"
        """
        header = request.META.get('HTTP_ACCEPT', '*/*')
        header = request.QUERY_PARAMS.get(self.settings.URL_ACCEPT_OVERRIDE, header)
        return [token.strip() for token in header.split(',')]
