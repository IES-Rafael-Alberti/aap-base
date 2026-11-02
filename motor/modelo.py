"""Cliente mínimo para una API compatible con OpenAI (por defecto, OpenRouter).

Variables de entorno (o .env):
    AAP_API_KEY   clave del proveedor (vale también OPENROUTER_API_KEY)
    AAP_URL       endpoint de chat completions del proveedor
"""

import json
import os
import math
from pathlib import Path
import re
import urllib.parse
import urllib.error
import urllib.request
import uuid

MISSING='Tu Kali no tiene la IA del aula configurada. Avisa al profesor.'
NETWORK='No se llega al servicio de IA del aula.'
UNAVAILABLE='El servicio de IA no está disponible ahora mismo. Inténtalo más tarde.'


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):return None


def cargar(path=None):
    path=Path(path or Path.home()/'.aula-ia.env')
    data={}
    for line in path.read_text().splitlines():
        if '=' in line and not line.lstrip().startswith('#'):
            k,v=line.split('=',1)
            if k.strip() in ('AAP_URL','AAP_MODELO','AAP_API_KEY'):data[k.strip()]=v.strip().strip('\"\'')
    if not re.fullmatch(r'sk-[A-Za-z0-9_-]{16,1000}',data.get('AAP_API_KEY','')):raise ValueError(MISSING)
    if data.get('AAP_URL')!='http://10.30.0.6:4000/v1/chat/completions':raise ValueError(MISSING)
    return data


def consulta(key,opener=None):
    opener=opener or urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect())
    req=urllib.request.Request('http://10.30.0.6:4001/cupo',headers={'Authorization':'Bearer '+key})
    try:
        with opener.open(req,timeout=5) as response:
            raw=response.read(32769)
            if len(raw)>32768:raise ValueError()
            value=json.loads(raw)
            if not isinstance(value,dict):raise ValueError()
            return value
    except urllib.error.HTTPError as exc:
        exc.close();raise


def numero(v):
    if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or v<0:raise ValueError()
    return v


def cupo(key,opener=None):
    data=consulta(key,opener)
    if set(data)!={'consumidor','gastado_usd','tope_usd','renovacion','rpm','tpm','estado'}:raise ValueError()
    if not isinstance(data['consumidor'],str) or not re.fullmatch(r'alumno(?:[0-9]{2,3}|-test(?:-[a-z0-9]+)+)',data['consumidor']):raise ValueError()
    spent,limit=numero(data['gastado_usd']),numero(data['tope_usd'])
    if data['estado'] not in ('activa','agotado') or (data['estado']=='agotado')!=(spent>=limit):raise ValueError()
    reset=data['renovacion']
    if reset is not None:
        from datetime import datetime
        if not isinstance(reset,str) or len(reset)>64:raise ValueError()
        date=datetime.fromisoformat(reset.replace('Z','+00:00'))
        if date.tzinfo is None:raise ValueError()
        reset=date.isoformat()
    for field in ('rpm','tpm'):
        if type(data[field]) is not int or data[field]<=0:raise ValueError()
    return dict(gastado=spent,tope=limit,renueva=reset or 'sin fecha disponible',rpm=data['rpm'],tpm=data['tpm'],estado=data['estado'])


def del_aula(model):
    """Modelos de la clave del aula: aula, aula-N y corsario-N."""
    return bool(re.fullmatch(r'aula|(?:aula|corsario)-[0-9]+',model or ''))


def mensaje(code,account=None,model='aula'):
    aula=del_aula(model)
    if code==401:return 'Tu clave ya no es válida (se ha cambiado o retirado). Avisa al profesor.'
    if code==403:return 'Ese modelo no está disponible en el aula. Usa el de tu aula (corsario-N o aula-N, en Acceso-IA.txt).'
    if code==422 or code in (404,429) and aula and account and account['gastado']>=account['tope']:
        return 'Has agotado tu cupo de IA. Se renueva el '+(account or {}).get('renueva','fecha no disponible')+'.'
    if code==429 and not aula:return 'Demasiadas peticiones seguidas. Espera un minuto.'
    if code==429 and account and account['gastado']<account['tope']:
        return UNAVAILABLE+' Si has hecho muchas peticiones, espera un minuto.'
    return UNAVAILABLE



