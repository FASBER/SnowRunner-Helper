"""Prepare a GitHub release's signed update.json without sending private keys.

Usage:
  python release_tools/prepare_github_release.py OWNER REPO 0.31.0 \
    installer_build/SnowRunnerHelper_Setup_v0.31.0.exe \
    D:/Secrets/snowrunner_ed25519.pem [--notes 'Что нового']

Upload the original installer and the generated update.json into a public
GitHub Release tagged vX.Y.Z. Do not push private key or staging copy to Git.
"""
import argparse
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from github_releases import github_setup_url, github_latest_manifest_url
from release_tools.sign_release import sign


def prepare(owner, repo, version, installer, private_key_file, *, notes='Исправления и улучшения.', output='update.json'):
    url = github_setup_url(owner, repo, version, Path(installer).name)
    data = sign(installer, url, version, private_key_file, notes=notes)
    out = Path(output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return {'manifest': str(out), 'download_url': url,
            'manifest_url': github_latest_manifest_url(owner, repo)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('owner')
    parser.add_argument('repo')
    parser.add_argument('version')
    parser.add_argument('installer')
    parser.add_argument('private_key_file')
    parser.add_argument('--notes', default='Исправления и улучшения.')
    parser.add_argument('--output', default='update.json')
    args = parser.parse_args()
    result = prepare(args.owner, args.repo, args.version, args.installer,
                     args.private_key_file, notes=args.notes, output=args.output)
    print('Ready to upload:')
    print('  ', args.installer)
    print('  ', result['manifest'])
    print('Release tag: v' + args.version)
    print('Stable update URL: ' + result['manifest_url'])

if __name__ == '__main__':
    main()
