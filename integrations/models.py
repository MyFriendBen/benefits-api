from screener.models import WhiteLabel
from django.db import models
import hashlib
import requests
import random


class LinkManager(models.Manager):
    def create(self, *args, **kwargs):
        instance = super().create(*args, **kwargs)
        instance.fill_hash()
        instance.save()

        return instance


class Link(models.Model):
    white_label = models.ForeignKey(WhiteLabel, related_name="links", null=False, blank=False, on_delete=models.CASCADE)
    link = models.URLField(max_length=2_048, unique=True)
    in_use = models.BooleanField(default=False)
    validated = models.BooleanField(default=False)
    status_code = models.IntegerField(blank=True, null=True)
    valid_status_code = models.BooleanField(default=False)
    hash = models.CharField(max_length=2_048, blank=True, null=True)

    objects = LinkManager()

    def __str__(self) -> str:
        return self.link

    @staticmethod
    def hash_data(data: str) -> str:
        return hashlib.sha224(data.encode()).hexdigest()

    @staticmethod
    def good_status_code(code: int) -> bool:
        return 200 >= code < 300

    def _get_request(self) -> requests.Response:
        user_agents = [
            "Mozilla/5.0 (Windows; U; Windows NT 5.1; it; rv:1.8.1.11) Gecko/20071127 Firefox/2.0.0.11",
            "Opera/9.25 (Windows NT 5.1; U; en)",
            "Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1; SV1; .NET CLR 1.1.4322; .NET CLR 2.0.50727)",
            "Mozilla/5.0 (compatible; Konqueror/3.5; Linux) KHTML/3.5.5 (like Gecko) (Kubuntu)",
            "Mozilla/5.0 (Windows NT 5.1) AppleWebKit/535.19 (KHTML, like Gecko) Chrome/18.0.1025.142 Safari/535.19",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.7; rv:11.0) Gecko/20100101 Firefox/11.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.6; rv:8.0.1) Gecko/20100101 Firefox/8.0.1",
            "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/535.19 (KHTML, like Gecko) Chrome/18.0.1025.151 Safari/535.19",
        ]
        rand_agent_index = random.randint(0, len(user_agents) - 1)
        header = {"User-agent": user_agents[rand_agent_index]}
        req = requests.get(self.link, headers=header, timeout=(5, 30))

        return req

    def _get_request_parts(self) -> tuple[int, str]:
        try:
            req = self._get_request()
        except requests.RequestException:
            return 400, "error"

        return req.status_code, req.text

    def validate(self) -> None:
        status_code, body = self._get_request_parts()

        self.status_code = status_code
        self.valid_status_code = self.good_status_code(status_code)
        self.save()

        if not self.valid_status_code:
            self.validated = False
            self.save()
            return

        new_hash = self.hash_data(body)

        if self.hash != new_hash:
            self.validated = False
            self.save()

    def fill_hash(self) -> None:
        if self.hash is None:
            status_code, body = self._get_request_parts()
            self.status_code = status_code
            self.valid_status_code = self.good_status_code(status_code)
            self.hash = self.hash_data(body)
            self.validated = False

    def save(self, force_insert: bool = False, force_update: bool = False, using=None, update_fields=None):
        self.fill_hash()

        return super().save(force_insert, force_update, using, update_fields)
