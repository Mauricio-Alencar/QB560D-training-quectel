"""Publication exclusions, relative to aibox_training; no files are deleted.

Keep the Git rules in the root .gitignore aligned with GIT_EXCLUSIONS. A release
uses these rules even outside Git, and rejects forbidden explicit/locked inputs.
"""
from pathlib import PurePosixPath

GIT_EXCLUSIONS = {
    '/firmware/': 'Private firmware; distributed separately with restricted access.',
    '/archive/': 'Historical materials, backups, generators and old releases.',
    '/dist/': 'Generated versioned distributions, not repository source files.',
    '/training_v2/slides/fontes/': 'Presentation templates and authoring sources.',
    '/training_v2/slides/previews/': 'Presentation review images.',
    '/training_v2/slides/validation/': 'Internal presentation validation reports.',
    '/training_v2/slides/README.md': 'Presentation maintenance instructions.',
    '/training_v2/docs/PENDENCIAS_TREINAMENTO_TEMP.txt': 'Internal preparation backlog.',
    '/training_v2/host/update_slide_references.py': 'Obsolete slide generation script.',
    '**/.build/': 'Development builds, backups and temporary review candidates.',
    '**/.venv/': 'Machine-specific virtual environments; recreate after extraction.',
    '**/__pycache__/': 'Generated Python bytecode cache.',
    '*.pyc': 'Generated Python bytecode.',
    '*.pyo': 'Generated Python bytecode.',
    '/training_v2/provision_target/plan.json': 'Installation plan bound to a local inventory.',
    '/training_v2/provision_target/LATEST.json': 'Pointer to a local provisioning inventory.',
    '/training_v2/provision_target/os-release-atual.txt': 'Local target inventory snapshot.',
    '/training_v2/provision_target/RELATORIO_FIRMWARE_ATUAL.txt': 'Internal target preparation report.',
    '/training_v2/provision_target/VALIDACAO_ATUAL.json': 'Internal provisioning validation snapshot.',
    '/training_v2/provision_target/CORRECAO_RELOGIO.txt': 'Historical preparation and clock-fix report.',
    '/training_v2/provision_target/plan-console.log': 'Local planning console output.',
    '/training_v2/provision_target/prepare-console.log': 'Local preparation console output.',
    '/training_v2/provision_target/local-tests.log': 'Local test console output.',
    '/training_v2/provision_target/cache/payload-qb560d-docker-demo.tar': 'Regenerable deployment transfer archive; original locked inputs are retained.',
    '/training_v2/provision_target/cache/payload-qb560d-training-payload.tar': 'Regenerable deployment transfer archive; original locked inputs are retained.',
    '/training_v2/htp251/LATEST.json': 'Pointer to a local HTP run.',
    '/training_v2/htp251/BENCHMARK_LATEST.json': 'Pointer to a local benchmark run.',
    '/training_v2/htp251/test-temp/': 'Temporary HTP test files.',
    '/training_v2/htp251/output/': 'Regenerable HTP scratch output.',
}


def exclusion_reason(relative):
    """Return a Git exclusion reason, or None, for a project-relative path."""
    text = str(relative).replace('\\', '/')
    path = PurePosixPath(text)
    if path.is_absolute() or '..' in path.parts or (path.parts and ':' in path.parts[0]):
        raise ValueError('Expected a project-relative publication path: ' + text)
    text = path.as_posix().casefold()
    for pattern, reason in GIT_EXCLUSIONS.items():
        rule = pattern.casefold()
        if rule.startswith('**/'):
            if rule[3:-1] in [part.casefold() for part in path.parts]:
                return reason
        elif rule.startswith('*.'):
            if text.endswith(rule[1:]):
                return reason
        elif rule.endswith('/'):
            prefix = rule.strip('/')
            if text == prefix or text.startswith(prefix + '/'):
                return reason
        elif text == rule.lstrip('/'):
            return reason
    return None


def release_exclusion_reason(relative):
    reason = exclusion_reason(relative)
    if reason:
        return reason
    path = PurePosixPath(str(relative).replace('\\', '/'))
    if any(part.casefold() in {'.git', '.gitignore'} for part in path.parts):
        return 'Git metadata and ignore configuration are not student payload.'
    if path.suffix.casefold() == '.part':
        return 'Incomplete download.'
    return None
