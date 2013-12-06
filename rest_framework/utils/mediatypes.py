"""
Handling of media types, as found in HTTP Content-Type and Accept headers.

See http://www.w3.org/Protocols/rfc2616/rfc2616-sec3.html#sec3.7
"""
from __future__ import unicode_literals
from django.http.multipartparser import parse_header
from rest_framework import HTTP_HEADER_ENCODING


def media_type_matches(lhs, rhs):
    """
    Returns ``True`` if the media type in the first argument <= the
    media type in the second argument.  The media types are strings
    as described by the HTTP spec.

    Valid media type strings include:

    'application/json; indent=4'
    'application/json'
    'text/*'
    '*/*'
    """
    lhs = _MediaType(lhs)
    rhs = _MediaType(rhs)
    return lhs.match(rhs)


_NOT_GIVEN = object()


class _MediaType(object):
    def __init__(self, media_type_str):
        if media_type_str is None:
            media_type_str = ''
        self.orig = media_type_str
        self.full_type, self.params = parse_header(media_type_str.encode(HTTP_HEADER_ENCODING))
        
        self.quality = self.params.pop('q', _NOT_GIVEN)
        self.quality_not_given = self.quality is _NOT_GIVEN
        if self.quality_not_given:
            self.quality = 1.0
        else:
            self.quality = float(self.quality)

        self.main_type, sep, self.sub_type = self.full_type.partition('/')

    def match(self, other):
        """Return true if this MediaType satisfies the given MediaType.
        Note, this method is not transient:
        
        _MediaType('application/json').match(_MediaType('application/json; indent=4')) -> True

        but
        
        _MediaType('application/json; indent=4').match(_MediaType('application/json')) -> False
        """
        for key in self.params.keys():
            if other.params.get(key, None) != self.params[key]:
                return False

        if self.sub_type != '*' and other.sub_type != '*'  and other.sub_type != self.sub_type:
            return False

        if self.main_type != '*' and other.main_type != '*' and other.main_type != self.main_type:
            return False

        return True

    @property
    def precedence(self):
        """
        Return a precedence level from 0-3 for the media type given how specific it is.
        """
        return (
            self.main_type != '*',
            self.sub_type != '*',
            len(self.params) > 0,
            self.quality)

    def __str__(self):
        return unicode(self).encode('utf-8')

    def __unicode__(self):
        ret = [u'%s/%s' % (self.main_type, self.sub_type)]
        if not self.quality_not_given:
            ret.append(u'q=%s' % self.quality)
        for item in self.params.items():
            ret.append(u'%s=%s' % item)
        return u'; '.join(ret)

    def __repr__(self):
        return "%s('%s')" % (self.__class__.__name__, self.orig)

