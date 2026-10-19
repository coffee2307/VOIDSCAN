import unittest
from email.message import Message
from unittest.mock import patch
from urllib.error import HTTPError
import share_resolver

URL="https://www.facebook.com/share/1JRVuBz4pg/"
TARGET="https://www.facebook.com/photo/?fbid=123456789012345"

class FakeOpener:
    def __init__(self,location):
        self.location=location
        self.calls=0
    def open(self,req,timeout):
        self.calls+=1
        headers=Message()
        headers["Location"]=self.location
        raise HTTPError(req.full_url,302,"Found",headers,None)

class ShareResolverTests(unittest.TestCase):
    def test_permitted_facebook_redirect(self):
        opener=FakeOpener(TARGET)
        with patch("share_resolver.build_opener",return_value=opener):
            response=share_resolver.resolve_shortlink(URL)
        self.assertEqual(response["status"],"resolved")
        self.assertEqual(response["url"],TARGET)
        self.assertEqual(opener.calls,1)
    def test_rejects_external_redirect(self):
        with patch("share_resolver.build_opener",
                   return_value=FakeOpener("https://evil.invalid/photo/?fbid=123")):
            response=share_resolver.resolve_shortlink(URL)
        self.assertEqual(response["status"],"unresolved")
        self.assertIsNone(response["url"])
    def test_non_facebook_urls_are_rejected(self):
        with self.assertRaises(ValueError):
            share_resolver.resolve_shortlink("https://evil.invalid/share/abc")
    def test_original_long_url_is_untouched(self):
        response=share_resolver.resolve_shortlink(TARGET)
        self.assertEqual(response["status"],"already_canonical")
        self.assertEqual(response["url"],TARGET)

if __name__=="__main__":
    unittest.main()
