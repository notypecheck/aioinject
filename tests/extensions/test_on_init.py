from aioinject import Container, SyncContainer
from aioinject.extensions import OnInitExtension


def test_on_mount_extension() -> None:
    class TestExtension(OnInitExtension):
        def __init__(self) -> None:
            self.mounted = False

        def on_init(self, _: Container | SyncContainer) -> None:
            self.mounted = True

    extension = TestExtension()
    assert not extension.mounted
    Container(extensions=[extension])
    assert extension.mounted