def abrir_chat(peticion,timeout):
    return urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect()).open(peticion,timeout=timeout)


URL_POR_DEFECTO = "https://openrouter.ai/api/v1/chat/completions"


class Modelo:
    def __init__(self, nombre: str, clave: str | None = None, timeout: int | None = None):
        self.nombre = nombre
        self.clave = (clave or os.environ.get("AAP_API_KEY")
                      or os.environ.get("OPENROUTER_API_KEY"))
        fallback=None
        if not self.clave:
            try:fallback=cargar()
            except (OSError,ValueError):raise RuntimeError(MISSING) from None
            self.clave=fallback['AAP_API_KEY']
            self.nombre=fallback.get('AAP_MODELO','aula')
        if not self.clave:
            raise RuntimeError("Falta la clave: define AAP_API_KEY en el entorno o en .env")
        self.url = (fallback["AAP_URL"] if fallback else os.environ.get("AAP_URL", URL_POR_DEFECTO))
        self.es_aula=self.url=="http://10.30.0.6:4000/v1/chat/completions"
        # Un modelo con razonamiento puede tardar: timeout amplio (configurable con AAP_TIMEOUT).
        self.timeout = timeout or int(os.environ.get("AAP_TIMEOUT", "300"))

    def responder(self, mensajes: list[dict], herramientas: list[dict]) -> dict:
        """Devuelve {"mensaje": {...}, "uso": {"entrada": n, "salida": n}}."""
        cuerpo = json.dumps({
            "model": self.nombre,
            "messages": mensajes,
            "tools": herramientas,
            **self._marca(mensajes),
        }).encode()
        peticion = urllib.request.Request(self.url, data=cuerpo, headers={
            "Authorization": f"Bearer {self.clave}",
            "Content-Type": "application/json",
        })
        try:
            with (abrir_chat(peticion,self.timeout) if self.es_aula else urllib.request.urlopen(peticion, timeout=self.timeout)) as r:
                datos = json.load(r)
        except urllib.error.HTTPError as e:
            if self.es_aula:
                code=e.code;e.close();account=None
                if code in (404,422,429):
                    try:account=cupo(self.clave)
                    except urllib.error.HTTPError as quota_error:
                        quota_code=quota_error.code;quota_error.close()
                        if quota_code==401:raise RuntimeError(mensaje(401)) from None
                        if code in (404,429):raise RuntimeError('No se puede consultar el cupo ahora. Inténtalo más tarde o avisa al profesor.') from None
                    except (OSError,ValueError,TypeError,KeyError):
                        if code in (404,429):raise RuntimeError('No se puede consultar el cupo ahora. Inténtalo más tarde o avisa al profesor.') from None
                raise RuntimeError(mensaje(code,account,self.nombre)) from None
            raise RuntimeError(f"El proveedor respondió {e.code}: {e.read()[:500]!r}") from e
        except (urllib.error.URLError,TimeoutError,ConnectionError) as e:
            if self.es_aula:raise RuntimeError(NETWORK) from None
            if isinstance(e,urllib.error.URLError):raise
            raise RuntimeError(f"El modelo no respondió en {self.timeout} s. "
                               "Súbelo con AAP_TIMEOUT.") from e
        uso = datos.get("usage", {})
        return {
            "mensaje": datos["choices"][0]["message"],
            "uso": {"entrada": uso.get("prompt_tokens", 0),
                    "salida": uso.get("completion_tokens", 0)},
        }

    def _marca(self, mensajes: list[dict]) -> dict:
        """Marca de ejecución para el gateway del aula: agrupa las vueltas de una misma ejecución
        para que el profesor vea cada ejecución completa. Solo con la IA del aula."""
        if not self.es_aula:
            return {}
        if len(mensajes) <= 2 or not getattr(self, "_ejecucion", None):  # instrucciones + objetivo: empieza otra
            self._ejecucion = str(uuid.uuid4())
        paso = 1 + sum(1 for m in mensajes if m.get("role") == "assistant")
        return {"metadata": {"aap": {"version": 1, "app": "corsario", "ejecucion": self._ejecucion, "paso": paso}}}
