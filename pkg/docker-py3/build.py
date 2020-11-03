import docker
import gramex.cache
import io

template = gramex.cache.open('Dockerfile.tmpl', 'template', rel=True)
release = gramex.cache.open('../../gramex/release.json', rel=True)['info']
client = docker.from_env()
tag = f'gramener/gramex:{release["version"]}'
streamer = client.api.build(
    fileobj=io.BytesIO(template.generate(**release)),
    tag=tag,
    decode=True,
    rm=True,
)
for chunk in streamer:
    if 'stream' in chunk:
        print(chunk['stream'], end='')      # noqa

# Tag current version as latest
client.api.tag(tag, 'gramener/gramex', 'latest')
