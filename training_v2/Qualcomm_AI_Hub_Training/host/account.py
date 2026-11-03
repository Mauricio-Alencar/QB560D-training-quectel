"""Configure AI Hub locally without echoing the API token or putting it in history."""
import argparse
import configparser
import getpass
import json
import os
from pathlib import Path
import shlex
import sys


def token_from_paste(value):
    value = value.strip()
    if not value or '\n' in value or '\r' in value:
        raise ValueError('Use one nonempty line')
    if value.startswith('qai-hub '):
        parts = shlex.split(value)
        if parts[:3] == ['qai-hub', 'configure', '--api_token'] and len(parts) == 4:
            value = parts[3]
        elif parts[:2] == ['qai-hub', 'configure'] and len(parts) == 3 and parts[2].startswith('--api_token='):
            value = parts[2].split('=', 1)[1]
        else:
            raise ValueError('Paste only the token or the portal configure command')
    if not value or any(c.isspace() for c in value):
        raise ValueError('Token must not contain whitespace')
    return value


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('action', choices=['check', 'configure', 'devices'])
    p.add_argument('--contains', default='', help='Filter public device names/attributes')
    a = p.parse_args()
    import qai_hub as hub
    from qai_hub.api_utils import get_config_path
    import numpy as np
    import onnx
    config_path = Path(get_config_path()).resolve()
    project = Path(__file__).resolve().parents[2]
    if a.action == 'check':
        print(json.dumps({'python': sys.version.split()[0], 'qai_hub': str(hub.__version__),
                          'numpy': np.__version__, 'onnx': onnx.__version__,
                          'account_configured': config_path.is_file()}, indent=2))
        return 0
    if a.action == 'configure':
        if config_path.is_relative_to(project):
            p.error('Keep the API token outside the training folder. Review QAIHUB_CLIENT_INI.')
        if config_path.exists():
            print('Configuration already exists. Use devices to validate it; it was preserved.')
            return 0
        try:
            token = token_from_paste(getpass.getpass('Cole o API token do Workbench (entrada oculta): '))
        except ValueError:
            p.error('Cole uma linha com o token ou o comando configure copiado do portal.')
        try:
            devices = hub.Client(hub.ClientConfig(api_token=token, verbose=False)).get_devices()
        except Exception as exc:
            print('ACCOUNT_NOT_VALIDATED: ' + type(exc).__name__)
            print('Confira token, organizacao ativa e acesso HTTPS. Nenhuma credencial foi gravada.')
            return 2
        config = configparser.ConfigParser()
        config['api'] = {'api_token': token, 'api_url': 'https://workbench.aihub.qualcomm.com',
                         'web_url': 'https://workbench.aihub.qualcomm.com', 'verbose': 'false'}
        config_path.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(config_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            config.write(f)
        print('ACCOUNT_READY: ' + str(len(devices)) + ' hosted devices returned.')
        print('Token salvo na configuracao privada do usuario, fora da pasta do treinamento.')
        return 0
    if not config_path.is_file():
        print('ACCOUNT_NOT_CONFIGURED: execute configure primeiro.')
        return 2
    try:
        devices = hub.Client().get_devices()
    except Exception as exc:
        print('DEVICE_LIST_FAILED: ' + type(exc).__name__)
        print('Confira autenticacao e acesso HTTPS. Nenhum job foi enviado.')
        return 2
    selected = [d for d in devices if a.contains.lower() in
                (d.name + ' ' + ' '.join(d.attributes)).lower()]
    print('Devices returned: ' + str(len(devices)) + '. Matching filter: ' + str(len(selected)))
    for d in selected:
        print(json.dumps({'name': d.name, 'os': str(d.os), 'attributes': list(d.attributes)}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
