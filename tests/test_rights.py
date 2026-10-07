import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common
import server


class RightsTests(unittest.TestCase):
    def test_unreviewed_replacement_cannot_install_or_generate(self):
        for change in (dict(repo='another/model'), dict(revision='unreviewed-new-weights')):
            replacement = dict(common.MODELS['image'], **change)
            with patch.dict(common.MODELS, image=replacement):
                for action in ('install', 'generate'):
                    with self.subTest(action=action, change=change), self.assertRaisesRegex(ValueError, 'Commercial use'):
                        server.validate(dict(kind='image', action=action, prompt='a flower'))

    def test_rights_records_actual_download_and_keeps_media_unchanged(self):
        with tempfile.TemporaryDirectory() as temp:
            data = Path(temp)
            model = data / 'models' / 'image'
            model.mkdir(parents=True)
            (model / 'download.json').write_text(json.dumps({'revision': 'measured-revision'}))
            destination = data / 'result'
            destination.mkdir()
            media = destination / 'image.png'
            media.write_bytes(b'existing-media')
            with patch.object(common, 'DATA', data):
                common.write_rights(destination, dict(kind='image', id='test-output'))
            rights = json.loads((destination / 'rights.json').read_text(encoding='utf-8'))
            self.assertEqual(rights['download']['revision'], 'measured-revision')
            self.assertEqual(media.read_bytes(), b'existing-media')
            self.assertIn('does not guarantee', rights['notice'])
            self.assertIn('OpenRAIL', (destination / 'commercial-use.txt').read_text(encoding='utf-8'))


if __name__ == '__main__':
    unittest.main()
