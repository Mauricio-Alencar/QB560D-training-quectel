"""Guard public/student boundaries, including explicit inputs and real Git rules."""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

TRAINING = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TRAINING/'host'))
import release_package
from release_policy import GIT_EXCLUSIONS, exclusion_reason, release_exclusion_reason
from validate_release import validate_selection


class PublicationBoundaries(unittest.TestCase):
    def test_existing_local_logs_are_not_valid_links_until_selected(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'docs').mkdir();(root/'raw-logs').mkdir()
            guide=root/'docs/README.md';log=root/'raw-logs/console.txt'
            guide.write_text('[Session logs](../raw-logs/)');log.write_text('internal log')
            with self.assertRaisesRegex(RuntimeError,'link not in student package'):
                validate_selection({guide},root)
            self.assertEqual(validate_selection({guide,log},root)['result'],'PASS_SELECTED_LINKS')

    def test_student_readmes_assets_and_locked_evidence_remain_allowed(self):
        for path in (
            'README.md', 'training_v2/README.md', 'training_v2/demos/docker/README.md',
            'training_v2/Qualcomm_AI_Hub_Training/README.md',
            'training_v2/runtimes/qairt_2_51/readme.me',
            'training_v2/slides/QB560D_EU_Training.pptx',
            'training_v2/provision_target/bundle-manifest.json',
            'training_v2/runtimes/qairt_2_51/versions.lock.json',
            'training_v2/evidence/target-ai/classification/result.json',
            'training_v2/demos/docker/evidence/archive/result.json',
        ):
            with self.subTest(path=path):
                self.assertIsNone(release_exclusion_reason(path))

    def test_forbidden_explicit_inputs_cannot_bypass_tree_filter(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            with patch.object(release_package, 'PROJECT', root):
                for relative in ('firmware/private.bin', 'training_v2/slides/README.md',
                                 'training_v2/demos/docker/.build/old.zip',
                                 'training_v2/provision_target/VALIDACAO_ATUAL.json'):
                    path = root/relative
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text('keep this local file')
                    with self.subTest(path=relative), self.assertRaisesRegex(ValueError, 'Forbidden release input'):
                        release_package.checked_input(path)
                    self.assertEqual(path.read_text(), 'keep this local file')

    def test_external_inputs_and_traversal_are_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            project = root/'workspace'
            project.mkdir()
            external = root/'private.bin'
            external.write_text('outside')
            with patch.object(release_package, 'PROJECT', project), self.assertRaisesRegex(ValueError, 'External release input'):
                release_package.checked_input(external)
        with self.assertRaises(ValueError):
            exclusion_reason('../firmware/private.bin')

    @unittest.skipUnless(shutil.which('git') and (TRAINING.parent/'.gitignore').is_file(),
                         'Git ignore rules are checked in the source checkout, not the student ZIP')
    def test_git_rules_match_publication_policy_without_hiding_other_readmes(self):
        samples = []
        for rule in GIT_EXCLUSIONS:
            if rule.startswith('**/'):
                path = 'training_v2/demos/docker/'+rule[3:]+'sample.txt'
            elif rule.startswith('*.'):
                path = 'training_v2/host/example'+rule[1:]
            else:
                path = rule.lstrip('/')+('sample.txt' if rule.endswith('/') else '')
            samples.append(path)
        samples += ['README.md', 'training_v2/README.md', 'references/README.md',
                    'training_v2/demos/docker/README.md',
                    'training_v2/runtimes/qairt_2_51/readme.me',
                    'training_v2/slides/QB560D_EU_Training.pptx']
        with tempfile.TemporaryDirectory() as folder:
            subprocess.run(['git', 'init', '--quiet', folder], check=True, capture_output=True)
            shutil.copyfile(TRAINING.parent/'.gitignore', Path(folder)/'.gitignore')
            result = subprocess.run(
                ['git', '-c', 'core.excludesFile=NUL', '-C', folder, 'check-ignore', '--no-index', '--stdin', '-z'],
                input=('\0'.join(samples)+'\0').encode('utf-8'), capture_output=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(set(result.stdout.decode('utf-8').split('\0'))-{''}, {p for p in samples if exclusion_reason(p)})


if __name__ == '__main__':
    unittest.main()
