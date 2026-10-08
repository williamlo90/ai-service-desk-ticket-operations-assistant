"""Host-side verified Docker archive when daemon-side registry transfer stalls.

Uses only the public official Quay repository. Checks compressed layer hashes,
uncompressed diff IDs and image config digest before Docker load.
"""
from pathlib import Path
from hashlib import sha256
from urllib.request import Request,urlopen
import gzip,io,json,shutil,subprocess,tarfile,time

ROOT=Path(__file__).resolve().parents[1]
BASE='https://quay.io/v2/keycloak/keycloak/'
TAG='quay.io/keycloak/keycloak:26.8.0'


def main():
    directory=ROOT/'local/images/keycloak-26.8.0';directory.mkdir(parents=True,exist_ok=True)
    if shutil.disk_usage(directory).free<4*1024**3:raise RuntimeError('At least 4 GiB free required')
    with urlopen('https://quay.io/v2/auth?service=quay.io&scope=repository:keycloak/keycloak:pull',timeout=30) as r:token=json.load(r)['token']
    headers={'Authorization':'Bearer '+token,'Accept':'application/vnd.oci.image.index.v1+json, application/vnd.oci.image.manifest.v1+json, application/vnd.docker.distribution.manifest.list.v2+json, application/vnd.docker.distribution.manifest.v2+json'}
    def get(path):
        with urlopen(Request(BASE+path,headers=headers),timeout=30) as r:return r.read()
    index=json.loads(get('manifests/26.8.0'))
    digest=next(x['digest'] for x in index['manifests'] if x.get('platform',{}).get('architecture')=='amd64' and x.get('platform',{}).get('os')=='linux')
    raw=get('manifests/'+digest);assert 'sha256:'+sha256(raw).hexdigest()==digest
    manifest=json.loads(raw);config_raw=get('blobs/'+manifest['config']['digest'])
    assert 'sha256:'+sha256(config_raw).hexdigest()==manifest['config']['digest']
    config=json.loads(config_raw);layer_paths=[]
    for number,layer in enumerate(manifest['layers']):
        compressed=directory/(layer['digest'].split(':')[1]+'.gz')
        if not compressed.exists() or sha256(compressed.read_bytes()).hexdigest()!=layer['digest'].split(':')[1]:
            downloaded=0;last=time.monotonic();digestor=sha256()
            with urlopen(Request(BASE+'blobs/'+layer['digest'],headers=headers),timeout=30) as response,compressed.open('wb') as out:
                while True:
                    chunk=response.read(1024*1024)
                    if not chunk:break
                    downloaded+=len(chunk)
                    if downloaded>layer['size']:raise RuntimeError('Unexpected layer length')
                    out.write(chunk);digestor.update(chunk)
                    if time.monotonic()-last>=20:
                        print('Official layer '+str(number+1)+': '+str(round(downloaded/layer['size']*100))+'%',flush=True);last=time.monotonic()
            assert downloaded==layer['size'] and 'sha256:'+digestor.hexdigest()==layer['digest']
        unpacked=directory/(str(number)+'.tar');digestor=sha256()
        with gzip.open(compressed,'rb') as source,unpacked.open('wb') as out:
            while chunk:=source.read(1024*1024):out.write(chunk);digestor.update(chunk)
        assert 'sha256:'+digestor.hexdigest()==config['rootfs']['diff_ids'][number]
        layer_paths.append(unpacked)
        print('Official layer '+str(number+1)+' verified.',flush=True)
    archive=directory/'verified-image.tar';config_name=manifest['config']['digest'].split(':')[1]+'.json'
    with tarfile.open(archive,'w') as out:
        def add_bytes(name,data):
            info=tarfile.TarInfo(name);info.size=len(data);out.addfile(info,io.BytesIO(data))
        add_bytes(config_name,config_raw)
        add_bytes('manifest.json',json.dumps([{'Config':config_name,'RepoTags':[TAG],
            'Layers':[str(i)+'/layer.tar' for i in range(len(layer_paths))]}]).encode())
        for i,path in enumerate(layer_paths):out.add(path,arcname=str(i)+'/layer.tar')
    subprocess.run(['docker','load','-i',str(archive)],check=True,stdout=subprocess.DEVNULL)
    actual=subprocess.check_output(['docker','image','inspect',TAG,'--format','{{.Id}}'],text=True).strip()
    assert actual==manifest['config']['digest']
    report={'image':TAG,'registry_manifest_digest':digest,'image_config_digest':actual,
        'layers_verified':len(layer_paths),'source':'Official public quay.io/keycloak/keycloak repository'}
    (ROOT/'docs/phase-5/keycloak-image-provenance.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Official Keycloak image loaded; config digest and every layer verified.',flush=True)


if __name__=='__main__':main()
