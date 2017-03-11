from django.apps import AppConfig


class LfsIoAppConfig(AppConfig):
    name = 'lfs.io'

    def ready(self):
        import export
        import listeners
