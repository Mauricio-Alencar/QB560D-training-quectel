#!/bin/sh
set -eu
root=/opt/qb560d-docker-demo
cd "$root"
d() { sh "$root/target/docker.sh" "$@"; }
base=$(cat config/base-image.txt)
image=qb560d-telemetry:1.0.0
archive=offline/images/qb560d-telemetry-1.0.0-arm64.tar.gz
[ ! -e "$archive" ] || { echo 'Archive already exists; preserve it before rebuilding'; exit 1; }
d pull --platform linux/arm64 "$base"
digest=$(d image inspect "$base" --format '{{index .RepoDigests 0}}')
printf '%s\n' "$digest" > evidence/base-image-digest.txt
d buildx build --platform linux/arm64 --network none --build-arg "BASE_IMAGE=$digest" --load --tag "$image" app
d image inspect "$image" > evidence/image-inspect.json
[ "$(d image inspect "$image" --format '{{.Os}}/{{.Architecture}}')" = linux/arm64 ]
mkdir -p offline/images
d image save --output offline/images/qb560d-telemetry-1.0.0-arm64.tar "$image"
gzip -n offline/images/qb560d-telemetry-1.0.0-arm64.tar
sha256sum "$archive" > offline/image.sha256
cat offline/image.sha256
echo 'RESULT: ARM64_IMAGE_BUILT_AND_EXPORTED'
