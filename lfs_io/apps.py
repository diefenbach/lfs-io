from django.apps import AppConfig


class LfsIoAppConfig(AppConfig):
    name = "lfs_io"

    def ready(self):
        from . import export
        from . import listeners
