from django.urls import reverse

from apps.sales.tests.test_sales_api import (
    BaseSetup,
    _headers,
    _customer_payload,
)


class CustomerApiCreateWithoutCodeTestCase(BaseSetup):
    def setUp(self):
        super().setUp()
        self.base = reverse("customer-list")
        self.h = _headers(self.client)

    def post_customer(self, name):
        return self.client.post(
            self.base,
            {"name": name},
            format="json",
            **self.h,
        )

    def test_first_create_mints_cus_0001(self):
        resp = self.post_customer("No Code Co")
        self.assertEqual(resp.status_code, 201, resp.content)
        self.assertEqual(resp.data["code"], "CUS-0001")

    def test_second_create_mints_cus_0002(self):
        self.post_customer("No Code Co")
        resp = self.post_customer("No Code Co 2")
        self.assertEqual(resp.status_code, 201, resp.content)
        self.assertEqual(resp.data["code"], "CUS-0002")
