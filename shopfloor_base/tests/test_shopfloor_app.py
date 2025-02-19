# Copyright 2021 Camptocamp SA (http://www.camptocamp.com)
# @author Simone Orsi <simahawk@gmail.com>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).
from odoo.tests.common import Form

from odoo.addons.shopfloor_base.utils import APP_VERSION

from .common import CommonCase


# @tagged("-at_install")
class TestShopfloorApp(CommonCase):
    @classmethod
    def setUpClassUsers(cls):
        super().setUpClassUsers()
        cls.env = cls.env(user=cls.shopfloor_manager)
        return

    @classmethod
    def setUpClassBaseData(cls):
        super().setUpClassBaseData()
        cls.records = cls.env["shopfloor.app"].create(
            {
                "name": "A wonderful test app",
                "tech_name": "test_app",
                "short_name": "Test app",
            }
        ) + cls.env["shopfloor.app"].create(
            {
                "name": "A wonderful test app 2",
                "tech_name": "test_app_2",
                "short_name": "Test app 2",
            }
        )
        return

    def test_app_create(self):
        # fmt: off
        expected = [
            {
                "api_route": "/shopfloor/api/test_app",
                "url": "/shopfloor/app/test_app/",
            },
            {
                "api_route": "/shopfloor/api/test_app_2",
                "url": "/shopfloor/app/test_app_2/",
            },
        ]
        # fmt: on
        self.assertRecordValues(self.records, expected)

    def _test_registered_routes(self, rec):
        # On class setup the registry is not ready thus endpoints are not registered yet
        rec._register_controllers(init=True)
        routes = rec._registered_routes()
        _check = {}
        for rule in routes:
            self.assertEqual(rule.route_group, rec._route_group())
            self.assertTrue(rule.endpoint_hash)
            service, endpoint = rule.route.split("/")[-2:]
            expected_handler_opts = {
                "default_pargs": [rec.id, service, endpoint],
                "klass_dotted_path": (
                    "odoo.addons.shopfloor_base.controllers.main.ShopfloorController"
                ),
                "method_name": "_process_endpoint",
            }
            self.assertEqual(rule.handler_options, expected_handler_opts)
            _check[rule.route] = set(rule.routing["methods"])
        expected = {
            # TODO: review methods
            f"/shopfloor/api/{rec.tech_name}/app/user_config": {"POST"},
            f"/shopfloor/api/{rec.tech_name}/user/menu": {"POST"},
            f"/shopfloor/api/{rec.tech_name}/user/user_info": {"POST"},
            f"/shopfloor/api/{rec.tech_name}/menu/search": {
                "GET",
            },
            f"/shopfloor/api/{rec.tech_name}/profile/search": {
                "GET",
            },
            f"/shopfloor/api/{rec.tech_name}/scan_anything/scan": {"POST"},
        }
        for route, method in expected.items():
            self.assertEqual(
                _check[route], method, f"{route}: {method} != {_check[route]}"
            )

        expected = sorted([f"{k} ({', '.join(v)})" for k, v in expected.items()])
        rec.invalidate_cache(["registered_routes"])
        self.assertEqual(
            sorted(rec.registered_routes.splitlines()),
            expected,
            f"{rec.tech_name} failed",
        )

    def test_registered_routes(self):
        rec1, rec2 = self.records
        self._test_registered_routes(rec1)
        self._test_registered_routes(rec2)
        # TODO: test after routing_map cleaned

    def test_api_url_for_service(self):
        app = self.shopfloor_app
        self.assertEqual(
            app.api_url_for_service("profile"),
            f"/shopfloor/api/{app.tech_name}/profile",
        )
        self.assertEqual(
            app.api_url_for_service("profile", "search"),
            f"/shopfloor/api/{app.tech_name}/profile/search",
        )
        self.assertEqual(
            app.api_url_for_service("app", "user_config"),
            f"/shopfloor/api/{app.tech_name}/app/user_config",
        )

    def test_make_app_info(self):
        info = self.shopfloor_app._make_app_info()
        expected = {
            "auth_type": "user_endpoint",
            "base_url": "/shopfloor/api/test/",
            "url": "/shopfloor/app/test/",
            "demo_mode": False,
            "manifest_url": "/shopfloor/app/test/manifest.json",
            "name": "Test",
            "profile_required": False,
            "running_env": "prod",
            "short_name": "test",
            "version": APP_VERSION,
            "lang": {
                "default": False,
                "enabled": [],
            },
        }
        self.assertEqual(info, expected)
        info = self.shopfloor_app._make_app_info(demo=True)
        self.assertEqual(info["demo_mode"], True)
        lang_en, lang_fr = self.env.ref("base.lang_en"), self.env.ref("base.lang_fr")
        lang_fr.sudo().active = True
        self.shopfloor_app.sudo().lang_id = lang_en
        self.shopfloor_app.sudo().lang_ids = lang_en + lang_fr
        info = self.shopfloor_app._make_app_info()
        self.assertEqual(
            info["lang"], {"default": "en-US", "enabled": ["en-US", "fr-FR"]}
        )

    def test_make_app_manifest(self):
        param = "http://localhost:8069"
        manifest = self.shopfloor_app._make_app_manifest()
        expected = {
            "name": self.shopfloor_app.name,
            "short_name": self.shopfloor_app.short_name,
            "start_url": param + self.shopfloor_app.url,
            "scope": param + self.shopfloor_app.url,
            "id": self.shopfloor_app.url,
            "display": "fullscreen",
            "icons": [],
        }
        self.assertEqual(manifest, expected)

    def test_lang_onchanges(self):
        lang_en, lang_fr = self.env.ref("base.lang_en"), self.env.ref("base.lang_fr")
        lang_fr.sudo().active = True
        form = Form(self.shopfloor_app)
        # No avail langs
        self.assertFalse(form.lang_id)
        self.assertFalse(form.lang_ids)
        form.lang_id = lang_en
        # Avail langs updated
        self.assertIn(lang_en, form.lang_ids)
        # Replace avail w/ FR
        form.lang_ids.add(lang_fr)
        form.lang_ids.remove(lang_en.id)
        # lang wiped out
        self.assertFalse(form.lang_id)
