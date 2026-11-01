"""Check that the tracked overview keeps all six original views."""

from pathlib import Path
import tempfile
import unittest

from matplotlib.image import imread, imsave
import numpy as np

from sketches.preview import save_preview
from sketches.settings import ROOT


class PreviewTests(unittest.TestCase):
    def test_six_views_keep_pixels_and_question_order(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            directory = Path(directory)
            images, paths = [], []
            for i in range(6):
                # Alternate RGB/RGBA input; use unequal sizes to check centering.
                pixels = np.full((12 - i % 2, 16 - i % 3, 3 + i % 2), 255, dtype=np.uint8)
                pixels[:, :, :3] = (i * 30, 200 - i * 20, 40 + i * 10)
                pixels[0, 0, :3] = 0
                path = directory / f"view-{i}.png"
                imsave(path, pixels)
                paths.append(path)
                images.append(np.rint(imread(path) * 255).astype(np.uint8))
            output = save_preview(paths, directory / "nested/preview.png")
            result = np.rint(imread(output) * 255).astype(np.uint8)
            self.assertEqual(result.shape, (132, 104, 4))
            for i, original in enumerate(images):
                top = 24 + (i // 2) * 36 + (12 - original.shape[0]) // 2
                left = 24 + (i % 2) * 40 + (16 - original.shape[1]) // 2
                np.testing.assert_array_equal(
                    result[top:top + original.shape[0], left:left + original.shape[1]], original,
                )
            np.testing.assert_array_equal(result[0, 0], [255, 255, 255, 255])

    def test_incomplete_preview_fails_without_output(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            output = Path(directory) / "preview.png"
            with self.assertRaisesRegex(ValueError, "exactly six"):
                save_preview([], output)
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
