from shlex import split
from subprocess import CalledProcessError, run

from pytest import mark, raises

from wigwam import Image


@mark.images
class TestImageInternals:
    def test_inspect(self, image_tag, image_id):
        """
        Tests that the _inspect method correctly retrieves data from the Docker
        image.
        """
        inspect_process = run(
            split("docker inspect -f='{{.RepoTags}}' " + image_tag),
            capture_output=True,
            text=True,
            check=True,
        )
        tags = inspect_process.stdout.strip()

        img: Image = Image(image_id)
        img_tags = img._inspect(format="{{.RepoTags}}").strip()
        assert img_tags == tags

    def test_inspect_malformed(self, image_id):
        """
        Tests that the _inspect method correctly raises a CalledProcessError
        when a malformed string is passed to it.
        """
        img: Image = Image(image_id)
        with raises(CalledProcessError):
            img._inspect(format="{{.MalformedInspect}}").strip()
