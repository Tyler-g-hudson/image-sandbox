from pytest import raises

from docker_cli._mount import BindMount


def test_mount_init():
    """Tests that the mount object works and returns the correct string."""
    mount = BindMount(
        host_mount_point="anything", image_mount_point="anything", permissions="ro"
    )
    assert mount.mount_string() == "anything:anything:ro"


def test_mount_error():
    """
    Tests that the mount object fails to build when given an unrecognized
    permission.
    """
    with raises(ValueError):
        BindMount(
            host_mount_point="anything",
            image_mount_point="anything",
            permissions="malformed",
        )
