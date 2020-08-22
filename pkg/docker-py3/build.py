import docker
import gramex.cache
import io

template = gramex.cache.open('Dockerfile.tmpl', 'template', rel=True)
release = gramex.cache.open('../../gramex/release.json', rel=True)
client = docker.from_env()
streamer = client.api.build(
    fileobj=io.BytesIO(template.generate(**release)),
    tag=f'gramener/gramex:{release["version"]}',
    decode=True,
    rm=True,
)
for chunk in streamer:
    if 'stream' in chunk:
        print(chunk['stream'])  # noqa
