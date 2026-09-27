from django.urls import reverse
from rest_framework import status

from apps.inventory.tests.base import BaseSetup


class ProductListPaginationSearchTests(BaseSetup):
    def test_product_list_is_paginated_envelope(self):
        h = self.admin_h()
        for i in range(3):
            self.make_product(sku=f"PS-{i:04d}")
        resp = self.client.get(reverse("product-list") + "?page_size=2", **h)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["count"], 3)
        self.assertEqual(len(resp.data["results"]), 2)
        self.assertIsNotNone(resp.data["next"])

    def test_product_list_search_filters(self):
        h = self.admin_h()
        self.make_product(sku="P-WIDGET", name="Aluminum Widget")
        self.make_product(sku="P-BOLT", name="Steel Bolt")
        resp = self.client.get(reverse("product-list") + "?search=bolt", **h)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["count"], 1)
        self.assertEqual(resp.data["results"][0]["sku"], "P-BOLT")
        self.assertEqual(
            resp.data["results"][0]["name"], "Steel Bolt"
        )