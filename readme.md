# Integração SIGA -> MegaZap

Esta integração busca alunos ativos no ano de 2026 no SIGA, consulta boletos que vencem nos próximos 5 dias e envia uma solicitação para o MegaZap conforme o payload configurado. Como as documentações do SIGA e do MegaZap estão protegidas, os endpoints e chaves são configuráveis por variáveis de ambiente para adequar ao ambiente real.

## Requisitos

- Python 3.11+
- Dependências em `requirements.txt`

## Instalação

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Configuração

Defina as variáveis de ambiente antes de executar:

```bash
export SIGA_AUTH_TOKEN="seu-token-siga"
export MEGAZAP_AUTH_TOKEN="seu-token-megazap"
```

> **Observação sobre tokens**: os tokens são lidos apenas de variáveis de ambiente e não devem ser versionados. Para testes com `--dry-run`, somente o `SIGA_AUTH_TOKEN` é obrigatório, pois não há envio para o MegaZap.

Variáveis opcionais (ajuste conforme a documentação real):

```bash
export SIGA_BASE_URL="https://siga04.activesoft.com.br/api"
export SIGA_AUTH_HEADER="Authorization"
export SIGA_AUTH_PREFIX="Bearer"
export SIGA_STUDENTS_ENDPOINT="/alunos"
export SIGA_BOLETOS_ENDPOINT="/alunos/{aluno_id}/boletos"
export SIGA_BOLETOS_BASE_URL="https://siga04.activesoft.com.br/api"
export SIGA_BOLETOS_STUDENT_PARAM="aluno_id"
export SIGA_ACTIVE_YEAR="2026"
export SIGA_PAGE_SIZE="100"
# Headers extras exigidos pelo SIGA (ex: X-CSRFToken)
export SIGA_EXTRA_HEADERS_JSON='{"X-CSRFToken":"seu-csrf-token"}'

export MEGAZAP_BASE_URL="https://api.megazap.com.br"
export MEGAZAP_AUTH_HEADER="Authorization"
export MEGAZAP_AUTH_PREFIX="Bearer"
export MEGAZAP_QRCODE_ENDPOINT="/whatsapp/qrcode"
export MEGAZAP_DEFAULT_MESSAGE="Olá {nome}, seu boleto vence em {data_vencimento}."

# Template JSON mesclado ao payload padrão (opcional)
export MEGAZAP_PAYLOAD_TEMPLATE_JSON='{"canal":"whatsapp"}'
```

## Execução

```bash
python -m src.integration --dry-run
```

Remova `--dry-run` para efetuar os envios.

## Debug do SIGA

Para validar se o script está montando a URL, parâmetros e headers corretos (sem expor o token inteiro), execute:

```bash
python -m src.integration --debug-siga
```

O comando imprime a URL, os parâmetros e os headers com o token ofuscado para facilitar a verificação.

## Ajuste de payload

O payload enviado ao MegaZap é montado em `src/integration.py` e pode ser ajustado através de:

- `MEGAZAP_PAYLOAD_TEMPLATE_JSON` para incluir chaves fixas no JSON.
- `MEGAZAP_DEFAULT_MESSAGE` para definir o texto padrão.
- Sobrescrevendo `build_megazap_payload` caso o modelo precise de mapeamentos específicos.
