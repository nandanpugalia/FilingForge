"""Release notifications are on by default, with an explicit quiet option."""
from pathlib import Path
import unittest


class QuietReleaseTests(unittest.TestCase):
    def test_workflow_has_an_explicit_release_tag_and_notifications_enabled_by_default(self):
        text = Path('.github/workflows/release.yml').read_text()
        dispatch = text.split('  workflow_dispatch:', 1)[1].split('\njobs:', 1)[0]
        self.assertIn('release_tag:', dispatch)
        self.assertIn('notify_discord:', dispatch)
        self.assertIn('default: true', dispatch)
        self.assertIn('RELEASE_TAG: ${{ inputs.release_tag || github.ref_name }}', text)

    def test_every_discord_step_obeys_the_release_notification_switch(self):
        text = Path('.github/workflows/release.yml').read_text()
        notices = [step for step in text.split('      - name: ') if step.startswith('Notify Discord')]
        self.assertEqual(len(notices), 4)
        for step in notices:
            condition = next((line for line in step.splitlines() if line.strip().startswith('if:')), '')
            self.assertIn("env.NOTIFY_DISCORD == 'true'", condition)
            if 'failed' in step.splitlines()[0] or 'needs attention' in step.splitlines()[0]:
                self.assertIn('failure()', condition)

    def test_dispatch_uses_selected_tag_for_all_release_operations(self):
        text = Path('.github/workflows/release.yml').read_text()
        self.assertIn('tagName: ${{ env.RELEASE_TAG }}', text)
        self.assertIn("prerelease: ${{ contains(env.RELEASE_TAG, '-') }}", text)
        self.assertNotIn('TAG="${{ github.ref_name }}"', text)
        self.assertNotIn("gh release download '${{ github.ref_name }}'", text)
        self.assertIn('python scripts/check_release_version.py --tag "$RELEASE_TAG"', text)


if __name__ == '__main__':
    unittest.main()
