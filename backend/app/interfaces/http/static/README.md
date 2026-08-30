# Assets da documentação (opcional)

Por padrão o `/docs` carrega o Swagger UI de um CDN. Se a apresentação for numa
rede sem internet — ou instável —, a página abre em branco.

Baixe os arquivos abaixo **uma vez** para esta pasta e o hub passa a servi-los
localmente, sem nenhuma alteração de código:

```bash
cd backend/app/interfaces/http/static

curl -sLO https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js
curl -sLO https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css
curl -sLO https://cdn.jsdelivr.net/npm/redoc@next/bundles/redoc.standalone.js   # opcional
```

Sem esses arquivos, o comportamento padrão (CDN) continua valendo.
Estão no `.gitignore` por serem artefatos de terceiros.
