import sys

from django.apps import AppConfig
from django.conf import settings


class TripsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "trips"

    def ready(self):
        if settings.ENVIRONMENT == "dev" and sys.platform == "darwin":
            self._patch_qcluster_mp_context()

    @staticmethod
    def _patch_qcluster_mp_context():
        """Force django-q2 workers to spawn instead of fork on macOS.

        setproctitle (pulled in transitively by granian[pname]) crashes with a
        segfault when called from a forked child on macOS: CoreFoundation's
        os_log preference lookup isn't fork-safe. django-q2's get_mp_context()
        picks "fork" whenever it's available, so hide it from
        get_all_start_methods() instead of patching django_q.cluster directly
        — every qcluster child re-runs django.setup() (and this hook) from a
        fresh interpreter while django_q.cluster is still mid-import, so
        patching that module here would race its own circular-import guard.
        multiprocessing has no such circularity.
        """
        import multiprocessing

        original_get_all_start_methods = multiprocessing.get_all_start_methods

        def get_all_start_methods_without_fork():
            return [m for m in original_get_all_start_methods() if m != "fork"]

        multiprocessing.get_all_start_methods = get_all_start_methods_without_fork
